# Google Flow (Veo Engine) Automation Pipeline 🚀

Dự án tự động hóa quá trình tạo và tải video từ [Google Flow (Labs)](https://labs.google/fx/tools/flow) sử dụng Python, Selenium, và `undetected-chromedriver`. Hệ thống được thiết kế để vượt qua các rào cản về CAPTCHA, xử lý kết xuất (render) lâu, và quản lý tiến trình làm việc hàng loạt hoàn toàn tự động.

## ✨ Tính năng nổi bật

- 🤖 **Bypass Anti-Bot:** Sử dụng `undetected-chromedriver` để vượt qua các cơ chế phát hiện bot của Google.
- 🍪 **Bảo Lưu Phiên Đăng Nhập:** Quản lý cookies thông minh, xử lý prefix `__Host-` của NextAuth, giúp duy trì phiên làm việc lâu dài mà không cần đăng nhập lại liên tục.
- 📁 **Tải Tệp Lên Trực Tiếp (Headless-friendly):** Can thiệp vào DOM (bỏ qua Windows Native Dialogs) để upload hình ảnh thông qua `send_keys`.
- ⚙️ **Cài Đặt Video Nâng Cao:** Tự động điều hướng Radix UI để cấu hình:
  - Loại (Video/Images)
  - Chế độ (References/Text)
  - Tỷ lệ khung hình (16:9, 9:16)
  - Số lượng (1-4)
  - Model AI (Veo 3.1 Fast, v.v...)
- 🛡️ **Quản Lý Kết Xuất (Retry Logic):** Bắt lỗi khi render (hiện nút Thử lại/Retry), tự động bấm nút thử lại (tối đa 3 lần) và chờ hệ thống tái tạo video thành công mà không break pipeline.
- 📥 **Tải Xuống 2 Tùy Chọn:** 
  1. **ZIP Project Export (`zip`):** Tải toàn bộ dự án dưới dạng 1 file ZIP chặn đứng thất bại mạng, sau đó tự động giải nén ra các file `.mp4` / `.webm` và xóa file rác (Nhanh và ổn định nhất).
  2. **Tải Từng Video (`individual`):** Click vào từng tile video riêng lẻ, chọn mức phân giải và tải xuống native.
- 📋 **Trình Quản Lý Luồng Công Việc (`main.py`):** Lần lượt duyệt qua các luồng task (`pending` -> `processing` -> `completed` / `failed`), tự động đóng/mở trình duyệt mới sau mỗi lần để giải phóng RAM.

---

## 🛠️ Yêu cầu môi trường & Cài đặt

- **Hệ điều hành:** Windows / macOS / Linux
- **Python:** Phiên bản 3.10 trở lên
- **Trình duyệt:** Google Chrome được cài đặt ở thư mục mặc định

### Khởi tạo môi trường ảo (Virtual Environment)
Dự án được khuyến nghị chạy trong môi trường ảo để đảm bảo tính cô lập và tránh xung đột thư viện.

**Trên Windows:**
```powershell
# 1. Tạo môi trường ảo (tên là venv)
python -m venv venv

# 2. Kích hoạt môi trường ảo
.\venv\Scripts\activate

# 3. Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

**Trên macOS/Linux:**
```bash
# 1. Tạo môi trường ảo
python3 -m venv venv

# 2. Kích hoạt môi trường ảo
source venv/bin/activate

# 3. Cài đặt các thư viện
pip install -r requirements.txt
```

---

## ⚙️ Cấu trúc thư mục

```
Create_Video/
├── config/
│   ├── cookies.json       # (Tạo thủ công hoặc qua script) Chứa mảng JSON cookies từ file xuất extention
│   └── selectors.json     # Chứa các bộ chọn XPATH, CSS, Text phục vụ việc bấm nút UI
├── data/
│   └── sample_input.json  # File cấu hình luồng quay vòng các videos cần tạo
├── src/
│   ├── browser_controller.py # Các hàm quản lý trình duyệt, click, delay
│   ├── cookie_manager.py     # Nạp/xuất cookie, kiểm tra login session
│   ├── flow_automator.py     # LỚP CỐT LÕI - Thực thi các bước từ upload đến cấu hình, tải về
│   ├── json_handler.py       # Đọc ghi trạng thái JSON
│   └── test_steps.py         # Chạy trực tiếp 1 task để debug các bước đơn lẻ
├── output/                # Thư mục đích dể hứng các file video (tự động tạo)
├── main.py                # Điểm khởi chạy hệ thống theo vòng lặp các tasks
└── README.md
```

---

## 🔧 Cách cấu hình Job Run (`sample_input.json`)

Mọi thông số của mỗi video được lưu tại `data/sample_input.json`. 

```json
[
  {
    "ten_san_pham": "Ví Nữ Ngắn",
    "prompt": "Create a cinematic product showcase...",
    "link_folder_video": "D:\\Automation\\Create_Video\\output",
    "flow_settings": {
      "type": "VIDEO",
      "mode": "VIDEO_REFERENCES",
      "ratio": "PORTRAIT",
      "count": 2,
      "model": "Veo 3.1 - Fast",
      "download_quality": "720p",
      "download_method": "zip"  // [ "zip" hoặc "individual" ]
    },
    "status": "pending", // Sau khi chạy xong sẽ chuyển thành "completed"
    "_images": [
      "D:\\Automation\\Create_Video\\data\\image_source\\img1.jpg",
      "D:\\Automation\\Create_Video\\data\\image_source\\img2.jpg"
    ]
  }
]
```

### Chi tiết các tùy chọn cấu hình:
| Biến Cấu Hình | Chức năng | Giá trị mẫu |
| --- | --- | --- |
| `status` | Trạng thái của job | `pending`, `processing`, `completed`, `failed` |
| `flow_settings.type` | Loại tạo | `VIDEO`, `IMAGE` |
| `flow_settings.mode` | Chế độ chạy | `VIDEO_REFERENCES`, `TEXT_ONLY` |
| `flow_settings.ratio` | Tỷ lệ màn hình | `PORTRAIT` (9:16), `LANDSCAPE` (16:9) |
| `flow_settings.count` | Số lượng thẻ (tiles) xuất ra | `1`, `2`, `3`, `4` |
| `flow_settings.download_method`| **Cách tải về** | `zip` (Khuyên dùng), `individual` |

---

## 👟 Cách thức hoạt động và khởi chạy

### Bước 1: Mở khóa Cookie
Copy chuỗi JSON xuất từ extention EditThisCookie (hoặc tương tự) trên trình duyệt chính chủ trong thư mục tài khoản Google của bạn, dán vào file `config/cookies.json` để hệ thống không bị dính vòng lặp xác minh Google Đăng nhập lần tới.

### Bước 2: Khởi chạy Pipeline
*(Lưu ý: Chắc chắn rằng bạn đã kích hoạt môi trường ảo - Terminal sẽ hiện chữ `(venv)` ở đầu)*

- **Chạy thực tế ở chế độ Prod:** 
  Hệ thống sẽ duyệt các task "pending", xử lý, báo thành công ("completed"):
  ```bash
  python main.py
  ```

- **Chạy test luồng (Không lưu trạng thái json):**
  Rất tiện khi bạn đang tinh chỉnh XPath, UI selector:
  ```bash
  python src/test_steps.py
  ```

### Các sự kiện diễn ra tự động bên dưới:
1. Mở cửa sổ ẩn/hiện ChromeDriver, nhồi cookie, bypass checking
2. Vào trang chủ nhấn `New Project` + `Image input` + `Bỏ qua Dialog File của Win OS`
3. Tìm phần tử ô prompt, xóa chữ cũ, gõ prompt mới
4. Mở nút 3 chấm, định cấu hình Setting Radix (Aspect ratio, Type...)
5. Chờ thanh loading 3 -> 5 phút
6. Phát hiện các nút "Thử lại", click bù và tiếp tục chờ tiến trình ảo
7. Hoàn tất -> Click vào Tải Project (ZIP / Từng Video) -> Lưu file về thư mục cấu hình -> End Session.

---

## 📌 Khắc phục lỗi phổ biến (Troubleshooting)

1. Lỗi Stale Element Exception 
> *Google Flow dùng React render nên DOM thường xuyên bị xé lẻ, hệ thống hiện tại đã xử lý bằng vòng lặp get_elements liên tục.*

2. Lỗi Không tìm thấy DOM Menu 
> *Bạn cần cập nhật bộ máy selector trong file `config/selectors.json` đề phòng Google đổi giao diện HTML*.

3. Lỗi tải ZIP timeout
> *Đảm bảo đường dẫn tải xuống mặc định (`Downloads`) của bạn không bị ghi đè, hệ thống timeout trong 200s trước khi báo lỗi không nhận được file ZIP.*

# 📖 DOCUMENTATION — Google Flow Video Automation

> Tài liệu kỹ thuật đầy đủ cho project tự động hóa tạo video trên Google Flow (Veo Engine).  
> Cập nhật: 2026-03-27

---

## Mục lục

1. [Tổng quan kiến trúc](#1-tổng-quan-kiến-trúc)
2. [Cấu trúc thư mục](#2-cấu-trúc-thư-mục)
3. [Luồng thực thi (Pipeline)](#3-luồng-thực-thi-pipeline)
4. [Cấu hình môi trường](#4-cấu-hình-môi-trường)
5. [Định dạng dữ liệu đầu vào](#5-định-dạng-dữ-liệu-đầu-vào)
6. [API nội bộ (Internal API Reference)](#6-api-nội-bộ-internal-api-reference)
7. [Hệ thống Retry (Fault Tolerant)](#7-hệ-thống-retry-fault-tolerant)
8. [GUI — Giao diện Desktop](#8-gui--giao-diện-desktop)
9. [Chạy dự án](#9-chạy-dự-án)
10. [Khắc phục sự cố](#10-khắc-phục-sự-cố)
11. [Luồng dữ liệu (Data Flow)](#11-luồng-dữ-liệu-data-flow)

---

## 1. Tổng quan kiến trúc

Project được tổ chức theo mô hình **layered architecture**, phân tách rõ ràng giữa:

```
┌─────────────────────────────────────────────────────────┐
│                     GUI Layer                           │
│          (gui/app.py, gui/panels/*.py)                  │
│  CustomTkinter Desktop App — quản lý project, pipeline  │
└───────────────────────┬─────────────────────────────────┘
                        │  callbacks / events
┌───────────────────────▼─────────────────────────────────┐
│                   API Bridge Layer                      │
│               (src/automation_api.py)                   │
│  Thread management, callbacks, sequential/parallel run  │
└───────────────────────┬─────────────────────────────────┘
                        │  calls
┌───────────────────────▼─────────────────────────────────┐
│                    Engine Layer                         │
│        (src/flow_automator.py) + (src/retry_engine.py)  │
│  8-step pipeline, Selenium automation, retry logic      │
└───────────────────────┬─────────────────────────────────┘
                        │  uses
┌───────────────────────▼─────────────────────────────────┐
│                 Infrastructure Layer                    │
│  browser_controller | cookie_manager | json_handler     │
│  download_manager   | config         | utils            │
└─────────────────────────────────────────────────────────┘
```

### Công nghệ sử dụng

| Thư viện | Phiên bản | Vai trò |
|---|---|---|
| `undetected-chromedriver` | ≥3.5.5 | Vượt qua anti-bot detection của Google |
| `selenium` | ≥4.15.0 | Điều khiển trình duyệt, tương tác DOM |
| `python-dotenv` | ≥1.0.0 | Đọc biến môi trường từ `.env` |
| `customtkinter` | ≥5.2.0 | Giao diện desktop (GUI) |
| `Pillow` | ≥10.0.0 | Xử lý ảnh thumbnail trong GUI |
| `schedule` | ≥1.2.0 | Hỗ trợ lên lịch chạy tự động |

---

## 2. Cấu trúc thư mục

```
Create_Video/
├── config/
│   ├── .env                 # Biến môi trường (timeouts, paths)
│   ├── cookies.json         # Cookie phiên Google (NextAuth)
│   └── selectors.json       # CSS/XPATH selectors cho Google Flow UI
│
├── data/
│   └── sample_input.json    # Danh sách task cần chạy (nguồn sự thật)
│
├── gui/
│   ├── app.py               # Entry point GUI, khởi tạo cửa sổ chính
│   ├── theme.py             # Design tokens (màu sắc, font, kích thước)
│   └── panels/
│       ├── config_panel.py  # Tab ⚙️ Cấu hình (JSON editor, cookies, .env)
│       ├── project_panel.py # Tab 📹 Tạo Video (CRUD project)
│       └── progress_panel.py# Tab 📊 Tiến trình (Render queue, logs)
│
├── src/
│   ├── automation_api.py    # Bridge: GUI ↔ Engine (threading, callbacks)
│   ├── browser_controller.py# Tạo driver, click helper, human delay
│   ├── config.py            # Load .env, export constants toàn global
│   ├── cookie_manager.py    # Load/inject/validate/save cookies
│   ├── discover_editor.py   # Tool debug: khám phá DOM elements
│   ├── discover_selectors.py# Tool debug: tìm selectors đúng
│   ├── download_manager.py  # Theo dõi file tải xuống, đổi tên
│   ├── flow_automator.py    # LỚP CỐT LÕI — 8-step pipeline
│   ├── json_handler.py      # Đọc/ghi/cập nhật sample_input.json
│   ├── main.py              # Main pipeline CLI (chạy trong src/)
│   ├── retry_engine.py      # 3-phase retry strategy
│   ├── test_steps.py        # Debug: chạy 1 task đơn lẻ
│   └── utils.py             # Tiện ích: setup_logger, ...
│
├── docs/
│   └── PLAN-desktop-gui.md  # Kế hoạch thiết kế GUI
│
├── output/                  # Thư mục hứng video (tự tạo khi chạy)
├── logs/                    # Log file (tự tạo khi chạy)
│
├── main.py                  # CLI Entry point (root level)
├── run_gui.py               # GUI Entry point
├── requirements.txt
└── README.md
```

---

## 3. Luồng thực thi (Pipeline)

Pipeline gồm **8 bước tuần tự**, được định nghĩa trong `FlowAutomator.STEPS`:

```
Step 1: navigate          → Mở Chrome, inject cookie, vào Google Flow
Step 2: create_project    → Click "Dự án mới" / "New project"
Step 3: upload_to_prompt  → Click '+' → chặn native dialog → send_keys ảnh
Step 4: enter_prompt      → Điền prompt vào contenteditable field
Step 5: configure_settings→ Mở Radix dropdown, chọn type/mode/ratio/count/model
Step 6: generate          → Click nút "Tạo" để bắt đầu render
Step 7: wait_render       → Poll DOM mỗi 10s, xử lý Retry nếu có tile lỗi
Step 8: download          → Tải ZIP project hoặc từng video (tuỳ config)
```

### Sơ đồ luồng chạy

```
[sample_input.json]
       │
       ▼
  Lọc "pending" tasks
       │
  ┌────▼──────────────────────────────┐
  │  Với mỗi task:                    │
  │                                   │
  │  1. Mở Chrome (undetected)        │
  │  2. Inject cookies                │
  │  3. Chạy 8 steps                  │
  │  4. Retry khi step thất bại       │
  │  5. Cập nhật status → JSON        │
  │  6. Đóng Chrome                   │
  └───────────────────────────────────┘
       │
       ▼
  status: "completed" / "failed"
```

### Kỹ thuật đặc biệt

#### Upload ảnh không dùng Native Dialog
Google Flow dùng `<input type="file">` để upload. Thay vì mở cửa sổ Windows chọn file (không tự động được), hệ thống:
1. Chặn phương thức `.click()` gốc bằng JS injection (`input.click = function() {}`)
2. Click button "Tải hình ảnh lên" để kích hoạt React context
3. Khôi phục `.click()` gốc
4. Gọi `file_input.send_keys(file_paths)` trực tiếp để bypass dialog

#### Xử lý Radix UI Settings
Google Flow dùng Radix UI, selector phải dùng `aria-controls` thay vì class. Ví dụ:
```python
tab = driver.find_element(By.CSS_SELECTOR, "button[aria-controls*='portrait']")
```

---

## 4. Cấu hình môi trường

File: `config/.env`

| Biến | Mặc định | Kiểu | Mô tả |
|---|---|---|---|
| `COOKIES_PATH` | `config/cookies.json` | str | Đường dẫn file cookies |
| `JSON_INPUT_PATH` | `data/sample_input.json` | str | File chứa danh sách task |
| `SELECTORS_PATH` | `config/selectors.json` | str | File chứa CSS/XPATH selectors |
| `LOG_DIR` | `logs` | str | Thư mục chứa log |
| `FLOW_URL` | `https://labs.google/fx/tools/flow` | str | URL Google Flow |
| `HEADLESS` | `false` | bool | Chạy Chrome headless hay không |
| `WINDOW_WIDTH` | `1440` | int | Chiều rộng cửa sổ Chrome |
| `WINDOW_HEIGHT` | `900` | int | Chiều cao cửa sổ Chrome |
| `HUMAN_DELAY_MIN` | `2` | float | Delay ngẫu nhiên tối thiểu (giây) |
| `HUMAN_DELAY_MAX` | `5` | float | Delay ngẫu nhiên tối đa (giây) |
| `PAGE_LOAD_TIMEOUT` | `30` | int | Timeout chờ trang load (giây) |
| `RENDER_TIMEOUT` | `600` | int | Timeout tối đa chờ render video (giây) |
| `DOWNLOAD_TIMEOUT` | `120` | int | Timeout tải file ZIP (giây) |
| `MAX_STEP_RETRY` | `3` | int | Số lần retry mỗi step |
| `MAX_RELOAD_RETRY` | `3` | int | Số lần reload page khi step liên tục fail |
| `MAX_FULL_RESTART` | `1` | int | Số lần restart toàn bộ pipeline |

---

## 5. Định dạng dữ liệu đầu vào

File: `data/sample_input.json`

```json
[
  {
    "d_id": "unique-id-001",
    "ten_san_pham": "Ví Nữ Ngắn Da Bò",
    "prompt": "Create a cinematic product showcase video of a brown leather women's wallet...",
    "link_folder_anh": "D:\\Automation\\Assets\\vi-nu",
    "link_folder_video": "D:\\Automation\\Create_Video\\output",
    "flow_settings": {
      "type": "VIDEO",
      "mode": "VIDEO_REFERENCES",
      "ratio": "PORTRAIT",
      "count": 2,
      "model": "Veo 3.1 - Fast",
      "download_quality": "720p",
      "download_method": "zip"
    },
    "status": "pending"
  }
]
```

### Giải thích các trường

| Trường | Bắt buộc | Giá trị hợp lệ | Mô tả |
|---|---|---|---|
| `d_id` | Không | string | ID duy nhất để tracking (tự tạo nếu không có) |
| `ten_san_pham` | **Có** | string | Tên sản phẩm, dùng để đặt tên file video |
| `prompt` | **Có** | string | Mô tả video gửi vào AI |
| `link_folder_anh` | **Có** | đường dẫn tuyệt đối | Thư mục chứa ảnh tham chiếu |
| `link_folder_video` | Không | đường dẫn tuyệt đối | Thư mục lưu video đầu ra |
| `flow_settings.type` | Không | `VIDEO`, `IMAGE` | Loại output AI tạo |
| `flow_settings.mode` | Không | `VIDEO_REFERENCES`, `TEXT_ONLY` | Chế độ tạo |
| `flow_settings.ratio` | Không | `PORTRAIT` (9:16), `LANDSCAPE` (16:9) | Tỉ lệ khung hình |
| `flow_settings.count` | Không | `1`, `2`, `3`, `4` | Số lượng video/tile |
| `flow_settings.model` | Không | `Veo 3.1 - Fast`, v.v. | Model AI |
| `flow_settings.download_quality` | Không | `720p`, `1080p` | Chất lượng tải xuống (individual mode) |
| `flow_settings.download_method` | Không | `zip` *(mặc định)*, `individual` | **Phương thức tải** |
| `status` | Không | `pending`, `processing`, `completed`, `failed`, `skipped` | Trạng thái hiện tại |

### So sánh download_method

| | `zip` (Khuyên dùng) | `individual` |
|---|---|---|
| **Cách hoạt động** | Click "Tải dự án xuống" → ZIP → giải nén | Click từng tile → chọn chất lượng → tải |
| **Tốc độ** | ✅ Nhanh hơn | ❌ Chậm hơn |
| **Ổn định** | ✅ Cao (1 request) | ❌ Dễ lỗi StaleElement |
| **Chất lượng** | ⚠️ Phụ thuộc Google Flow | ✅ Chọn được 720p/1080p |

---

## 6. API nội bộ (Internal API Reference)

### `FlowAutomator` — `src/flow_automator.py`

Lớp cốt lõi thực thi pipeline.

```python
class FlowAutomator:
    STEPS = ["navigate", "create_project", "upload_to_prompt",
             "enter_prompt", "configure_settings", "generate",
             "wait_render", "download"]

    def __init__(self, driver: WebDriver)
    def execute_all(self, task: dict) -> None        # Chạy từ step 1
    def execute_from_step(self, step_name: str, task: dict) -> None  # Chạy từ step bất kỳ
    def get_step_index(self) -> int                  # Trả về index của step hiện tại

    # Các step methods (tất cả nhận task: dict):
    def step_navigate(self, task)
    def step_create_project(self, task)
    def step_upload_to_prompt(self, task)
    def step_enter_prompt(self, task)
    def step_configure_settings(self, task)
    def step_generate(self, task)
    def step_wait_render(self, task)
    def step_download(self, task)
```

### `AutomationAPI` — `src/automation_api.py`

Bridge giữa GUI và engine. Quản lý threading và callbacks.

```python
class AutomationAPI:
    # Callbacks — đặt trước khi gọi run_tasks()
    on_log: Callable[[str, str], None]       # (message, level)
    on_step_change: Callable[[str, str, int, int, int], None]  # (task_name, step, idx, total, worker_id)
    on_task_complete: Callable[[dict, str, str|None], None]    # (task, status, error)
    on_progress: Callable[[int, int], None]  # (completed, total)
    on_finished: Callable[[dict], None]      # (results: {success, failed, skipped})

    def run_tasks(self, tasks: list, all_tasks: list, headless: bool = True, max_workers: int = 1)
    def stop(self)                           # Dừng sau khi hoàn thành step hiện tại
    def check_ready(self) -> tuple[bool, str]# Kiểm tra cookies hợp lệ

    @property
    def is_running(self) -> bool
```

**Ví dụ sử dụng:**
```python
api = AutomationAPI()
api.on_log = lambda msg, level: print(f"[{level}] {msg}")
api.on_task_complete = lambda task, status, err: print(f"{task['ten_san_pham']}: {status}")
api.run_tasks(pending_tasks, all_tasks, headless=False, max_workers=1)
```

### `RetryEngine` — `src/retry_engine.py`

Xử lý 3 tầng retry khi step thất bại.

```python
class RetryEngine:
    def __init__(self, driver: WebDriver, automator: FlowAutomator)
    def execute_task_with_retry(self, task: dict) -> bool
```

### `GUILogHandler` — `src/automation_api.py`

`logging.Handler` tùy chỉnh chuyển tiếp log tới GUI callback.

```python
class GUILogHandler(logging.Handler):
    def __init__(self, callback: Callable, worker_id: int | None = None)
```

---

## 7. Hệ thống Retry (Fault Tolerant)

### 3-Phase Retry Strategy

```
Phase 1: STEP-LEVEL RETRY
  ├─ Mỗi step được retry tối đa MAX_STEP_RETRY (mặc định: 3) lần
  ├─ Backoff: 2^attempt giây giữa mỗi lần (2s → 4s → 8s)
  └─ Nếu step "wait_render" thất bại → thử download video còn lại

Phase 2: PAGE RELOAD RETRY
  ├─ Nếu Phase 1 thất bại: reload trang
  ├─ Tiếp tục từ step bị lỗi (execute_from_step)
  └─ Tối đa MAX_RELOAD_RETRY (mặc định: 3) lần

Phase 3: FULL RESTART
  ├─ Nếu Phase 2 thất bại: quay về URL gốc
  ├─ Chạy lại toàn bộ pipeline từ đầu
  └─ Tối đa MAX_FULL_RESTART (mặc định: 1) lần
```

### Render Retry (trong step_wait_render)

Khi đang render, nếu phát hiện nút "Thử lại" / "Retry":
- Click tất cả tile lỗi
- Chờ 30 giây để job được re-queue
- Reset timer timeout
- Tối đa `MAX_RETRIES = 3` lần (hardcoded trong FlowAutomator)

---

## 8. GUI — Giao diện Desktop

Entry point: `run_gui.py` → `gui/app.py`

### Tab ⚙️ Cấu hình (`config_panel.py`)

- **JSON Editor**: Xem và chỉnh sửa `data/sample_input.json` trực tiếp
- **Cookie Manager**: Import từ file hoặc paste JSON text, validate cấu trúc
- **Settings Editor**: Chỉnh `.env` qua form (không cần mở file thủ công)

### Tab 📹 Tạo Video (`project_panel.py`)

- **Sidebar**: Danh sách project với icon trạng thái (🟡 pending, ✅ done, ❌ failed)
- **Detail Form**: Chỉnh `ten_san_pham`, `prompt`, ảnh, video settings, output folder
- **Actions**: Thêm mới, Clone, Xóa (đơn / hàng loạt)
- **Validation**: Cảnh báo nếu thiếu thông tin bắt buộc khi lưu

### Tab 📊 Tiến trình (`progress_panel.py`)

- **Render Queue**: Checkbox chọn task, icon trạng thái real-time
- **Pipeline Step Indicator**: 8 bước trực quan (sáng lên theo tiến trình)
- **Log Viewer**: Real-time log với timestamp, auto-scroll
- **Action Bar**: Chọn số workers (1–4), chạy toàn bộ hoặc chạy đã chọn, nút Dừng

### Phím tắt

| Tổ hợp phím | Chức năng |
|---|---|
| `Ctrl+S` | Lưu project đang chỉnh sửa |
| `F5` | Refresh danh sách & render queue |
| `Ctrl+R` | Chạy tất cả task pending |
| `Escape` | Dừng pipeline đang chạy |

### Design Tokens (`gui/theme.py`)

File `theme.py` chứa tất cả màu sắc, font, và kích thước dùng xuyên suốt GUI. Khi muốn đổi giao diện, chỉ cần sửa file này.

---

## 9. Chạy dự án

### Yêu cầu hệ thống

- **OS**: Windows / macOS / Linux
- **Python**: ≥ 3.10
- **Chrome**: Bản mới nhất (cùng phiên bản với ChromeDriver)

### Cài đặt

```powershell
# Tạo môi trường ảo
python -m venv venv
.\venv\Scripts\activate     # Windows
# source venv/bin/activate  # macOS/Linux

# Cài thư viện
pip install -r requirements.txt
```

### Lần đầu chạy: Import Cookies

1. Đăng nhập thủ công vào [labs.google/fx/tools/flow](https://labs.google/fx/tools/flow)
2. Dùng extension **EditThisCookie** (Chrome) hoặc **Cookie-Editor** để export cookies dạng JSON
3. Import vào GUI qua tab **⚙️ Cấu hình → Cookie Manager**

> ⚠️ **Lưu ý**: Cookies Google có prefix `__Host-` nên yêu cầu inject đúng domain. Hệ thống tự xử lý điều này.

### Chạy qua GUI (Khuyên dùng)

```powershell
.\venv\Scripts\activate
python run_gui.py
```

1. Tab **⚙️ Cấu hình** → Import cookies → Kiểm tra Settings
2. Tab **📹 Tạo Video** → Tạo các dự án cần render
3. Tab **📊 Tiến trình** → Chọn số workers → Bấm **▶ Chạy tất cả**

### Chạy qua CLI

```powershell
.\venv\Scripts\activate

# Chạy toàn bộ pending tasks
python main.py

# Debug 1 task đơn lẻ
python src/test_steps.py
```

### Chạy song song (Parallel)

Trong GUI, tab **Tiến trình**, chọn số workers (1–4). Mỗi worker là 1 Chrome instance độc lập:

```
Worker 1: Task A → Task D → Task G
Worker 2: Task B → Task E → Task H  
Worker 3: Task C → Task F → Task I
```

> ⚠️ RAM: Mỗi Chrome chiếm ~400–800MB. Với 4 workers, cần ít nhất 4GB RAM trống.

---

## 10. Khắc phục sự cố

### ❌ Lỗi StaleElementReferenceException

**Nguyên nhân**: Google Flow dùng React — DOM re-render liên tục gây mất tham chiếu element.

**Giải pháp**: Hệ thống đã tích hợp `get_tiles()` với vòng lặp lấy lại element mỗi lần trước khi click. Nếu vẫn xảy ra, tăng `HUMAN_DELAY_MIN` và `HUMAN_DELAY_MAX` trong `.env`.

---

### ❌ Không tìm thấy DOM Menu / Selector

**Nguyên nhân**: Google Flow đổi giao diện HTML (đây là web app, không phải native app).

**Giải pháp**: Cập nhật `config/selectors.json`. Dùng tool debug:
```powershell
python src/discover_selectors.py
```

---

### ❌ ZIP download timeout

**Nguyên nhân**: Thư mục Downloads bị ghi đè hoặc mạng chậm.

**Giải pháp**:
- Kiểm tra đường dẫn mặc định `C:\Users\<user>\Downloads` không bị redirect
- Tăng `DOWNLOAD_TIMEOUT` trong `.env` (mặc định 120 giây)
- Đảm bảo đủ dung lượng ổ đĩa

---

### ❌ Cookies hết hạn / Đăng nhập thất bại

**Giải pháp**:
1. Đăng nhập lại thủ công vào Google Flow
2. Export cookies mới bằng extension
3. Import lại trong GUI → tab **⚙️ Cấu hình → Cookie Manager**

---

### ❌ GUI không mở được

**Giải pháp**:
```powershell
pip install customtkinter Pillow
# Hoặc cài lại toàn bộ:
pip install -r requirements.txt
```

---

### ❌ ChromeDriver version mismatch

**Giải pháp**: `undetected-chromedriver` tự tải ChromeDriver phù hợp. Tuy nhiên cần có Chrome được cài từ trước. Cập nhật Chrome lên bản mới nhất.

---

## 11. Luồng dữ liệu (Data Flow)

```
[Người dùng tạo project trong GUI]
           │
           ▼
   data/sample_input.json
   {"status": "pending", ...}
           │
           ▼
   AutomationAPI.run_tasks()
   (background thread)
           │
           ├─ status → "processing"  →  ghi vào JSON
           │
           ▼
   RetryEngine.execute_task_with_retry()
           │
           ▼
   FlowAutomator.execute_all()
   Step 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8
           │
     Thành công?
      ┌────┴────┐
     Có        Không
      │         │
      ▼         ▼
  status →  Retry Engine
 "completed"  Phase 1/2/3
  ghi JSON       │
              Vẫn lỗi?
                 │
                 ▼
            status → "failed"
            error_reason → ghi JSON
           │
           ▼
   on_task_complete() callback
   GUI update: icon, log, progress bar
```

---

*Tài liệu được tạo bởi Antigravity AI — 2026-03-27*

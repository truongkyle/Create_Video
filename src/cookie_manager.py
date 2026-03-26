import json
import logging

from src.config import COOKIES_PATH

logger = logging.getLogger("flow_automation")


def load_cookies():
    with open(COOKIES_PATH, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    logger.info(f"Loaded {len(cookies)} cookies from {COOKIES_PATH}")
    return cookies


def inject_cookies(driver, cookies):
    import time

    # Navigate to domain first (required to set cookies for that domain)
    for attempt in range(3):
        try:
            driver.get("https://labs.google")
            time.sleep(3)
            break
        except Exception as e:
            logger.warning(f"Navigation attempt {attempt+1} failed: {e}")
            time.sleep(2)
            if attempt == 2:
                raise

    for cookie in cookies:
        selenium_cookie = {
            "name": cookie["name"],
            "value": cookie["value"],
            "domain": cookie.get("domain", "labs.google"),
            "path": cookie.get("path", "/"),
            "secure": cookie.get("secure", True),
        }
        if cookie.get("expirationDate"):
            selenium_cookie["expiry"] = int(cookie["expirationDate"])
        if cookie.get("sameSite"):
            same_site = cookie["sameSite"].capitalize()
            if same_site in ("Strict", "Lax", "None"):
                selenium_cookie["sameSite"] = same_site

        if cookie["name"].startswith("__Host-") and "domain" in selenium_cookie:
            del selenium_cookie["domain"]

        try:
            driver.add_cookie(selenium_cookie)
            logger.debug(f"Injected cookie: {cookie['name']}")
        except Exception as e:
            logger.warning(f"Failed to inject cookie {cookie['name']}: {e}")

    logger.info("All cookies injected")


def save_cookies(driver, path=None):
    path = path or COOKIES_PATH
    selenium_cookies = driver.get_cookies()
    export = []
    for c in selenium_cookies:
        entry = {
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ""),
            "path": c.get("path", "/"),
            "secure": c.get("secure", False),
            "httpOnly": c.get("httpOnly", False),
        }
        if c.get("expiry"):
            entry["expirationDate"] = c["expiry"]
        if c.get("sameSite"):
            entry["sameSite"] = c["sameSite"].lower()
        export.append(entry)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(export)} cookies to {path}")


def validate_login(driver):
    import time
    time.sleep(3)
    page_source = driver.page_source.lower()

    is_logged_in = (
        "sign in" not in page_source
        or "avatar" in page_source
        or "user" in page_source
    )
    if is_logged_in:
        logger.info("Login validated: user is authenticated")
    else:
        logger.warning("Login validation: user may NOT be authenticated")
    return is_logged_in


def validate_cookies(cookies_data):
    """Validate cookie data structure. Returns (is_valid, message)."""
    if not isinstance(cookies_data, list):
        return False, "Dữ liệu cookies phải là một danh sách (JSON array)"

    if len(cookies_data) == 0:
        return False, "Danh sách cookies trống"

    required_fields = {"name", "value"}
    for i, cookie in enumerate(cookies_data):
        if not isinstance(cookie, dict):
            return False, f"Cookie #{i+1} không phải object"
        missing = required_fields - set(cookie.keys())
        if missing:
            return False, f"Cookie #{i+1} thiếu field: {', '.join(missing)}"

    return True, f"✅ Hợp lệ — {len(cookies_data)} cookies"


def import_cookies_from_text(json_text):
    """Parse JSON text, validate, and save to cookies.json. Returns (success, message)."""
    try:
        cookies_data = json.loads(json_text)
    except json.JSONDecodeError as e:
        return False, f"❌ JSON không hợp lệ: {e}"

    is_valid, msg = validate_cookies(cookies_data)
    if not is_valid:
        return False, f"❌ {msg}"

    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        json.dump(cookies_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Imported {len(cookies_data)} cookies from text input")
    return True, f"✅ Đã lưu {len(cookies_data)} cookies vào {COOKIES_PATH.name}"


def has_valid_cookies():
    """Check if a valid cookies file exists."""
    if not COOKIES_PATH.exists():
        return False, "❌ Chưa có file cookies.json"
    try:
        with open(COOKIES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        is_valid, msg = validate_cookies(data)
        return is_valid, msg
    except Exception as e:
        return False, f"❌ Lỗi đọc cookies: {e}"


def first_time_login(driver, flow_url):
    print("\n" + "=" * 60)
    print("  LẦN ĐẦU CHẠY — CẦN ĐĂNG NHẬP THỦ CÔNG")
    print("=" * 60)
    print(f"\n  Browser đã mở trang: {flow_url}")
    print("  → Hãy đăng nhập bằng tài khoản Google của bạn")
    print("  → Sau khi thấy giao diện Flow, quay lại đây")
    input("\n  ✅ Nhấn ENTER khi đã đăng nhập xong... ")
    save_cookies(driver)
    print("  💾 Cookies đã được lưu! Lần sau không cần đăng nhập lại.\n")

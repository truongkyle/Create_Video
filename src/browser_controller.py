import json
import logging
import random
import time

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)

from src.config import (
    HEADLESS, WINDOW_WIDTH, WINDOW_HEIGHT,
    HUMAN_DELAY_MIN, HUMAN_DELAY_MAX,
    PAGE_LOAD_TIMEOUT, SELECTORS_PATH,
)

logger = logging.getLogger("flow_automation")


def load_selectors():
    with open(SELECTORS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


SELECTORS = None


def get_selectors():
    global SELECTORS
    if SELECTORS is None:
        SELECTORS = load_selectors()
    return SELECTORS


def create_driver(headless=None):
    if headless is None:
        headless = HEADLESS

    options = uc.ChromeOptions()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument(f"--window-size={WINDOW_WIDTH},{WINDOW_HEIGHT}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-gpu")

    prefs = {
        "profile.default_content_settings.popups": 0,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    options.add_experimental_option("prefs", prefs)

    chrome_version = _detect_chrome_version()
    logger.info(f"Detected Chrome version: {chrome_version}")

    # Retry driver creation up to 3 times
    last_err = None
    for attempt in range(1, 4):
        try:
            driver = uc.Chrome(
                options=options,
                version_main=chrome_version,
            )
            time.sleep(5)  # Longer wait for Chrome to stabilize
            # Verify window is alive
            _ = driver.current_url
            driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
            driver.implicitly_wait(5)
            logger.info(f"Chrome driver created (headless={headless}, version={chrome_version})")
            return driver
        except Exception as e:
            last_err = e
            logger.warning(f"Driver creation attempt {attempt} failed: {e}")
            try:
                driver.quit()
            except Exception:
                pass
            time.sleep(3)

    raise RuntimeError(f"Failed to create Chrome driver after 3 attempts: {last_err}")


def _detect_chrome_version():
    """Auto-detect installed Chrome major version."""
    import subprocess
    import re
    try:
        # Windows: query registry for Chrome version
        result = subprocess.run(
            ['reg', 'query', r'HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon', '/v', 'version'],
            capture_output=True, text=True, timeout=5
        )
        match = re.search(r'(\d+)\.\d+\.\d+\.\d+', result.stdout)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    try:
        # Fallback: try running chrome --version
        result = subprocess.run(
            ['chrome', '--version'], capture_output=True, text=True, timeout=5
        )
        match = re.search(r'(\d+)\.\d+', result.stdout)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    # Default fallback
    logger.warning("Could not detect Chrome version, defaulting to 146")
    return 146


def set_download_dir(driver, download_path):
    params = {
        "behavior": "allow",
        "downloadPath": str(download_path),
    }
    driver.execute_cdp_cmd("Page.setDownloadBehavior", params)
    logger.debug(f"Download dir set to: {download_path}")


def human_delay(min_s=None, max_s=None):
    min_s = min_s or HUMAN_DELAY_MIN
    max_s = max_s or HUMAN_DELAY_MAX
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)
    return delay


def human_click(driver, element):
    try:
        actions = ActionChains(driver)
        offset_x = random.randint(-3, 3)
        offset_y = random.randint(-3, 3)
        actions.move_to_element_with_offset(element, offset_x, offset_y)
        actions.pause(random.uniform(0.1, 0.3))
        actions.click()
        actions.perform()
    except Exception as e:
        logger.debug(f"ActionChains click failed ({type(e).__name__}), falling back to direct click")
        try:
            element.click()
        except:
            driver.execute_script("arguments[0].click();", element)
            
    human_delay(0.5, 1.5)


def human_type(driver, element, text, clear_first=True):
    if clear_first:
        element.clear()
        human_delay(0.3, 0.6)

    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.03, 0.12))

    human_delay(0.5, 1.0)


def safe_find(driver, selector_str, timeout=10, multiple=False):
    selectors = [s.strip() for s in selector_str.split(",")]

    for sel in selectors:
        try:
            by = By.XPATH if sel.startswith(("//", "(//")) else By.CSS_SELECTOR
            if multiple:
                elements = WebDriverWait(driver, timeout).until(
                    EC.presence_of_all_elements_located((by, sel))
                )
                if elements:
                    return elements
            else:
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((by, sel))
                )
                return element
        except (TimeoutException, NoSuchElementException):
            continue

    logger.warning(f"Element not found with selectors: {selector_str}")
    return None


def safe_click(driver, selector_str, timeout=10):
    selectors = [s.strip() for s in selector_str.split(",")]

    for sel in selectors:
        try:
            by = By.XPATH if sel.startswith(("//", "(//")) else By.CSS_SELECTOR
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, sel))
            )
            human_click(driver, element)
            return True
        except (TimeoutException, NoSuchElementException,
                ElementClickInterceptedException, StaleElementReferenceException):
            continue

    logger.warning(f"Could not click element: {selector_str}")
    return False


def find_by_text(driver, tag, text, timeout=10):
    xpath = f"//{tag}[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        return element
    except TimeoutException:
        return None


def click_by_text(driver, tag, text, timeout=10):
    element = find_by_text(driver, tag, text, timeout)
    if element:
        human_click(driver, element)
        return True
    logger.warning(f"Could not find element <{tag}> with text '{text}'")
    return False


def close_driver(driver):
    try:
        driver.quit()
        logger.info("Chrome driver closed")
    except Exception as e:
        logger.warning(f"Error closing driver: {e}")

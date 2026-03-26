import logging
import time
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException

from src.browser_controller import (
    get_selectors, human_delay, human_click, human_type,
    safe_find, safe_click, click_by_text, find_by_text,
    set_download_dir,
)
from src.config import FLOW_URL, RENDER_TIMEOUT

logger = logging.getLogger("flow_automation")


class FlowAutomator:
    """Automates Google Flow video creation.

    Simplified workflow (confirmed 2026-03-26):
    1. Navigate to Flow
    2. Click '+ Dự án mới'
    3. Click '+' in prompt bar → Click 'Tải hình ảnh lên' → Upload images directly
    4. Type prompt
    5. Select model/ratio
    6. Click 'Tạo' (Generate)
    7. Wait for render
    8. Download video
    """

    STEPS = [
        "navigate",
        "create_project",
        "upload_to_prompt",
        "enter_prompt",
        "configure_settings",
        "generate",
        "wait_render",
        "download",
    ]

    def __init__(self, driver):
        self.driver = driver
        self.selectors = get_selectors()
        self.current_step = None
        self.completed_steps = []

    def get_step_index(self):
        if self.current_step is None:
            return 0
        try:
            return self.STEPS.index(self.current_step)
        except ValueError:
            return 0

    def execute_from_step(self, step_name, task):
        start_idx = self.STEPS.index(step_name)
        for i in range(start_idx, len(self.STEPS)):
            step = self.STEPS[i]
            self.current_step = step
            logger.info(f">> Step {i + 1}/{len(self.STEPS)}: {step}")

            method = getattr(self, f"step_{step}")
            method(task)

            self.completed_steps.append(step)
            human_delay()

        logger.info("[OK] All steps completed")

    def execute_all(self, task):
        self.completed_steps = []
        self.execute_from_step("navigate", task)

    # --- Step 1: Navigate ---
    def step_navigate(self, task):
        self.driver.get(FLOW_URL)
        human_delay(3, 5)
        logger.info(f"Navigated to {FLOW_URL}")

    def step_create_project(self, task):
        sel = self.selectors.get("new_project", {})
        btn_css = sel.get("btn_css", "")
        
        # 1. Handle landing page if present
        landing_clicked = click_by_text(self.driver, "*", "Create with Flow", timeout=5)
        if not landing_clicked:
            landing_clicked = click_by_text(self.driver, "*", "Tạo bằng Flow", timeout=2)
        if landing_clicked:
            logger.info("Clicked landing page 'Create with Flow' button")
            human_delay(5, 7)
        
        # 2. Look for New Project button
        clicked = click_by_text(self.driver, "*", "Dự án mới", timeout=10)
        if not clicked:
            clicked = click_by_text(self.driver, "*", "New project", timeout=5)
            
        if not clicked and btn_css:
            clicked = safe_click(self.driver, btn_css, timeout=5)
            
        if clicked:
            logger.info("Clicked New Project")
            human_delay(3, 5)
        else:
            logger.warning("Could not find 'New project' button - assuming we are already inside a project workspace")

    # --- Step 3: Upload images directly into prompt ---
    def step_upload_to_prompt(self, task):
        """Click '+' → intercept native dialog → 'Tải hình ảnh lên' → send_keys."""
        images = task.get("_images", [])
        if not images:
            raise ValueError("No images to upload")
        logger.info(f"Task specifies {len(images)} images to upload as prompt ingredients")

        sel = self.selectors.get("upload_to_prompt", {})
        
        # 1. Click '+' button to open the ingredient dialog
        # The prompt interface might take a few seconds to load
        plus_btn = safe_find(self.driver, sel.get("plus_btn_aria", "button[aria-haspopup='dialog']"), timeout=15)
        if not plus_btn:
            plus_btn = safe_find(self.driver, sel.get("plus_btn_css", "button.jQayrS"), timeout=5)
        
        if not plus_btn:
            icon = find_by_text(self.driver, "i", "add_2", timeout=5)
            if icon:
                plus_btn = icon.find_element(By.XPATH, "./..")
        if not plus_btn:
            raise RuntimeError("Cannot find '+' button next to prompt")

        human_click(self.driver, plus_btn)
        human_delay(1, 2)
        logger.info("Clicked '+' — dialog opened")

        # 2. Intercept file input click to prevent native Windows dialog
        file_input = safe_find(self.driver, "input[type='file']", timeout=5)
        if not file_input:
            raise RuntimeError("Cannot find file input")

        self.driver.execute_script("""
            var input = arguments[0];
            input._originalClick = input.click;
            input.click = function() { /* blocked native dialog */ };
        """, file_input)

        # 3. Click 'Tải hình ảnh lên' — sets React context for prompt upload
        upload_btn = find_by_text(self.driver, "button", "Tải hình ảnh lên", timeout=5)
        if not upload_btn:
            upload_btn = find_by_text(self.driver, "span", "Tải hình ảnh lên", timeout=5)
            if upload_btn:
                upload_btn = upload_btn.find_element(By.XPATH, "./..")
        if not upload_btn:
            upload_icon = find_by_text(self.driver, "i", "upload", timeout=5)
            if upload_icon:
                upload_btn = upload_icon.find_element(By.XPATH, "./..")

        if upload_btn:
            human_click(self.driver, upload_btn)
            human_delay(0.5, 1)
            logger.info("Clicked 'Tải hình ảnh lên' (native dialog intercepted)")
        else:
            logger.warning("Upload button not found — trying direct send_keys")

        # 4. Restore original click and send files via send_keys
        self.driver.execute_script("""
            var input = arguments[0];
            if (input._originalClick) input.click = input._originalClick;
        """, file_input)

        file_paths = "\n".join(images)
        file_input.send_keys(file_paths)
        logger.info(f"Uploaded {len(images)} images to prompt")
        human_delay(5, 8)

    # --- Step 4: Enter prompt ---
    def step_enter_prompt(self, task):
        prompt = task.get("prompt", "")
        if not prompt:
            raise ValueError("No prompt provided")

        sel = self.selectors.get("prompt", {})

        prompt_el = safe_find(self.driver, sel.get("contenteditable", ""), timeout=10)
        if not prompt_el:
            prompt_el = safe_find(self.driver, "div[contenteditable='true']", timeout=10)
        if not prompt_el:
            prompt_el = find_by_text(self.driver, "div", "Bạn muốn tạo gì", timeout=5)
        if not prompt_el:
            raise RuntimeError("Cannot find prompt input field")

        human_click(self.driver, prompt_el)
        human_delay(0.5, 1)

        prompt_el.send_keys(Keys.CONTROL + "a")
        human_delay(0.2, 0.4)
        prompt_el.send_keys(Keys.DELETE)
        human_delay(0.3, 0.5)

        human_type(self.driver, prompt_el, prompt, clear_first=False)
        logger.info(f"Entered prompt ({len(prompt)} chars)")

    # --- Step 5: Configure Video Settings ---
    def step_configure_settings(self, task):
        settings = task.get("flow_settings", {})
        if not settings:
            logger.info("No flow_settings in task, skipping configuration")
            return

        sel = self.selectors.get("settings", {})
        
        # 1. Open settings dropdown
        dropdown_opened = False
        
        # Check if tabs are already visible
        if safe_find(self.driver, "button[role='tab']", timeout=1):
            dropdown_opened = True
        else:
            # Find trigger button: The settings button has aria-haspopup="menu" and its text contains the config 
            # (e.g., 'Video', 'Hình ảnh', 'x1', 'x2') or it has an internal crop icon.
            # Avoid the 'more_vert' (Tuỳ chọn) menu.
            trigger_btns = self.driver.find_elements(By.CSS_SELECTOR, "button[aria-haspopup='menu']")
            valid_texts = ["Video", "Hình ảnh", "16:9", "9:16", "x1", "x2", "x3", "x4", "Khung hình", "Thành phần"]
            for btn in trigger_btns:
                text = btn.text.strip()
                html = btn.get_attribute("innerHTML") or ""
                is_match = any(v in text for v in valid_texts) or "crop_" in html
                if is_match and "Sắp xếp" not in text and "Tuỳ chọn" not in text:
                    if btn.get_attribute("aria-expanded") == "false":
                        human_click(self.driver, btn)
                        human_delay(1, 2)
                    dropdown_opened = True
                    break
                    
        if not dropdown_opened:
            logger.warning("Could not verify settings dropdown is open, attempting to proceed anyway")

        # 2. Helper to click Radix tabs
        def click_tab(category, key):
            val = settings.get(key)
            if not val:
                return
            
            option = sel.get(category, {}).get(str(val))
            if not option:
                logger.warning(f"Invalid {category} setting in config: {val}")
                return
                
            aria_contains = option.get("aria_controls_contains")
            
            tab = safe_find(self.driver, f"button[aria-controls*='{aria_contains}']", timeout=2)
            if tab:
                is_selected = tab.get_attribute("aria-selected") == "true"
                if not is_selected:
                    human_click(self.driver, tab)
                    logger.info(f"Set {category} -> {val}")
                    human_delay(0.5, 1)
                else:
                    logger.info(f"Setting {category} -> {val} already selected")
            else:
                logger.warning(f"Could not find tab for {category} -> {val}")

        # 3. Click the configuration tabs
        click_tab("type", "type")
        click_tab("mode", "mode")
        click_tab("ratio", "ratio")
        click_tab("count", "count")
        
        # 4. Handle model selection (dropdown inside the dropdown)
        model = settings.get("model")
        if model:
            # Model trigger inside the menu (it's the last button with aria-haspopup)
            model_triggers = self.driver.find_elements(By.CSS_SELECTOR, "button[aria-haspopup='menu']")
            # The inner one might be the only one visible now, or the last one
            if model_triggers:
                inner_trigger = model_triggers[-1]
                if inner_trigger.get_attribute("aria-expanded") == "false":
                    human_click(self.driver, inner_trigger)
                    human_delay(0.5, 1)
                    
            model_option = find_by_text(self.driver, "*", model, timeout=2)
            if model_option:
                human_click(self.driver, model_option)
                logger.info(f"Set model -> {model}")
                human_delay(0.5, 1)
            else:
                logger.warning(f"Could not find model option: {model}")
        
        # Close settings dropdown (Escape key usually works)
        ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
        human_delay(0.5, 1)

    # --- Step 6: Generate ---
    def step_generate(self, task):
        sel = self.selectors.get("generate", {})
        btn_css = sel.get("btn_css", "")

        clicked = safe_click(self.driver, btn_css, timeout=5) if btn_css else False
        if not clicked:
            logger.info("CSS selector failed for Generate, trying JS fallback")
            btn = self.driver.execute_script("""
                return Array.from(document.querySelectorAll('button')).find(b => 
                    b.innerText && b.innerText.includes('Tạo') && 
                    !b.innerText.includes('Dự án') && 
                    b.offsetParent !== null
                );
            """)
            if btn:
                human_click(self.driver, btn)
                clicked = True

        if clicked:
            logger.info("Generate clicked — rendering...")
        else:
            raise RuntimeError("Cannot find Generate button")
        human_delay(2, 3)

    # --- Step 7: Wait for render ---
    def step_wait_render(self, task):
        start = time.time()
        check_interval = 10
        last_log = 0

        while time.time() - start < RENDER_TIMEOUT:
            elapsed = int(time.time() - start)

            video_el = safe_find(self.driver, "video", timeout=3)
            if video_el:
                logger.info(f"Render done in {elapsed}s")
                human_delay(2, 3)
                return

            dl_btn = find_by_text(self.driver, "*", "Download", timeout=2)
            if not dl_btn:
                dl_btn = find_by_text(self.driver, "*", "Tải", timeout=2)
            if dl_btn:
                logger.info(f"Render done in {elapsed}s (download ready)")
                return

            retry_btn = find_by_text(self.driver, "*", "Thử lại", timeout=1)
            if not retry_btn:
                retry_btn = find_by_text(self.driver, "*", "Retry", timeout=1)
            if retry_btn:
                raise RuntimeError("Render failed — retry needed")

            if elapsed - last_log >= 30:
                logger.info(f"Rendering... {elapsed}s")
                last_log = elapsed

            time.sleep(check_interval)

        raise TimeoutException(f"Render timeout after {RENDER_TIMEOUT}s")

    # --- Step 8: Download ---
    def step_download(self, task):
        download_folder = task.get("link_folder_video", "")
        if download_folder:
            Path(download_folder).mkdir(parents=True, exist_ok=True)
            set_download_dir(self.driver, download_folder)

        clicked = click_by_text(self.driver, "button", "Download", timeout=10)
        if not clicked:
            clicked = click_by_text(self.driver, "button", "Tải về", timeout=5)
        if not clicked:
            clicked = click_by_text(self.driver, "*", "Download", timeout=5)

        if not clicked:
            video_el = safe_find(self.driver, "video", timeout=5)
            if video_el:
                src = video_el.get_attribute("src")
                if src:
                    logger.info(f"Video URL: {src[:80]}...")
                    self.driver.execute_script(f"window.open('{src}', '_blank');")
                    human_delay(3, 5)
                    clicked = True

        if clicked:
            logger.info("Download initiated")
            human_delay(5, 10)
        else:
            raise RuntimeError("Cannot find download button or video source")

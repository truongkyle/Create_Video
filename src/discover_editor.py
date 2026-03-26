"""
Step-by-step Selector Discovery
---------------------------------
Opens Flow, clicks 'Du an moi', then scans each page state.
Pauses at each step so user can verify.

Usage:
    venv/Scripts/python src/discover_editor.py
"""

import sys
import json
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import FLOW_URL, COOKIES_PATH, SELECTORS_PATH
from src.cookie_manager import load_cookies, inject_cookies
from src.browser_controller import create_driver, close_driver, human_delay
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


SCAN_SCRIPT = r"""
function discoverElements() {
    const results = {
        buttons: [], inputs: [], textareas: [], file_inputs: [],
        dropdowns: [], clickable: [], contenteditable: [], links: [],
        iframes: [], videos: [], images: [],
    };

    function getSelector(el) {
        if (el.id) return '#' + el.id;
        const testId = el.getAttribute('data-testid');
        if (testId) return '[data-testid="' + testId + '"]';
        const ariaLabel = el.getAttribute('aria-label');
        if (ariaLabel) return '[aria-label="' + ariaLabel + '"]';
        if (el.className && typeof el.className === 'string') {
            const classes = el.className.trim().split(/\s+/).filter(c => c.length > 0 && !c.startsWith('sc-'));
            if (classes.length > 0) {
                const sel = el.tagName.toLowerCase() + '.' + classes.join('.');
                try { if (document.querySelectorAll(sel).length === 1) return sel; } catch(e) {}
            }
            // Try with all classes including styled-components
            const allClasses = el.className.trim().split(/\s+/).filter(c => c.length > 0);
            if (allClasses.length > 0) {
                const sel = el.tagName.toLowerCase() + '.' + allClasses.join('.');
                try { if (document.querySelectorAll(sel).length <= 3) return sel; } catch(e) {}
            }
        }
        const role = el.getAttribute('role');
        if (role) {
            const sel = '[role="' + role + '"]';
            try { if (document.querySelectorAll(sel).length === 1) return sel; } catch(e) {}
        }
        let path = [];
        let cur = el;
        while (cur && cur !== document.body) {
            let tag = cur.tagName.toLowerCase();
            if (cur.id) { path.unshift('#' + cur.id); break; }
            const parent = cur.parentElement;
            if (parent) {
                const sibs = Array.from(parent.children).filter(c => c.tagName === cur.tagName);
                if (sibs.length > 1) tag += ':nth-of-type(' + (sibs.indexOf(cur) + 1) + ')';
            }
            path.unshift(tag);
            cur = parent;
        }
        return path.join(' > ');
    }

    function info(el) {
        const r = el.getBoundingClientRect();
        return {
            tag: el.tagName.toLowerCase(),
            selector: getSelector(el),
            text: (el.textContent || '').trim().substring(0, 120),
            type: el.type || null,
            name: el.name || null,
            id: el.id || null,
            'class': el.className && typeof el.className === 'string' ? el.className.trim().substring(0, 200) : null,
            'data-testid': el.getAttribute('data-testid'),
            'aria-label': el.getAttribute('aria-label'),
            role: el.getAttribute('role'),
            placeholder: el.placeholder || null,
            contenteditable: el.getAttribute('contenteditable'),
            visible: r.width > 0 && r.height > 0,
            position: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) }
        };
    }

    document.querySelectorAll('button, [role="button"]').forEach(el => results.buttons.push(info(el)));
    document.querySelectorAll('input:not([type="file"]):not([type="hidden"])').forEach(el => results.inputs.push(info(el)));
    document.querySelectorAll('textarea').forEach(el => results.textareas.push(info(el)));
    document.querySelectorAll('input[type="file"]').forEach(el => results.file_inputs.push(info(el)));
    document.querySelectorAll('[contenteditable="true"]').forEach(el => results.contenteditable.push(info(el)));
    document.querySelectorAll('select, [role="listbox"], [role="combobox"], [role="menu"], [role="menubar"]').forEach(el => results.dropdowns.push(info(el)));
    document.querySelectorAll('[data-testid], [data-action], [data-value], [data-type]').forEach(el => {
        if (!['BUTTON','INPUT','TEXTAREA','SELECT'].includes(el.tagName)) results.clickable.push(info(el));
    });
    document.querySelectorAll('a[href]').forEach(el => results.links.push(info(el)));
    document.querySelectorAll('video').forEach(el => results.videos.push(info(el)));
    document.querySelectorAll('img[src]').forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.width > 30 && r.height > 30) results.images.push(info(el));
    });

    results._summary = {
        total_buttons: results.buttons.length, total_inputs: results.inputs.length,
        total_textareas: results.textareas.length, total_file_inputs: results.file_inputs.length,
        total_contenteditable: results.contenteditable.length, total_dropdowns: results.dropdowns.length,
        total_clickable: results.clickable.length, total_links: results.links.length,
        total_videos: results.videos.length, total_images: results.images.length,
        page_title: document.title, page_url: window.location.href
    };
    return results;
}
return discoverElements();
"""


def scan_and_print(driver, label):
    print(f"\n[SCAN] {label}...")
    results = driver.execute_script(SCAN_SCRIPT)
    summary = results.get("_summary", {})

    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"  URL: {summary.get('page_url', '')}")
    print(f"{'=' * 60}")
    print(f"  Buttons:         {summary.get('total_buttons', 0)}")
    print(f"  Inputs:          {summary.get('total_inputs', 0)}")
    print(f"  Textareas:       {summary.get('total_textareas', 0)}")
    print(f"  File inputs:     {summary.get('total_file_inputs', 0)}")
    print(f"  Contenteditable: {summary.get('total_contenteditable', 0)}")
    print(f"  Dropdowns:       {summary.get('total_dropdowns', 0)}")
    print(f"  Clickable:       {summary.get('total_clickable', 0)}")
    print(f"  Videos:          {summary.get('total_videos', 0)}")
    print(f"  Images:          {summary.get('total_images', 0)}")
    print(f"{'=' * 60}\n")

    categories = [
        ("[BTN] BUTTONS", "buttons"),
        ("[INP] INPUTS", "inputs"),
        ("[TXT] TEXTAREAS", "textareas"),
        ("[FIL] FILE INPUTS", "file_inputs"),
        ("[EDT] CONTENTEDITABLE", "contenteditable"),
        ("[DRP] DROPDOWNS", "dropdowns"),
        ("[CLK] CLICKABLE", "clickable"),
        ("[VID] VIDEOS", "videos"),
    ]

    for title, key in categories:
        items = results.get(key, [])
        if not items:
            continue
        print(f"\n{title} ({len(items)})")
        print("-" * 60)
        for i, item in enumerate(items):
            if not item.get("visible", False):
                continue
            text = item.get("text", "").replace("\n", " ")[:80]
            sel = item.get("selector", "?")
            aria = item.get("aria-label", "") or ""
            testid = item.get("data-testid", "") or ""
            pos = item.get("position", {})

            print(f"  [{i+1}] {text or '(no text)'}")
            print(f"      selector: {sel}")
            if testid:
                print(f"      data-testid: {testid}")
            if aria:
                print(f"      aria-label: {aria}")
            if item.get("placeholder"):
                print(f"      placeholder: {item['placeholder']}")
            print(f"      pos: ({pos.get('x',0)}, {pos.get('y',0)}) {pos.get('w',0)}x{pos.get('h',0)}")
            print()

    return results


def main():
    all_results = {}

    driver = create_driver(headless=False)

    try:
        # 1. Inject cookies and navigate
        if COOKIES_PATH.exists():
            cookies = load_cookies()
            inject_cookies(driver, cookies)

        driver.get(FLOW_URL)
        print("[WAIT] Loading Flow dashboard...")
        human_delay(5, 8)

        # 2. Scan dashboard
        input("\n[STEP 1] Dashboard loaded. Nhan ENTER de quet Dashboard... ")
        all_results["dashboard"] = scan_and_print(driver, "DASHBOARD PAGE")

        # 3. Click "Du an moi" button
        print("\n[STEP 2] Clicking '+ Du an moi' button...")
        try:
            # Try multiple selectors for the new project button
            new_btn = None
            selectors_to_try = [
                ("xpath", "//*[contains(text(), 'Dự án mới')]"),
                ("xpath", "//*[contains(text(), 'New project')]"),
                ("xpath", "//button[contains(text(), 'mới')]"),
                ("xpath", "//button[contains(text(), 'New')]"),
                ("css", "button.sc-16c4830a-1"),
            ]
            for by_type, sel in selectors_to_try:
                try:
                    by = By.XPATH if by_type == "xpath" else By.CSS_SELECTOR
                    new_btn = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((by, sel))
                    )
                    if new_btn:
                        print(f"    Found with: {sel}")
                        break
                except Exception:
                    continue

            if new_btn:
                new_btn.click()
                print("[OK] Clicked new project button")
                human_delay(3, 5)
            else:
                print("[WARN] Could not find new project button")
                input("    Please click '+ Du an moi' manually, then press ENTER... ")
                human_delay(2, 3)
        except Exception as e:
            print(f"[ERR] {e}")
            input("    Please click '+ Du an moi' manually, then press ENTER... ")
            human_delay(2, 3)

        # 4. Scan editor page
        input("\n[STEP 3] Editor page should be visible. Nhan ENTER de quet Editor... ")
        all_results["editor"] = scan_and_print(driver, "PROJECT EDITOR PAGE")

        # 5. Try to find and open mode selector (Ingredients)
        print("\n[STEP 4] Looking for mode/workflow selectors...")
        input("    If there's a mode selector, click 'Ingredients to Video' manually if needed.\n    Then press ENTER to scan again... ")
        all_results["editor_with_mode"] = scan_and_print(driver, "EDITOR WITH MODE SELECTED")

        # 6. Save all results
        output_path = Path("logs") / "editor_selectors.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n[SAVED] All results saved to: {output_path}")

        # 7. Build suggested selectors from editor scan
        suggested = build_selectors(all_results)
        with open(SELECTORS_PATH, "w", encoding="utf-8") as f:
            json.dump(suggested, f, ensure_ascii=False, indent=2)
        print(f"[OK] Selectors updated: {SELECTORS_PATH}")

        input("\n  Nhan ENTER de dong browser... ")

    finally:
        close_driver(driver)


def build_selectors(all_results):
    """Build selectors from multiple page scans."""
    dashboard = all_results.get("dashboard", {})
    editor = all_results.get("editor_with_mode", all_results.get("editor", {}))

    d_buttons = dashboard.get("buttons", [])
    e_buttons = editor.get("buttons", [])
    e_file_inputs = editor.get("file_inputs", [])
    e_textareas = editor.get("textareas", [])
    e_contenteditable = editor.get("contenteditable", [])
    e_inputs = editor.get("inputs", [])
    e_dropdowns = editor.get("dropdowns", [])

    def find_btn(buttons, keywords, visible_only=True):
        for btn in buttons:
            if visible_only and not btn.get("visible", False):
                continue
            text = (btn.get("text", "") + " " + (btn.get("aria-label", "") or "")).lower()
            testid = (btn.get("data-testid", "") or "").lower()
            for kw in keywords:
                if kw in text or kw in testid:
                    return btn.get("selector", "")
        return ""

    # Filter real textareas (not recaptcha)
    real_textareas = [t for t in e_textareas
                      if t.get("visible") and "recaptcha" not in (t.get("id", "") or "").lower()]
    real_contenteditable = [c for c in e_contenteditable if c.get("visible")]

    prompt_selector = ""
    if real_textareas:
        prompt_selector = real_textareas[0].get("selector", "")
    elif real_contenteditable:
        prompt_selector = real_contenteditable[0].get("selector", "")

    file_input_sel = "input[type='file']"
    if e_file_inputs:
        file_input_sel = e_file_inputs[0].get("selector", file_input_sel)

    return {
        "_comment": "Auto-discovered from dashboard + editor scans",
        "new_project": {
            "btn": find_btn(d_buttons, ["moi", "new", "add"]),
            "description": "New project button on dashboard"
        },
        "ingredients_mode": {
            "menu_btn": find_btn(e_buttons, ["ingredient"]),
            "description": "Ingredients to Video mode button"
        },
        "upload": {
            "file_input": file_input_sel,
            "drop_zone": find_btn(e_buttons, ["upload", "drop", "add image", "add photo"]),
            "description": "File upload input"
        },
        "prompt": {
            "textarea": prompt_selector,
            "description": "Prompt input field"
        },
        "ratio": {
            "ratio_btn": find_btn(e_buttons, ["aspect", "ratio", "16:9", "9:16"]),
            "nine_sixteen": find_btn(e_buttons, ["9:16"]),
            "description": "Aspect ratio selector"
        },
        "style": {
            "selector": find_btn(e_buttons, ["style", "cinematic"]),
            "option_template": "",
            "description": "Style picker"
        },
        "generate": {
            "btn": find_btn(e_buttons, ["generate", "create", "make", "tao"]),
            "description": "Generate button"
        },
        "render": {
            "progress": "",
            "complete": "",
            "description": "Render status indicators"
        },
        "download": {
            "btn": find_btn(e_buttons, ["download", "save", "export", "tai"]),
            "description": "Download button"
        },
        "retry": {
            "btn": find_btn(e_buttons, ["retry", "try again", "thu lai"]),
            "description": "Retry button after render failure"
        },
        "login": {
            "pro_badge": find_btn(d_buttons, ["pro"]),
            "description": "Login indicators"
        }
    }


if __name__ == "__main__":
    main()

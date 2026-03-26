"""
Selector Discovery Script
--------------------------
Open Google Flow, scan DOM, list all interactive elements
with CSS selectors. Output to JSON + console.

Usage:
    venv/Scripts/python src/discover_selectors.py
    venv/Scripts/python src/discover_selectors.py --save
"""

import sys
import json
import time
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import FLOW_URL, COOKIES_PATH, SELECTORS_PATH
from src.cookie_manager import load_cookies, inject_cookies
from src.browser_controller import create_driver, close_driver, human_delay


SCAN_SCRIPT = r"""
function discoverElements() {
    const results = {
        buttons: [], inputs: [], textareas: [], file_inputs: [],
        dropdowns: [], clickable: [], contenteditable: [], links: [],
    };

    function getSelector(el) {
        if (el.id) return '#' + el.id;
        const testId = el.getAttribute('data-testid');
        if (testId) return '[data-testid="' + testId + '"]';
        const ariaLabel = el.getAttribute('aria-label');
        if (ariaLabel) return '[aria-label="' + ariaLabel + '"]';
        if (el.className && typeof el.className === 'string') {
            const classes = el.className.trim().split(/\s+/).filter(c => c.length > 0);
            if (classes.length > 0) {
                const sel = el.tagName.toLowerCase() + '.' + classes.join('.');
                try { if (document.querySelectorAll(sel).length === 1) return sel; } catch(e) {}
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
            text: (el.textContent || '').trim().substring(0, 100),
            type: el.type || null, name: el.name || null, id: el.id || null,
            'class': el.className && typeof el.className === 'string' ? el.className.trim().substring(0, 150) : null,
            'data-testid': el.getAttribute('data-testid'),
            'aria-label': el.getAttribute('aria-label'),
            role: el.getAttribute('role'),
            placeholder: el.placeholder || null,
            visible: r.width > 0 && r.height > 0,
            position: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) }
        };
    }

    document.querySelectorAll('button, [role="button"]').forEach(el => results.buttons.push(info(el)));
    document.querySelectorAll('input:not([type="file"]):not([type="hidden"])').forEach(el => results.inputs.push(info(el)));
    document.querySelectorAll('textarea').forEach(el => results.textareas.push(info(el)));
    document.querySelectorAll('input[type="file"]').forEach(el => results.file_inputs.push(info(el)));
    document.querySelectorAll('[contenteditable="true"]').forEach(el => results.contenteditable.push(info(el)));
    document.querySelectorAll('select, [role="listbox"], [role="combobox"]').forEach(el => results.dropdowns.push(info(el)));
    document.querySelectorAll('[data-testid], [data-action], [data-value]').forEach(el => {
        if (!['BUTTON','INPUT','TEXTAREA','SELECT'].includes(el.tagName)) results.clickable.push(info(el));
    });
    document.querySelectorAll('a[href]').forEach(el => results.links.push(info(el)));

    results._summary = {
        total_buttons: results.buttons.length, total_inputs: results.inputs.length,
        total_textareas: results.textareas.length, total_file_inputs: results.file_inputs.length,
        total_contenteditable: results.contenteditable.length, total_dropdowns: results.dropdowns.length,
        total_clickable: results.clickable.length, total_links: results.links.length,
        page_title: document.title, page_url: window.location.href
    };
    return results;
}
return discoverElements();
"""


def discover(url=None, save_to_file=False):
    url = url or FLOW_URL
    print(f"\n[SCAN] Selector Discovery - Scanning: {url}\n")

    driver = create_driver(headless=False)

    try:
        if COOKIES_PATH.exists():
            cookies = load_cookies()
            inject_cookies(driver, cookies)

        driver.get(url)
        print("[WAIT] Waiting for page to load...")
        human_delay(5, 8)

        input("\n[READY] Khi trang da load xong, nhan ENTER de quet DOM... ")

        print("[SCAN] Scanning DOM...")
        results = driver.execute_script(SCAN_SCRIPT)

        summary = results.get("_summary", {})
        print(f"\n{'=' * 60}")
        print(f"  SCAN RESULTS - {summary.get('page_title', 'Unknown')}")
        print(f"  URL: {summary.get('page_url', '')}")
        print(f"{'=' * 60}")
        print(f"  Buttons:         {summary.get('total_buttons', 0)}")
        print(f"  Inputs:          {summary.get('total_inputs', 0)}")
        print(f"  Textareas:       {summary.get('total_textareas', 0)}")
        print(f"  File inputs:     {summary.get('total_file_inputs', 0)}")
        print(f"  Contenteditable: {summary.get('total_contenteditable', 0)}")
        print(f"  Dropdowns:       {summary.get('total_dropdowns', 0)}")
        print(f"  Custom clickable:{summary.get('total_clickable', 0)}")
        print(f"  Links:           {summary.get('total_links', 0)}")
        print(f"{'=' * 60}\n")

        categories = [
            ("[BTN] BUTTONS", "buttons"),
            ("[INP] INPUTS", "inputs"),
            ("[TXT] TEXTAREAS", "textareas"),
            ("[FIL] FILE INPUTS", "file_inputs"),
            ("[EDT] CONTENTEDITABLE", "contenteditable"),
            ("[DRP] DROPDOWNS", "dropdowns"),
            ("[CLK] CUSTOM CLICKABLE", "clickable"),
        ]

        for title, key in categories:
            items = results.get(key, [])
            if not items:
                continue
            print(f"\n{title} ({len(items)})")
            print("-" * 50)
            for i, item in enumerate(items):
                if not item.get("visible", False):
                    continue
                text = item.get("text", "").replace("\n", " ")[:60]
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
                print(f"      pos: ({pos.get('x',0)}, {pos.get('y',0)}) {pos.get('w',0)}x{pos.get('h',0)}")
                print()

        output_path = Path("logs") / "discovered_selectors.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n[SAVED] Raw results saved to: {output_path}")

        if save_to_file:
            suggested = suggest_selectors(results)
            with open(SELECTORS_PATH, "w", encoding="utf-8") as f:
                json.dump(suggested, f, ensure_ascii=False, indent=2)
            print(f"[OK] Selectors updated: {SELECTORS_PATH}")

        print("\n" + "=" * 60)
        print("  TIP: Review logs/discovered_selectors.json for full details")
        print("=" * 60)
        input("\n  Nhan ENTER de dong browser... ")

    finally:
        close_driver(driver)


def suggest_selectors(results):
    buttons = results.get("buttons", [])
    file_inputs = results.get("file_inputs", [])
    textareas = results.get("textareas", [])
    contenteditable = results.get("contenteditable", [])

    def find_btn(keywords):
        for btn in buttons:
            text = (btn.get("text", "") + " " + (btn.get("aria-label", "") or "")).lower()
            testid = (btn.get("data-testid", "") or "").lower()
            for kw in keywords:
                if kw in text or kw in testid:
                    return btn.get("selector", "")
        return ""

    return {
        "_comment": "Auto-discovered selectors. Review and adjust as needed.",
        "ingredients_mode": {
            "menu_btn": find_btn(["ingredient"]),
            "description": "Ingredients to Video mode button"
        },
        "upload": {
            "file_input": file_inputs[0].get("selector", "input[type='file']") if file_inputs else "input[type='file']",
            "description": "File upload input"
        },
        "prompt": {
            "textarea": (
                textareas[0].get("selector", "") if textareas
                else contenteditable[0].get("selector", "") if contenteditable
                else "textarea, div[contenteditable='true']"
            ),
            "description": "Prompt input field"
        },
        "ratio": {
            "ratio_btn": find_btn(["aspect", "ratio"]),
            "nine_sixteen": find_btn(["9:16"]),
            "description": "Aspect ratio selector"
        },
        "style": {
            "selector": find_btn(["style", "cinematic"]),
            "option_template": "",
            "description": "Style picker"
        },
        "generate": {
            "btn": find_btn(["generate", "create", "make"]),
            "description": "Generate button"
        },
        "render": {
            "progress": "",
            "complete": "",
            "description": "Render status indicators"
        },
        "download": {
            "btn": find_btn(["download", "save", "export"]),
            "description": "Download button"
        },
        "login": {
            "avatar": find_btn(["avatar", "profile", "account"]),
            "sign_in": find_btn(["sign in", "log in"]),
            "description": "Login indicators"
        }
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-discover UI selectors")
    parser.add_argument("--url", type=str, default=None, help="URL to scan")
    parser.add_argument("--save", action="store_true", help="Auto-update selectors.json")
    args = parser.parse_args()
    discover(url=args.url, save_to_file=args.save)

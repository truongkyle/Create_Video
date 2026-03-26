"""
Test: Full Pipeline (Generate -> Render -> Download)
------------------------------------------------
Instantiates FlowAutomator and runs the pipeline for the first task.
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.browser_controller import create_driver, close_driver
from src.json_handler import load_tasks, save_tasks
from src.flow_automator import FlowAutomator
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

def step_log(num, title):
    print(f"\n{'=' * 60}")
    print(f"  STEP {num}: {title}")
    print(f"{'=' * 60}")

def pause(msg="ENTER..."):
    input(f"\n  >> {msg} ")

def main():
    tasks = load_tasks()
    if not tasks:
        print("No tasks found in sample_input.json")
        return
        
    task = tasks[0]
    print(f"\n[INFO] Running Full Pipeline for: {task.get('ten_san_pham')}")

    # Set headless=False so we can observe the generation process
    driver = create_driver(headless=False)
    automator = FlowAutomator(driver)

    try:
        steps = [
            ("navigate", automator.step_navigate),
            ("create_project", automator.step_create_project),
            ("upload_to_prompt", automator.step_upload_to_prompt),
            ("enter_prompt", automator.step_enter_prompt),
            ("configure_settings", automator.step_configure_settings),
            ("generate", automator.step_generate),
            ("wait_render", automator.step_wait_render),
            ("download", automator.step_download)
        ]
        
        for i, (name, func) in enumerate(steps, 1):
            step_log(i, name.upper())
            automator.current_step = name
            func(task)
            print(f"  [OK] Step '{name}' completed.")
            
            # Optional: Log progress before generation
            if name == "configure_settings":
                print("  >> Settings Configured. Proceeding to Generation automatically...")
            elif name == "generate":
                print("  >> Waiting for render. Please wait (this could take a few minutes)...")
                
    except Exception as e:
        print(f"\n[FAIL] Pipeline failed at step {automator.current_step}: {e}")
        import traceback
        traceback.print_exc()
        print("Closing browser...")
    finally:
        # Don't save tasks right now, since it might overwrite status to 'processing' without finishing
        # save_tasks(tasks)
        close_driver(driver)

if __name__ == "__main__":
    main()

"""
Main Orchestrator for Google Flow Video Automation
--------------------------------------------------
Reads tasks from data/sample_input.json.
Iterates over pending tasks, launching the automation pipeline for each.
Updates the JSON file with success/failure status.
"""

import sys
import time
import traceback
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.browser_controller import create_driver, close_driver
from src.json_handler import load_tasks, save_tasks
from src.flow_automator import FlowAutomator
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("main")

def run_task(driver, task):
    """Executes the full pipeline for a single task."""
    automator = FlowAutomator(driver)
    
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
    
    for name, func in steps:
        logger.info(f"--- Executing Step: {name.upper()} ---")
        automator.current_step = name
        func(task)

def main():
    logger.info("Starting Google Flow Auto-Generation Pipeline")
    
    while True:
        tasks = load_tasks()
        
        # Filter for tasks that are not yet successfully completed
        pending_tasks = [t for t in tasks if t.get("status") not in ["completed"]]
        
        if not pending_tasks:
            logger.info("🎉 All tasks completed! No pending jobs found. Exiting pipeline.")
            break
            
        task = pending_tasks[0]
        # Locate the exact index so we can update the source list correctly
        task_idx = next(i for i, t in enumerate(tasks) if t.get("d_id") == task.get("d_id"))
        
        logger.info(f"\n{'='*60}\n🚀 Starting Task: {task.get('ten_san_pham')} (ID: {task.get('d_id')})\n{'='*60}")
        
        tasks[task_idx]["status"] = "processing"
        save_tasks(tasks)
        
        driver = None
        try:
            # Booting a fresh browser session for each task guarantees zero state contamination
            # and bypasses SPA memory leaks or cached React UI staleness.
            driver = create_driver(headless=False)
            
            run_task(driver, tasks[task_idx])
            
            # If no exception was thrown, the full pipeline passed successfully
            tasks[task_idx]["status"] = "completed"
            logger.info(f"✅ Task {task.get('d_id')} finished successfully!")
            
        except Exception as e:
            logger.error(f"❌ Task {task.get('d_id')} failed: {e}")
            traceback.print_exc()
            tasks[task_idx]["status"] = "failed"
            tasks[task_idx]["error_reason"] = str(e)  # Record why it failed so user can adapt
            
        finally:
            save_tasks(tasks)
            if driver:
                logger.info("Closing browser session ahead of next task cycle...")
                try:
                    close_driver(driver)
                except Exception:
                    pass # Ignore shutdown bugs like WinError 6
                
        # To avoid triggering Anti-Bot load balancers, a short delay between major browser sessions
        logger.info("Waiting 15 seconds before booting next profile cycle...")
        time.sleep(15)

if __name__ == "__main__":
    main()

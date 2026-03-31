"""
Automation API — Bridge between GUI and the automation engine.
Wraps FlowAutomator + RetryEngine for GUI-friendly execution
with callbacks, threading, and stop mechanism.
"""

import logging
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.utils import setup_logger
from src.config import FLOW_URL, COOKIES_PATH
from src.cookie_manager import load_cookies, inject_cookies, validate_login, save_cookies, has_valid_cookies
from src.json_handler import load_tasks, update_task_status, get_images_from_folder
from src.browser_controller import create_driver, close_driver, human_delay, set_download_dir
from src.flow_automator import FlowAutomator
from src.retry_engine import RetryEngine
from src.download_manager import setup_download_dir

logger = logging.getLogger("flow_automation")


PIPELINE_STEPS = [
    "navigate", "create_project", "upload_images",
    "enter_prompt", "configure_settings", "generate",
    "wait_render", "download"
]


class GUILogHandler(logging.Handler):
    """Captures log records and forwards them to a GUI callback."""

    def __init__(self, callback, worker_id=None):
        super().__init__()
        self.callback = callback
        self.worker_id = worker_id

    def emit(self, record):
        msg = self.format(record)
        if self.worker_id is not None:
            msg = f"[W{self.worker_id}] {msg}"
        try:
            self.callback(msg, record.levelname)
        except Exception:
            pass


class AutomationAPI:
    """High-level API to run automation tasks from the GUI."""

    def __init__(self):
        self._stop_event = threading.Event()
        self._running = False
        self._threads = []
        self._lock = threading.Lock()

        # Callbacks (set by GUI before calling run_tasks)
        self.on_log = None           # (message: str, level: str)
        self.on_step_change = None   # (task_name: str, step_name: str, step_idx: int, total: int, worker_id: int)
        self.on_task_complete = None  # (task: dict, status: str, error: str|None)
        self.on_progress = None      # (completed: int, total: int)
        self.on_finished = None      # (results: dict)

    @property
    def is_running(self):
        return self._running

    def check_ready(self):
        """Check if the system is ready to run (cookies exist and valid)."""
        is_valid, msg = has_valid_cookies()
        return is_valid, msg

    def stop(self):
        """Signal all workers to stop after their current step."""
        logger.info("⏹ Stop requested — workers will finish current step then halt")
        self._stop_event.set()

    def run_tasks(self, tasks, all_tasks, headless=True, max_workers=1):
        """
        Run tasks in a background thread.
        
        Args:
            tasks: List of task dicts to process
            all_tasks: Full task list (for updating JSON)
            headless: Run browser in headless mode
            max_workers: 1 = sequential, >1 = parallel workers
        """
        if self._running:
            self._emit_log("⚠️ Pipeline đang chạy. Vui lòng dừng trước khi chạy lại.", "WARNING")
            return

        self._stop_event.clear()
        self._running = True

        thread = threading.Thread(
            target=self._run_tasks_thread,
            args=(tasks, all_tasks, headless, max_workers),
            daemon=True,
        )
        thread.start()

    def _run_tasks_thread(self, tasks, all_tasks, headless, max_workers):
        """Main execution thread — runs sequential or parallel."""
        results = {"success": 0, "failed": 0, "skipped": 0}

        try:
            if max_workers <= 1:
                self._run_sequential(tasks, all_tasks, headless, results)
            else:
                self._run_parallel(tasks, all_tasks, headless, max_workers, results)
        except Exception as e:
            self._emit_log(f"❌ Fatal error: {e}", "ERROR")
            logger.error(traceback.format_exc())
        finally:
            self._running = False
            self._emit_log(
                f"\n{'=' * 50}\n"
                f"  KẾT QUẢ: ✅ {results['success']}  ❌ {results['failed']}  ⏭ {results['skipped']}\n"
                f"{'=' * 50}", "INFO"
            )
            if self.on_finished:
                try:
                    self.on_finished(results)
                except Exception:
                    pass

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  SEQUENTIAL MODE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _run_sequential(self, tasks, all_tasks, headless, results):
        """Process tasks one-by-one with a single Chrome instance."""
        self._emit_log("🔄 Chế độ: Tuần tự (1 Chrome)", "INFO")

        driver = create_driver(headless=headless)
        log_handler = self._attach_log_handler(worker_id=None)

        try:
            if not self._login(driver):
                self._emit_log("❌ Đăng nhập thất bại. Kiểm tra cookies.", "ERROR")
                return

            for idx, task in enumerate(tasks):
                if self._stop_event.is_set():
                    self._emit_log("⏹ Pipeline đã dừng theo yêu cầu", "WARNING")
                    break

                self._process_single_task(driver, task, all_tasks, idx, len(tasks), results, worker_id=0)

        finally:
            self._safe_save_cookies(driver)
            close_driver(driver)
            self._detach_log_handler(log_handler)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  PARALLEL MODE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _run_parallel(self, tasks, all_tasks, headless, max_workers, results):
        """Process tasks with multiple Chrome instances."""
        actual_workers = min(max_workers, len(tasks))
        self._emit_log(f"⚡ Chế độ: Song song ({actual_workers} workers)", "INFO")

        # Split tasks into chunks for each worker
        chunks = [[] for _ in range(actual_workers)]
        for i, task in enumerate(tasks):
            chunks[i % actual_workers].append(task)

        with ThreadPoolExecutor(max_workers=actual_workers) as executor:
            futures = {}
            for worker_id, chunk in enumerate(chunks):
                if chunk:
                    future = executor.submit(
                        self._worker_run, chunk, all_tasks, headless, worker_id, results
                    )
                    futures[future] = worker_id

            for future in as_completed(futures):
                worker_id = futures[future]
                try:
                    future.result()
                except Exception as e:
                    self._emit_log(f"❌ Worker {worker_id} crashed: {e}", "ERROR")

    def _worker_run(self, tasks, all_tasks, headless, worker_id, results):
        """Single worker thread — has its own Chrome instance."""
        log_handler = self._attach_log_handler(worker_id=worker_id)
        driver = create_driver(headless=headless)

        try:
            if not self._login(driver):
                self._emit_log(f"❌ [W{worker_id}] Đăng nhập thất bại", "ERROR")
                return

            for idx, task in enumerate(tasks):
                if self._stop_event.is_set():
                    self._emit_log(f"⏹ [W{worker_id}] Dừng theo yêu cầu", "WARNING")
                    break

                self._process_single_task(driver, task, all_tasks, idx, len(tasks), results, worker_id)

        finally:
            self._safe_save_cookies(driver)
            close_driver(driver)
            self._detach_log_handler(log_handler)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  CORE TASK PROCESSING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _process_single_task(self, driver, task, all_tasks, idx, total, results, worker_id):
        """Execute the 8-step pipeline for a single task."""
        product = task.get("ten_san_pham", f"Task {idx + 1}")
        global_idx = all_tasks.index(task) if task in all_tasks else -1

        self._emit_log(f"\n{'─' * 40}", "INFO")
        self._emit_log(f"📹 [{idx + 1}/{total}] {product}", "INFO")
        self._emit_log(f"{'─' * 40}", "INFO")

        # Get images
        images = get_images_from_folder(task.get("link_folder_anh", ""))
        if not images:
            self._emit_log(f"⏭ Bỏ qua '{product}': không tìm thấy ảnh", "WARNING")
            if global_idx >= 0:
                update_task_status(all_tasks, global_idx, "skipped", error="No images found")
            with self._lock:
                results["skipped"] += 1
            if self.on_task_complete:
                self.on_task_complete(task, "skipped", "No images found")
            return

        task["_images"] = images

        # Setup download dir
        download_dir = task.get("link_folder_video", "")
        if download_dir:
            setup_download_dir(download_dir)
            set_download_dir(driver, download_dir)

        # Update status
        if global_idx >= 0:
            update_task_status(all_tasks, global_idx, "processing")

        # Create automator and retry engine
        automator = FlowAutomator(driver)
        retry_engine = RetryEngine(driver, automator)

        # Hook step notifications
        original_execute = retry_engine._execute_steps_with_retry

        def patched_execute(t):
            steps = automator.STEPS
            for i, step in enumerate(steps):
                if self._stop_event.is_set():
                    raise RuntimeError("Pipeline stopped by user")

                if self.on_step_change:
                    self.on_step_change(product, step, i, len(steps), worker_id)

                automator.current_step = step
                success = retry_engine._retry_single_step(step, t)
                if success:
                    automator.completed_steps.append(step)
                    human_delay()
                else:
                    raise RuntimeError(f"Step '{step}' failed after retries")

            logger.info("✅ All steps completed successfully")
            return True

        retry_engine._execute_steps_with_retry = patched_execute

        try:
            retry_engine.execute_task_with_retry(task)

            # step_download() in FlowAutomator handles the entire download process
            # (both 'zip' and 'individual' methods). No need to wait/verify here.
            if global_idx >= 0:
                update_task_status(all_tasks, global_idx, "completed")

            with self._lock:
                results["success"] += 1
            self._emit_log(f"✅ Hoàn tất: {product}", "INFO")

            if self.on_task_complete:
                self.on_task_complete(task, "completed", None)
            if self.on_progress:
                with self._lock:
                    done = results["success"] + results["failed"] + results["skipped"]
                self.on_progress(done, len(all_tasks))

        except Exception as e:
            error_msg = str(e)
            self._emit_log(f"❌ Lỗi: {product} — {error_msg}", "ERROR")
            logger.debug(traceback.format_exc())

            if global_idx >= 0:
                update_task_status(all_tasks, global_idx, "failed", error=error_msg)

            with self._lock:
                results["failed"] += 1

            if self.on_task_complete:
                self.on_task_complete(task, "failed", error_msg)

        # Delay between tasks
        if not self._stop_event.is_set():
            human_delay(3, 5)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  HELPERS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _login(self, driver):
        """Inject cookies and validate login. Returns True if logged in."""
        try:
            if not COOKIES_PATH.exists():
                self._emit_log("❌ File cookies.json không tồn tại", "ERROR")
                return False

            cookies = load_cookies()
            inject_cookies(driver, cookies)
            driver.get(FLOW_URL)
            human_delay(3, 5)

            if validate_login(driver):
                self._emit_log("✅ Đăng nhập thành công", "INFO")
                return True
            else:
                self._emit_log("❌ Cookies hết hạn hoặc không hợp lệ", "ERROR")
                return False
        except Exception as e:
            self._emit_log(f"❌ Lỗi đăng nhập: {e}", "ERROR")
            return False

    def _safe_save_cookies(self, driver):
        try:
            save_cookies(driver)
        except Exception:
            pass

    def _emit_log(self, message, level="INFO"):
        if self.on_log:
            try:
                self.on_log(message, level)
            except Exception:
                pass

    def _attach_log_handler(self, worker_id=None):
        if not self.on_log:
            return None
        handler = GUILogHandler(self.on_log, worker_id=worker_id)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logging.getLogger("flow_automation").addHandler(handler)
        return handler

    def _detach_log_handler(self, handler):
        if handler:
            logging.getLogger("flow_automation").removeHandler(handler)

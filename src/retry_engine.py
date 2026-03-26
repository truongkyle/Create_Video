import logging
import time
import traceback

from src.config import MAX_STEP_RETRY, MAX_RELOAD_RETRY, MAX_FULL_RESTART, FLOW_URL
from src.browser_controller import human_delay

logger = logging.getLogger("flow_automation")


class RetryEngine:
    def __init__(self, driver, automator):
        self.driver = driver
        self.automator = automator

    def execute_task_with_retry(self, task):
        last_error = None

        # ── Phase 1: Execute all steps with step-level retry ──
        try:
            return self._execute_steps_with_retry(task)
        except Exception as e:
            last_error = e
            logger.error(f"Step-level retry exhausted: {e}")

        # ── Phase 2: Reload + retry from failed step ──
        failed_step = self.automator.current_step
        for reload_attempt in range(1, MAX_RELOAD_RETRY + 1):
            logger.info(f"🔄 Reload retry {reload_attempt}/{MAX_RELOAD_RETRY}")
            try:
                self.driver.refresh()
                human_delay(3, 5)
                self.automator.execute_from_step(failed_step, task)
                return True
            except Exception as e:
                last_error = e
                logger.error(f"Reload retry {reload_attempt} failed: {e}")

        # ── Phase 3: Full restart ──
        for restart_attempt in range(1, MAX_FULL_RESTART + 1):
            logger.info(f"🔁 Full restart {restart_attempt}/{MAX_FULL_RESTART}")
            try:
                self.driver.get(FLOW_URL)
                human_delay(3, 5)
                self.automator.completed_steps = []
                self.automator.execute_all(task)
                return True
            except Exception as e:
                last_error = e
                logger.error(f"Full restart {restart_attempt} failed: {e}")

        logger.error(f"❌ All retry strategies exhausted. Last error: {last_error}")
        raise last_error

    def _execute_steps_with_retry(self, task):
        steps = self.automator.STEPS
        i = 0

        while i < len(steps):
            step = steps[i]
            self.automator.current_step = step

            success = self._retry_single_step(step, task)
            if success:
                self.automator.completed_steps.append(step)
                i += 1
                human_delay()
            else:
                raise RuntimeError(f"Step '{step}' failed after {MAX_STEP_RETRY} retries")

        logger.info("✅ All steps completed successfully")
        return True

    def _retry_single_step(self, step_name, task):
        method = getattr(self.automator, f"step_{step_name}")
        is_render = step_name == "wait_render"
        max_retries = MAX_STEP_RETRY

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"▶ Step: {step_name} (attempt {attempt}/{max_retries})")
                method(task)
                return True
            except Exception as e:
                logger.warning(
                    f"Step '{step_name}' attempt {attempt} failed: {e}"
                )
                if attempt < max_retries:
                    wait = 2 ** attempt
                    logger.info(f"Waiting {wait}s before retry...")
                    time.sleep(wait)

                if is_render and attempt == max_retries:
                    logger.info("Render retry exhausted — checking for partial results")
                    self._try_download_completed(task)

        return False

    def _try_download_completed(self, task):
        try:
            self.automator.step_download(task)
            logger.info("Downloaded partially completed video")
        except Exception:
            logger.debug("No completed video to download after render failure")

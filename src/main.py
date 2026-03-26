import sys
import argparse
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils import setup_logger
from src.config import FLOW_URL, COOKIES_PATH
from src.cookie_manager import load_cookies, inject_cookies, validate_login, first_time_login, save_cookies
from src.json_handler import load_tasks, get_pending_tasks, update_task_status, get_images_from_folder
from src.browser_controller import create_driver, close_driver, human_delay, set_download_dir
from src.flow_automator import FlowAutomator
from src.retry_engine import RetryEngine
from src.download_manager import setup_download_dir, wait_for_download, rename_video, verify_download


def parse_args():
    parser = argparse.ArgumentParser(description="Google Flow Video Automation")
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--limit", type=int, default=0, help="Max videos to process (0=all)")
    parser.add_argument("--input", type=str, default=None, help="Path to JSON input file")
    parser.add_argument("--discover", action="store_true", help="Discovery mode: pause at each step")
    return parser.parse_args()


def main():
    args = parse_args()
    logger = setup_logger()

    logger.info("=" * 60)
    logger.info("  Google Flow Video Automation — Starting")
    logger.info("=" * 60)

    # ── Load tasks ──
    tasks = load_tasks(args.input)
    pending = get_pending_tasks(tasks)

    if not pending:
        logger.info("No pending tasks. Exiting.")
        return

    if args.limit > 0:
        pending = pending[:args.limit]
    logger.info(f"Processing {len(pending)} tasks")

    # ── Create browser ──
    headless = args.headless and not args.headed
    driver = create_driver(headless=headless)

    try:
        # ── Handle login ──
        if COOKIES_PATH.exists() and COOKIES_PATH.stat().st_size > 10:
            cookies = load_cookies()
            inject_cookies(driver, cookies)
            driver.get(FLOW_URL)
            human_delay(3, 5)

            if not validate_login(driver):
                logger.warning("Cookies expired — manual login required")
                first_time_login(driver, FLOW_URL)
        else:
            driver.get(FLOW_URL)
            human_delay(2, 3)
            first_time_login(driver, FLOW_URL)

        # ── Process tasks ──
        results = {"success": 0, "failed": 0, "skipped": 0}

        for task_idx, task in enumerate(pending):
            global_idx = tasks.index(task)
            product = task.get("ten_san_pham", f"Task {task_idx + 1}")

            logger.info(f"\n{'─' * 50}")
            logger.info(f"📹 [{task_idx + 1}/{len(pending)}] {product}")
            logger.info(f"{'─' * 50}")

            # Get images
            images = get_images_from_folder(task.get("link_folder_anh", ""))
            if not images:
                logger.warning(f"Skipping '{product}': no images found")
                update_task_status(tasks, global_idx, "skipped", error="No images found")
                results["skipped"] += 1
                continue

            task["_images"] = images

            # Setup download dir
            download_dir = task.get("link_folder_video", "")
            if download_dir:
                setup_download_dir(download_dir)
                set_download_dir(driver, download_dir)

            # Update status
            update_task_status(tasks, global_idx, "processing")

            # Execute with retry
            automator = FlowAutomator(driver)
            retry_engine = RetryEngine(driver, automator)

            try:
                retry_engine.execute_task_with_retry(task)

                # Wait for download and rename
                if download_dir:
                    video_path = wait_for_download(download_dir)
                    if video_path and verify_download(video_path):
                        final_path = rename_video(video_path, product, download_dir)
                        update_task_status(
                            tasks, global_idx, "completed",
                            video_path=final_path
                        )
                        results["success"] += 1
                        logger.info(f"✅ Completed: {product}")
                    else:
                        update_task_status(
                            tasks, global_idx, "completed",
                            error="Download verification failed"
                        )
                        results["success"] += 1
                else:
                    update_task_status(tasks, global_idx, "completed")
                    results["success"] += 1

            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Failed: {product} — {error_msg}")
                logger.debug(traceback.format_exc())
                update_task_status(tasks, global_idx, "failed", error=error_msg)
                results["failed"] += 1

            # Delay between tasks
            if task_idx < len(pending) - 1:
                human_delay(5, 10)

        # ── Summary ──
        logger.info(f"\n{'=' * 60}")
        logger.info(f"  SUMMARY")
        logger.info(f"  ✅ Success: {results['success']}")
        logger.info(f"  ❌ Failed:  {results['failed']}")
        logger.info(f"  ⏭  Skipped: {results['skipped']}")
        logger.info(f"{'=' * 60}")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.debug(traceback.format_exc())
    finally:
        # Save cookies before closing
        try:
            save_cookies(driver)
        except Exception:
            pass
        close_driver(driver)


if __name__ == "__main__":
    main()

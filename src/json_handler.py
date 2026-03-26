import json
import logging
from pathlib import Path

from src.config import JSON_INPUT_PATH
from src.utils import timestamp_now, is_image_file

logger = logging.getLogger("flow_automation")


def load_tasks(path=None):
    path = path or JSON_INPUT_PATH
    with open(path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    logger.info(f"Loaded {len(tasks)} tasks from {path}")
    return tasks


def save_tasks(tasks, path=None):
    path = path or JSON_INPUT_PATH
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
    logger.debug(f"Saved {len(tasks)} tasks to {path}")


def get_pending_tasks(tasks):
    pending = [t for t in tasks if t.get("status") == "pending"]
    logger.info(f"Found {len(pending)} pending tasks")
    return pending


def update_task_status(tasks, index, status, error=None, video_path=None):
    tasks[index]["status"] = status
    tasks[index]["timestamp"] = timestamp_now()
    if error is not None:
        tasks[index]["error"] = error
    if video_path is not None:
        tasks[index]["video_path"] = video_path
    save_tasks(tasks)
    logger.info(f"Task {index} → status={status}")


def get_images_from_folder(folder_path):
    folder = Path(folder_path)
    if not folder.exists():
        logger.error(f"Image folder not found: {folder}")
        return []

    images = sorted(
        [str(f) for f in folder.iterdir() if f.is_file() and is_image_file(f)]
    )
    logger.info(f"Found {len(images)} images in {folder}")
    return images

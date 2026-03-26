import logging
import time
from pathlib import Path

from src.config import DOWNLOAD_TIMEOUT

logger = logging.getLogger("flow_automation")


def setup_download_dir(folder_path):
    folder = Path(folder_path)
    folder.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Download dir ready: {folder}")
    return folder


def wait_for_download(download_dir, timeout=None):
    timeout = timeout or DOWNLOAD_TIMEOUT
    download_dir = Path(download_dir)
    start = time.time()

    while time.time() - start < timeout:
        files = list(download_dir.glob("*"))
        temp_files = [f for f in files if f.suffix in (".crdownload", ".tmp", ".part")]
        video_files = [f for f in files if f.suffix in (".mp4", ".webm", ".mov")]

        if video_files and not temp_files:
            newest = max(video_files, key=lambda f: f.stat().st_mtime)
            logger.info(f"Download complete: {newest.name}")
            return str(newest)

        time.sleep(2)

    logger.warning(f"Download timeout after {timeout}s")
    return None


def rename_video(src_path, product_name, dest_dir=None):
    src = Path(src_path)
    if not src.exists():
        logger.error(f"Source file not found: {src}")
        return None

    safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in product_name)
    safe_name = safe_name.strip()[:100]
    new_name = f"{safe_name}{src.suffix}"

    dest_dir = Path(dest_dir) if dest_dir else src.parent
    dest = dest_dir / new_name

    counter = 1
    while dest.exists():
        dest = dest_dir / f"{safe_name}_{counter}{src.suffix}"
        counter += 1

    src.rename(dest)
    logger.info(f"Renamed: {src.name} → {dest.name}")
    return str(dest)


def verify_download(file_path):
    path = Path(file_path)
    if not path.exists():
        return False
    if path.stat().st_size < 1024:
        logger.warning(f"Downloaded file too small: {path.stat().st_size} bytes")
        return False
    return True

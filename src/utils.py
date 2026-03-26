import logging
import sys
from datetime import datetime
from pathlib import Path

from src.config import LOG_DIR


def setup_logger(name="flow_automation"):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{name}_{datetime.now():%Y%m%d_%H%M%S}.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


def timestamp_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_image_file(path):
    return Path(path).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

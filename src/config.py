import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / "config" / ".env")


def _get(key, default=None, cast=str):
    val = os.getenv(key, default)
    if val is None:
        return default
    return cast(val)


COOKIES_PATH = BASE_DIR / _get("COOKIES_PATH", "config/cookies.json")
JSON_INPUT_PATH = BASE_DIR / _get("JSON_INPUT_PATH", "data/sample_input.json")
SELECTORS_PATH = BASE_DIR / _get("SELECTORS_PATH", "config/selectors.json")
LOG_DIR = BASE_DIR / _get("LOG_DIR", "logs")

FLOW_URL = _get("FLOW_URL", "https://labs.google/fx/tools/flow")

HEADLESS = _get("HEADLESS", "false").lower() == "true"
WINDOW_WIDTH = _get("WINDOW_WIDTH", "1440", int)
WINDOW_HEIGHT = _get("WINDOW_HEIGHT", "900", int)

HUMAN_DELAY_MIN = _get("HUMAN_DELAY_MIN", "2", float)
HUMAN_DELAY_MAX = _get("HUMAN_DELAY_MAX", "5", float)
PAGE_LOAD_TIMEOUT = _get("PAGE_LOAD_TIMEOUT", "30", int)
RENDER_TIMEOUT = _get("RENDER_TIMEOUT", "600", int)
DOWNLOAD_TIMEOUT = _get("DOWNLOAD_TIMEOUT", "120", int)

MAX_STEP_RETRY = _get("MAX_STEP_RETRY", "3", int)
MAX_RELOAD_RETRY = _get("MAX_RELOAD_RETRY", "3", int)
MAX_FULL_RESTART = _get("MAX_FULL_RESTART", "1", int)

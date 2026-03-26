"""
Entry point for the Video Automation Desktop GUI.
Usage: python run_gui.py
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gui.app import main

if __name__ == "__main__":
    main()

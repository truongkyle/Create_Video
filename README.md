# Google Flow Video Automation

Automated system for generating videos on Google Flow (Veo engine) using Selenium and undetected-chromedriver.

## Features
- **Anti-Detect Profile**: Bypasses bot detection using persistent, specialized Chrome profiles.
- **Robust UI Interaction**: Directly interacts with the React-based Google Flow UI, avoiding native Windows file dialogs via JS interception.
- **Automated Parameter Selection**: Configures generation settings (Model, Ratio, Mode, Video count) dynamically via a JSON configuration file.
- **Render Polling & Download**: Automatically monitors video rendering and downloads locally upon completion.

## Setup
1. Create a Python virtual environment: `python -m venv venv`
2. Install dependencies: `pip install -r requirements.txt`
3. Add your session cookies to `config/cookies.json` and environmental variables to `.env`.

## Usage
Run the main execution script or test individual steps:
- `python src/test_steps.py` to run full end-to-end testing pipeline.

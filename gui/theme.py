"""
Theme constants for the Video Automation GUI.
Dark theme color palette, fonts, and sizing.
"""

COLORS = {
    "bg_dark": "#0d1117",
    "bg_card": "#161b22",
    "bg_input": "#21262d",
    "bg_hover": "#30363d",
    "border": "#30363d",
    "text_primary": "#e6edf3",
    "text_secondary": "#8b949e",
    "text_muted": "#484f58",
    "accent": "#58a6ff",
    "accent_hover": "#79c0ff",
    "success": "#3fb950",
    "warning": "#d29922",
    "error": "#f85149",
    "pending": "#d29922",
}

FONTS = {
    "title": ("Segoe UI", 20, "bold"),
    "heading": ("Segoe UI", 15, "bold"),
    "subheading": ("Segoe UI", 13, "bold"),
    "body": ("Segoe UI", 12),
    "small": ("Segoe UI", 11),
    "mono": ("Consolas", 11),
}

SIZES = {
    "window_width": 1200,
    "window_height": 800,
    "sidebar_width": 280,
    "padding": 16,
    "padding_sm": 8,
    "corner_radius": 8,
    "button_height": 36,
}

STATUS_COLORS = {
    "pending": COLORS["pending"],
    "processing": COLORS["accent"],
    "completed": COLORS["success"],
    "failed": COLORS["error"],
    "skipped": COLORS["text_muted"],
}

STEP_COLORS = {
    "waiting": COLORS["text_muted"],
    "running": COLORS["accent"],
    "done": COLORS["success"],
    "error": COLORS["error"],
}

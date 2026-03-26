"""
Main GUI Application — Video Automation Desktop App
CustomTkinter window with 3 tabs: Cấu hình | Tạo Video | Tiến trình
"""

import sys
from pathlib import Path

import customtkinter as ctk

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gui.theme import COLORS, FONTS, SIZES


from gui.panels.config_panel import ConfigPanel
from gui.panels.project_panel import ProjectPanel


class VideoAutomationApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self._configure_window()
        self._create_header()
        self._create_tabs()
        self._create_panels()

    def _configure_window(self):
        self.title("Video Automation — Google Flow")
        self.geometry(f"{SIZES['window_width']}x{SIZES['window_height']}")
        self.minsize(900, 600)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.configure(fg_color=COLORS["bg_dark"])

    def _create_header(self):
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], height=56, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        title_label = ctk.CTkLabel(
            header,
            text="🎬 Video Automation",
            font=FONTS["title"],
            text_color=COLORS["text_primary"],
        )
        title_label.pack(side="left", padx=SIZES["padding"])

        self.status_label = ctk.CTkLabel(
            header,
            text="⚪ Sẵn sàng",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
        )
        self.status_label.pack(side="right", padx=SIZES["padding"])

    def _create_tabs(self):
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=COLORS["bg_dark"],
            segmented_button_fg_color=COLORS["bg_card"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_hover"],
            segmented_button_unselected_color=COLORS["bg_card"],
            segmented_button_unselected_hover_color=COLORS["bg_hover"],
            corner_radius=SIZES["corner_radius"],
        )
        self.tabview.pack(fill="both", expand=True, padx=SIZES["padding"], pady=(SIZES["padding_sm"], SIZES["padding"]))

        self.tab_config = self.tabview.add("⚙️ Cấu hình")
        self.tab_project = self.tabview.add("📹 Tạo Video")
        self.tab_progress = self.tabview.add("📊 Tiến trình")

    def _create_panels(self):
        # Phase 2: Config Panel
        self.config_panel = ConfigPanel(self.tab_config)

        # Phase 3-4: Project Panel
        self.project_panel = ProjectPanel(self.tab_project)

        # Placeholder for Phase 6
        ctk.CTkLabel(
            self.tab_progress,
            text="Tab Tiến trình — sẽ được xây dựng ở Phase 6",
            font=FONTS["body"], text_color=COLORS["text_muted"],
        ).pack(expand=True)

    def set_status(self, text, color=None):
        self.status_label.configure(text=text, text_color=color or COLORS["text_secondary"])


def main():
    app = VideoAutomationApp()
    app.mainloop()


if __name__ == "__main__":
    main()

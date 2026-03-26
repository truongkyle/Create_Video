"""
Main GUI Application — Video Automation Desktop App
CustomTkinter window with 3 tabs: Cấu hình | Tạo Video | Tiến trình
Wires together: ConfigPanel, ProjectPanel, ProgressPanel, and AutomationAPI.
"""

import sys
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gui.theme import COLORS, FONTS, SIZES
from gui.panels.config_panel import ConfigPanel
from gui.panels.project_panel import ProjectPanel
from gui.panels.progress_panel import ProgressPanel
from src.automation_api import AutomationAPI


class VideoAutomationApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.api = AutomationAPI()
        self._configure_window()
        self._create_header()
        self._create_tabs()
        self._create_panels()
        self._connect_signals()
        self._bind_shortcuts()

    def _configure_window(self):
        self.title("Video Automation — Google Flow")
        self.geometry(f"{SIZES['window_width']}x{SIZES['window_height']}")
        self.minsize(900, 600)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.configure(fg_color=COLORS["bg_dark"])
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_header(self):
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], height=56, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="🎬 Video Automation",
            font=FONTS["title"], text_color=COLORS["text_primary"],
        ).pack(side="left", padx=SIZES["padding"])

        self.status_label = ctk.CTkLabel(
            header, text="⚪ Sẵn sàng",
            font=FONTS["body"], text_color=COLORS["text_secondary"],
        )
        self.status_label.pack(side="right", padx=SIZES["padding"])

    def _create_tabs(self):
        self.tabview = ctk.CTkTabview(
            self, fg_color=COLORS["bg_dark"],
            segmented_button_fg_color=COLORS["bg_card"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_hover"],
            segmented_button_unselected_color=COLORS["bg_card"],
            segmented_button_unselected_hover_color=COLORS["bg_hover"],
            corner_radius=SIZES["corner_radius"],
            command=self._on_tab_change,
        )
        self.tabview.pack(fill="both", expand=True, padx=SIZES["padding"], pady=(SIZES["padding_sm"], SIZES["padding"]))

        self.tab_config = self.tabview.add("⚙️ Cấu hình")
        self.tab_project = self.tabview.add("📹 Tạo Video")
        self.tab_progress = self.tabview.add("📊 Tiến trình")

    def _create_panels(self):
        self.config_panel = ConfigPanel(self.tab_config)
        self.project_panel = ProjectPanel(self.tab_project)
        self.progress_panel = ProgressPanel(self.tab_progress)

    def _connect_signals(self):
        """Wire components together."""
        
        # ProgressPanel run buttons → app._run_***
        self.progress_panel.btn_run_all.configure(command=self._run_all_tasks)
        self.progress_panel.btn_run_selected.configure(command=self._run_selected_tasks)
        
        # ProgressPanel "Stop" button → API.stop
        self.progress_panel.btn_stop.configure(command=self._stop_pipeline)

        # AutomationAPI callbacks → ProgressPanel (via thread-safe after())
        self.api.on_log = lambda msg, lvl: self.after(0, self.progress_panel.on_log, msg, lvl)
        self.api.on_step_change = lambda name, step, idx, total, wid: self.after(
            0, self._on_step_change, name, step, idx, total, wid
        )
        self.api.on_task_complete = lambda task, status, err: self.after(
            0, self._on_task_complete, task, status, err
        )
        self.api.on_progress = lambda done, total: self.after(
            0, self.progress_panel.on_progress, done, total
        )
        self.api.on_finished = lambda results: self.after(
            0, self._on_pipeline_finished, results
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  RUN PIPELINE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _on_tab_change(self):
        """Refresh Render Queue when switching to Progress tab, if not already running."""
        if self.tabview.get() == "📊 Tiến trình" and not self.api.is_running:
            self.progress_panel.refresh_queue(self.project_panel.tasks)

    def _run_all_tasks(self):
        tasks = self.progress_panel.get_pending_tasks()
        if not tasks:
            messagebox.showinfo("Không có", "Không có dự án pending nào để chạy")
            return
        self._start_pipeline(tasks)

    def _run_selected_tasks(self):
        tasks = self.progress_panel.get_selected_tasks()
        if not tasks:
            messagebox.showwarning("Chưa chọn", "Vui lòng tick ☑ các dự án muốn chạy")
            return
        self._start_pipeline(tasks)

    def _start_pipeline(self, tasks):
        # Check cookies first
        is_valid, msg = self.api.check_ready()
        if not is_valid:
            messagebox.showerror("Cookies", f"Không thể chạy:\n{msg}\n\nVui lòng import cookies ở tab Cấu hình.")
            self.tabview.set("⚙️ Cấu hình")
            return

        # Get run mode
        mode = self.progress_panel.mode_var.get()
        max_workers = 1
        if mode == "Song song":
            max_workers = int(self.progress_panel.workers_var.get())

        mode_text = "Tuần tự (1 Chrome)" if max_workers <= 1 else f"Song song ({max_workers} workers)"

        # Switch to progress tab
        self.tabview.set("📊 Tiến trình")

        # Update UI
        self.progress_panel.on_pipeline_start(len(tasks), mode_text, tasks=tasks)
        self.set_status("🟢 Đang chạy", COLORS["success"])

        # Launch
        self.api.run_tasks(
            tasks=tasks,
            all_tasks=self.project_panel.tasks,
            headless=True,
            max_workers=max_workers,
        )

    def _stop_pipeline(self):
        self.api.stop()
        self.progress_panel.btn_stop.configure(state="disabled")
        self.set_status("⏹ Đang dừng...", COLORS["warning"])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  CALLBACKS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _on_step_change(self, task_name, step_name, step_idx, total_steps, worker_id):
        self.progress_panel.on_step_change(task_name, step_name, step_idx, total_steps, worker_id)
        # Find the task by name and update its step in the task list
        for task in self.project_panel.tasks:
            if task.get("ten_san_pham") == task_name:
                self.progress_panel.update_task_step(task, step_name, step_idx, total_steps)
                break

    def _on_task_complete(self, task, status, error):
        self.progress_panel.on_task_complete(task, status, error)
        # Refresh project list to update status icons
        self.project_panel._load_tasks()

    def _on_pipeline_finished(self, results):
        self.progress_panel.on_pipeline_finished(results)
        self.project_panel._load_tasks()
        self.set_status("⚪ Sẵn sàng", COLORS["text_secondary"])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  WINDOW
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _bind_shortcuts(self):
        """Global keyboard shortcuts."""
        self.bind("<Control-s>", lambda e: self._shortcut_save())
        self.bind("<F5>", lambda e: self._shortcut_refresh())
        self.bind("<Control-r>", lambda e: self._run_all_tasks())
        self.bind("<Escape>", lambda e: self._shortcut_stop())

    def _shortcut_save(self):
        """Ctrl+S: Save current project if on the Tạo Video tab."""
        if self.tabview.get() == "📹 Tạo Video":
            panel = self.project_panel
            if panel.selected_index is not None:
                panel._save_current_detail(panel.selected_index)

    def _shortcut_refresh(self):
        """F5: Refresh project list and render queue."""
        self.project_panel._load_tasks()
        if self.tabview.get() == "📊 Tiến trình" and not self.api.is_running:
            self.progress_panel.refresh_queue(self.project_panel.tasks)
        self.set_status("🔄 Đã refresh", COLORS["accent"])
        self.after(2000, lambda: self.set_status("⚪ Sẵn sàng"))

    def _shortcut_stop(self):
        """Escape: Stop pipeline if running."""
        if self.api.is_running:
            self._stop_pipeline()

    def set_status(self, text, color=None):
        self.status_label.configure(text=text, text_color=color or COLORS["text_secondary"])

    def _on_close(self):
        if self.api.is_running:
            confirm = messagebox.askyesno(
                "Đang chạy",
                "Pipeline đang chạy. Bạn có chắc muốn đóng?\nPipeline sẽ bị dừng."
            )
            if not confirm:
                return
            self.api.stop()
        self.destroy()


def main():
    app = VideoAutomationApp()
    app.mainloop()


if __name__ == "__main__":
    main()

"""
Progress Panel — Tab "Tiến trình"
Real-time pipeline monitoring with step indicators, progress bars, and log viewer.
"""

import sys
from datetime import datetime
from pathlib import Path

import customtkinter as ctk

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gui.theme import COLORS, FONTS, SIZES, STEP_COLORS

PIPELINE_STEPS = [
    ("navigate", "🧭 Navigate"),
    ("create_project", "📁 Create"),
    ("upload_images", "🖼 Upload"),
    ("enter_prompt", "✏️ Prompt"),
    ("configure_settings", "⚙️ Settings"),
    ("generate", "🚀 Generate"),
    ("wait_render", "⏳ Render"),
    ("download", "📥 Download"),
]


class ProgressPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)

        self._step_labels = {}
        self._task_items = {}  # {task_index: {frame, status_lbl, step_lbl}}
        self._task_list_tasks = []  # reference to tasks being run
        self._build_ui()

    def _build_ui(self):
        # ── Top: Overview bar ──
        self._build_overview()

        # ── Middle row: Step indicators ──
        mid_top = ctk.CTkFrame(self, fg_color="transparent")
        mid_top.pack(fill="x", pady=(SIZES["padding_sm"], 0))
        mid_top.columnconfigure(0, weight=1)
        self._build_step_indicators(mid_top)

        # ── Main area: Task list (left) + Log viewer (right) ──
        main_area = ctk.CTkFrame(self, fg_color="transparent")
        main_area.pack(fill="both", expand=True, pady=(SIZES["padding_sm"], 0))
        main_area.columnconfigure(0, weight=0, minsize=260)
        main_area.columnconfigure(1, weight=1)
        main_area.rowconfigure(0, weight=1)

        self._build_task_list(main_area)
        self._build_log_viewer(main_area)

        # ── Bottom: Stop button ──
        self._build_controls()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  OVERVIEW
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_overview(self):
        overview = ctk.CTkFrame(
            self, fg_color=COLORS["bg_card"], height=70,
            corner_radius=SIZES["corner_radius"],
            border_color=COLORS["border"], border_width=1,
        )
        overview.pack(fill="x")
        overview.pack_propagate(False)

        left = ctk.CTkFrame(overview, fg_color="transparent")
        left.pack(side="left", fill="y", padx=SIZES["padding"])

        self.task_label = ctk.CTkLabel(
            left, text="⏸ Chưa bắt đầu",
            font=FONTS["heading"], text_color=COLORS["text_primary"],
            anchor="w",
        )
        self.task_label.pack(anchor="w", pady=(10, 0))

        self.mode_label = ctk.CTkLabel(
            left, text="",
            font=FONTS["small"], text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.mode_label.pack(anchor="w")

        right = ctk.CTkFrame(overview, fg_color="transparent")
        right.pack(side="right", fill="y", padx=SIZES["padding"])

        self.progress_label = ctk.CTkLabel(
            right, text="0 / 0",
            font=FONTS["heading"], text_color=COLORS["accent"],
        )
        self.progress_label.pack(anchor="e", pady=(10, 2))

        self.progress_bar = ctk.CTkProgressBar(
            right, width=200, height=8,
            fg_color=COLORS["bg_input"],
            progress_color=COLORS["accent"],
            corner_radius=4,
        )
        self.progress_bar.pack(anchor="e")
        self.progress_bar.set(0)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  STEP INDICATORS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_step_indicators(self, parent):
        steps_frame = ctk.CTkFrame(
            parent, fg_color=COLORS["bg_card"],
            corner_radius=SIZES["corner_radius"],
            border_color=COLORS["border"], border_width=1,
            height=60,
        )
        steps_frame.grid(row=0, column=0, sticky="ew")
        steps_frame.pack_propagate(False)

        self.current_task_label = ctk.CTkLabel(
            steps_frame, text="",
            font=FONTS["small"], text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.current_task_label.pack(fill="x", padx=SIZES["padding"], pady=(6, 0))

        row = ctk.CTkFrame(steps_frame, fg_color="transparent")
        row.pack(fill="x", padx=SIZES["padding_sm"], pady=(0, 6))

        for step_key, step_label in PIPELINE_STEPS:
            cell = ctk.CTkFrame(row, fg_color="transparent")
            cell.pack(side="left", expand=True, fill="x", padx=1)

            lbl = ctk.CTkLabel(
                cell, text=step_label,
                font=FONTS["small"],
                text_color=STEP_COLORS["waiting"],
                fg_color=COLORS["bg_input"],
                corner_radius=4,
                height=26,
            )
            lbl.pack(fill="x", padx=1)
            self._step_labels[step_key] = lbl

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  TASK LIST
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_task_list(self, parent):
        task_frame = ctk.CTkFrame(
            parent, fg_color=COLORS["bg_card"],
            corner_radius=SIZES["corner_radius"],
            border_color=COLORS["border"], border_width=1,
            width=260,
        )
        task_frame.grid(row=0, column=0, sticky="nsew", padx=(0, SIZES["padding_sm"]))
        task_frame.grid_propagate(False)

        ctk.CTkLabel(
            task_frame, text="📋 Danh sách task", font=FONTS["subheading"],
            text_color=COLORS["text_primary"], anchor="w",
        ).pack(fill="x", padx=SIZES["padding_sm"], pady=(SIZES["padding_sm"], 4))

        self._check_vars = {}  # {task_index: BooleanVar}
        self.btn_run_selected = None
        self.btn_run_all = None

        self._task_scroll = ctk.CTkScrollableFrame(
            task_frame, fg_color="transparent",
            scrollbar_button_color=COLORS["bg_hover"],
            scrollbar_button_hover_color=COLORS["border"],
        )
        self._task_scroll.pack(fill="both", expand=True, padx=4, pady=(0, 4))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  LOG VIEWER
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_log_viewer(self, parent):
        log_frame = ctk.CTkFrame(
            parent, fg_color=COLORS["bg_card"],
            corner_radius=SIZES["corner_radius"],
            border_color=COLORS["border"], border_width=1,
        )
        log_frame.grid(row=0, column=1, sticky="nsew")

        header = ctk.CTkFrame(log_frame, fg_color="transparent")
        header.pack(fill="x", padx=SIZES["padding"], pady=(SIZES["padding_sm"], 0))

        ctk.CTkLabel(
            header, text="📜 Log", font=FONTS["subheading"],
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        ctk.CTkButton(
            header, text="🗑 Xóa log", font=FONTS["small"],
            width=80, height=24,
            fg_color=COLORS["bg_hover"], hover_color=COLORS["border"],
            command=self._clear_log,
        ).pack(side="right")

        self.log_textbox = ctk.CTkTextbox(
            log_frame, font=FONTS["mono"],
            fg_color=COLORS["bg_input"], text_color=COLORS["text_primary"],
            border_color=COLORS["border"], border_width=1,
            corner_radius=SIZES["corner_radius"],
            state="disabled",
        )
        self.log_textbox.pack(fill="both", expand=True, padx=SIZES["padding_sm"], pady=SIZES["padding_sm"])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  CONTROLS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_controls(self):
        bar = ctk.CTkFrame(
            self, fg_color=COLORS["bg_card"], height=52,
            corner_radius=SIZES["corner_radius"],
            border_color=COLORS["border"], border_width=1,
        )
        bar.pack(fill="x", pady=(SIZES["padding_sm"], 0))
        bar.pack_propagate(False)

        # Mode selector
        self.mode_var = ctk.StringVar(value="Tuần tự")
        mode_seg = ctk.CTkSegmentedButton(
            bar, values=["Tuần tự", "Song song"],
            variable=self.mode_var, font=FONTS["small"],
            height=32,
            fg_color=COLORS["bg_input"],
            selected_color=COLORS["accent"],
            selected_hover_color=COLORS["accent_hover"],
            unselected_color=COLORS["bg_input"],
            unselected_hover_color=COLORS["bg_hover"],
        )
        mode_seg.pack(side="left", padx=SIZES["padding_sm"])

        # Worker count dropdown
        self.workers_var = ctk.StringVar(value="2")
        self.workers_menu = ctk.CTkOptionMenu(
            bar, values=["1", "2", "3", "4"],
            variable=self.workers_var, font=FONTS["small"],
            width=80, height=32,
            fg_color=COLORS["bg_input"], button_color=COLORS["bg_hover"],
            button_hover_color=COLORS["border"],
            dropdown_fg_color=COLORS["bg_card"], dropdown_hover_color=COLORS["bg_hover"],
        )
        self.workers_menu.pack(side="left")

        ctk.CTkLabel(
            bar, text="workers", font=FONTS["small"],
            text_color=COLORS["text_muted"],
        ).pack(side="left", padx=(4, SIZES["padding"]))

        # Headless toggle
        self.headless_var = ctk.BooleanVar(value=True)
        self.headless_switch = ctk.CTkSwitch(
            bar, text="Chạy ngầm (Headless)",
            variable=self.headless_var, font=FONTS["small"],
            progress_color=COLORS["accent"],
            text_color=COLORS["text_secondary"]
        )
        self.headless_switch.pack(side="left", padx=SIZES["padding_sm"])

        # Status
        self.status_label = ctk.CTkLabel(
            bar, text="⏸ Sẵn sàng",
            font=FONTS["body"], text_color=COLORS["text_muted"],
        )
        self.status_label.pack(side="left", padx=SIZES["padding"])

        # Stop button
        self.btn_stop = ctk.CTkButton(
            bar, text="⏹ Dừng", font=FONTS["body"],
            height=36, width=100,
            fg_color=COLORS["error"], hover_color="#b62324",
            state="disabled",
        )
        self.btn_stop.pack(side="right", padx=SIZES["padding_sm"])

        # Run buttons
        self.btn_run_all = ctk.CTkButton(
            bar, text="▶ Chạy tất cả", font=FONTS["body"],
            height=36, width=140,
            fg_color=COLORS["success"], hover_color="#2ea043",
        )
        self.btn_run_all.pack(side="right", padx=(0, SIZES["padding_sm"]))

        self.btn_run_selected = ctk.CTkButton(
            bar, text="▶ Chạy đã chọn", font=FONTS["body"],
            height=36, width=140,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
        )
        self.btn_run_selected.pack(side="right")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  PUBLIC API (called from app.py via callbacks)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def on_pipeline_start(self, total_tasks, mode_text, tasks=None):
        """Called when pipeline starts."""
        self.task_label.configure(text=f"▶ Đang chạy {total_tasks} task...")
        self.mode_label.configure(text=mode_text)
        self.progress_label.configure(text=f"0 / {total_tasks}")
        self.progress_bar.set(0)
        self.btn_stop.configure(state="normal")
        self.btn_run_all.configure(state="disabled")
        self.btn_run_selected.configure(state="disabled")
        self.status_label.configure(text="🟢 Đang chạy", text_color=COLORS["success"])
        self._reset_steps()
        if tasks:
            self._populate_task_list(tasks)

    def on_step_change(self, task_name, step_name, step_idx, total_steps, worker_id):
        """Called when a step starts."""
        self.current_task_label.configure(text=f"📹 {task_name} — Step {step_idx + 1}/{total_steps}")

        # Reset all steps then highlight current
        for key, lbl in self._step_labels.items():
            lbl.configure(text_color=STEP_COLORS["waiting"], fg_color=COLORS["bg_input"])

        # Mark completed steps
        for i, (key, _) in enumerate(PIPELINE_STEPS):
            if i < step_idx:
                self._step_labels[key].configure(
                    text_color=STEP_COLORS["done"], fg_color=COLORS["bg_dark"]
                )
            elif i == step_idx:
                self._step_labels[key].configure(
                    text_color="#ffffff", fg_color=STEP_COLORS["running"]
                )

    def on_log(self, message, level):
        """Append a log line to the log viewer."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"

        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", line)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def on_progress(self, completed, total):
        """Update progress bar and label."""
        self.progress_label.configure(text=f"{completed} / {total}")
        self.progress_bar.set(completed / total if total > 0 else 0)

    def on_task_complete(self, task, status, error):
        """Called when a single task finishes."""
        name = task.get("ten_san_pham", "Task")
        if status == "completed":
            self.on_log(f"✅ {name}", "INFO")
        elif status == "failed":
            self.on_log(f"❌ {name}: {error}", "ERROR")
        elif status == "skipped":
            self.on_log(f"⏭ {name}: {error}", "WARNING")
        self._update_task_item(task, status)

    def on_pipeline_finished(self, results):
        """Called when the entire pipeline is done."""
        self.task_label.configure(text="✅ Pipeline hoàn tất")
        self.btn_stop.configure(state="disabled")
        self.btn_run_all.configure(state="normal")
        self.btn_run_selected.configure(state="normal")
        self.status_label.configure(text="⏸ Hoàn tất", text_color=COLORS["text_muted"])
        self.progress_bar.set(1)
        self._reset_steps()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  INTERNAL
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _reset_steps(self):
        for key, lbl in self._step_labels.items():
            lbl.configure(text_color=STEP_COLORS["waiting"], fg_color=COLORS["bg_input"])
        self.current_task_label.configure(text="")

    def _clear_log(self):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("0.0", "end")
        self.log_textbox.configure(state="disabled")

    def refresh_queue(self, tasks):
        """Update the Render Queue list when JSON changes."""
        for widget in self._task_scroll.winfo_children():
            widget.destroy()
        
        self._task_items.clear()
        self._check_vars.clear()
        self._task_list_tasks = tasks

        for i, task in enumerate(tasks):
            name = task.get("ten_san_pham", f"Task {i+1}")[:22]
            status = task.get("status", "pending") or "pending"
            
            item = ctk.CTkFrame(self._task_scroll, fg_color="transparent", corner_radius=4)
            item.pack(fill="x", pady=1)

            var = ctk.BooleanVar(value=False)
            self._check_vars[i] = var
            cb = ctk.CTkCheckBox(
                item, text="", variable=var,
                width=24, height=24, checkbox_width=16, checkbox_height=16,
                fg_color=COLORS["accent"], border_color=COLORS["border"],
                hover_color=COLORS["accent_hover"],
            )
            cb.pack(side="left", padx=(2, 2))

            icon = {"completed": "✅", "failed": "❌", "skipped": "⏭", "pending": "⏳", "processing": "🔵"}.get(status, "⏳")
            status_lbl = ctk.CTkLabel(item, text=icon, font=FONTS["small"], width=20)
            status_lbl.pack(side="left", padx=(0, 2))

            name_lbl = ctk.CTkLabel(
                item, text=name, font=FONTS["small"],
                text_color=COLORS["text_primary"], anchor="w",
            )
            name_lbl.pack(side="left", fill="x", expand=True)

            step_text = {"completed": "done", "failed": "error", "skipped": "skip", "pending": "pending"}.get(status, "")
            color = {
                "completed": COLORS["success"], "failed": COLORS["error"],
                "skipped": COLORS["text_muted"], "pending": COLORS["text_muted"]
            }.get(status, COLORS["text_muted"])

            # Keep video counts for completed
            if status == "completed":
                count = task.get("flow_settings", {}).get("count", 2)
                step_text = f"+{count} video"

            step_lbl = ctk.CTkLabel(
                item, text=step_text, font=("Consolas", 10),
                text_color=color, width=65, anchor="e",
            )
            step_lbl.pack(side="right", padx=(2, 4))

            self._task_items[id(task)] = {
                "frame": item, "status_lbl": status_lbl,
                "step_lbl": step_lbl, "name_lbl": name_lbl,
            }

    def _populate_task_list(self, tasks):
        """Build/update task list items when run starts. We just update statuses here."""
        # Instead of clearing, we just ensure it's up-to-date since refresh_queue is used
        pass

    def get_selected_tasks(self):
        """Return tasks that are checked in the render queue."""
        selected = []
        for i, var in self._check_vars.items():
            if var.get() and i < len(self._task_list_tasks):
                selected.append(self._task_list_tasks[i])
        return selected

    def get_pending_tasks(self):
        """Return all tasks that are currently pending."""
        return [t for t in self._task_list_tasks if t.get("status") in ("pending", None)]

    def _update_task_item(self, task, status):
        """Update a task's row in the task list."""
        item = self._task_items.get(id(task))
        if not item:
            return

        icon = {"completed": "✅", "failed": "❌", "skipped": "⏭", "processing": "🔵"}.get(status, "⏳")
        item["status_lbl"].configure(text=icon)

        step_text = ""
        if status == "completed":
            count = task.get("flow_settings", {}).get("count", 2)
            step_text = f"+{count} video"
        elif status == "failed":
            step_text = "error"
        elif status == "skipped":
            step_text = "skip"

        color = {
            "completed": COLORS["success"], "failed": COLORS["error"],
            "skipped": COLORS["text_muted"],
        }.get(status, COLORS["text_muted"])
        item["step_lbl"].configure(text=step_text, text_color=color)

    def update_task_step(self, task, step_name, step_idx, total_steps):
        """Update the current step text for a running task."""
        item = self._task_items.get(id(task))
        if not item:
            return
        item["status_lbl"].configure(text="🔵")
        # Format: "1/8 generate"
        text = f"{step_idx + 1}/{total_steps} {step_name}"
        item["step_lbl"].configure(text=text, text_color=COLORS["accent"])

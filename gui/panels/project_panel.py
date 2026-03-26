"""
Project Panel — Tab "Tạo Video"
Layout 2 cột: Sidebar danh sách (trái) + Form chi tiết (phải)
Phase 3: Sidebar danh sách dự án
Phase 4: Form chi tiết (sẽ bổ sung sau)
"""

import json
import copy
import sys
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gui.theme import COLORS, FONTS, SIZES, STATUS_COLORS
from src.config import JSON_INPUT_PATH


class ProjectPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)

        self.tasks = []
        self.selected_index = None
        self.check_vars = {}

        self._build_layout()
        self._load_tasks()

    def _build_layout(self):
        # Main 2-column layout
        self.columnconfigure(0, weight=0, minsize=SIZES["sidebar_width"])
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        # ── Left: Sidebar ──
        self._build_sidebar()

        # ── Right: Detail panel (placeholder for Phase 4) ──
        self.detail_frame = ctk.CTkFrame(
            self, fg_color=COLORS["bg_card"],
            corner_radius=SIZES["corner_radius"],
            border_color=COLORS["border"], border_width=1,
        )
        self.detail_frame.grid(row=0, column=1, sticky="nsew", padx=(SIZES["padding_sm"], 0), pady=0)

        self.detail_placeholder = ctk.CTkLabel(
            self.detail_frame,
            text="👈 Chọn một dự án từ danh sách bên trái\nđể xem và chỉnh sửa chi tiết",
            font=FONTS["body"], text_color=COLORS["text_muted"],
            justify="center",
        )
        self.detail_placeholder.pack(expand=True)

        # ── Bottom: Action bar ──
        self._build_action_bar()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  SIDEBAR (Left Column)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(
            self, fg_color=COLORS["bg_card"], width=SIZES["sidebar_width"],
            corner_radius=SIZES["corner_radius"],
            border_color=COLORS["border"], border_width=1,
        )
        sidebar.grid(row=0, column=0, sticky="nsew", pady=0)
        sidebar.grid_propagate(False)

        # Header
        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.pack(fill="x", padx=SIZES["padding_sm"], pady=(SIZES["padding_sm"], 0))

        ctk.CTkLabel(
            header, text="📋 Dự án", font=FONTS["heading"],
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        self.count_label = ctk.CTkLabel(
            header, text="0", font=FONTS["small"],
            text_color=COLORS["text_muted"],
        )
        self.count_label.pack(side="right")

        # Project list (scrollable)
        self.project_list = ctk.CTkScrollableFrame(
            sidebar, fg_color="transparent",
            scrollbar_button_color=COLORS["bg_hover"],
            scrollbar_button_hover_color=COLORS["border"],
        )
        self.project_list.pack(fill="both", expand=True, padx=4, pady=4)

        # Status summary
        self.status_summary = ctk.CTkLabel(
            sidebar, text="", font=FONTS["small"],
            text_color=COLORS["text_muted"], anchor="w",
        )
        self.status_summary.pack(fill="x", padx=SIZES["padding_sm"], pady=(0, 4))

        # Sidebar buttons
        btn_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        btn_frame.pack(fill="x", padx=SIZES["padding_sm"], pady=(0, SIZES["padding_sm"]))

        buttons = [
            ("+ Thêm", COLORS["accent"], COLORS["accent_hover"], self._add_project),
            ("📋 Clone", COLORS["bg_hover"], COLORS["border"], self._clone_project),
            ("🗑 Xóa", COLORS["error"], "#b62324", self._delete_project),
        ]

        for text, fg, hover, cmd in buttons:
            ctk.CTkButton(
                btn_frame, text=text, font=FONTS["small"],
                height=30, fg_color=fg, hover_color=hover,
                command=cmd,
            ).pack(side="left", expand=True, fill="x", padx=2)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  ACTION BAR (Bottom)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_action_bar(self):
        bar = ctk.CTkFrame(
            self, fg_color=COLORS["bg_card"], height=52,
            corner_radius=SIZES["corner_radius"],
            border_color=COLORS["border"], border_width=1,
        )
        bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(SIZES["padding_sm"], 0))
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
            fg_color=COLORS["bg_input"],
            button_color=COLORS["bg_hover"],
            button_hover_color=COLORS["border"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_hover_color=COLORS["bg_hover"],
        )
        self.workers_menu.pack(side="left")

        ctk.CTkLabel(
            bar, text="workers", font=FONTS["small"],
            text_color=COLORS["text_muted"],
        ).pack(side="left", padx=(4, SIZES["padding"]))

        # Run buttons (right side)
        self.btn_run_selected = ctk.CTkButton(
            bar, text="▶ Chạy đã chọn", font=FONTS["body"],
            height=36, width=160,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=self._run_selected,
        )
        self.btn_run_selected.pack(side="right", padx=SIZES["padding_sm"])

        self.btn_run_all = ctk.CTkButton(
            bar, text="▶ Chạy tất cả", font=FONTS["body"],
            height=36, width=160,
            fg_color=COLORS["success"], hover_color="#2ea043",
            command=self._run_all,
        )
        self.btn_run_all.pack(side="right")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  DATA OPERATIONS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _load_tasks(self):
        try:
            with open(JSON_INPUT_PATH, "r", encoding="utf-8") as f:
                self.tasks = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.tasks = []
        self._refresh_list()

    def _save_tasks(self):
        with open(JSON_INPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)

    def _refresh_list(self):
        # Clear existing items
        for widget in self.project_list.winfo_children():
            widget.destroy()
        self.check_vars.clear()

        # Render each project
        for i, task in enumerate(self.tasks):
            self._render_project_item(i, task)

        # Update counts
        total = len(self.tasks)
        pending = sum(1 for t in self.tasks if t.get("status") in ("pending", None))
        done = sum(1 for t in self.tasks if t.get("status") == "completed")
        failed = sum(1 for t in self.tasks if t.get("status") == "failed")

        self.count_label.configure(text=f"{total} dự án")

        parts = []
        if pending > 0:
            parts.append(f"🟡 {pending} pending")
        if done > 0:
            parts.append(f"✅ {done} done")
        if failed > 0:
            parts.append(f"❌ {failed} failed")
        self.status_summary.configure(text="  ".join(parts) if parts else "Không có dự án")

    def _render_project_item(self, index, task):
        name = task.get("ten_san_pham", f"Dự án {index + 1}")
        status = task.get("status", "pending") or "pending"

        item_frame = ctk.CTkFrame(
            self.project_list,
            fg_color=COLORS["bg_input"] if index == self.selected_index else "transparent",
            corner_radius=6,
            cursor="hand2",
        )
        item_frame.pack(fill="x", pady=1)

        # Checkbox
        var = ctk.BooleanVar(value=False)
        self.check_vars[index] = var
        cb = ctk.CTkCheckBox(
            item_frame, text="", variable=var,
            width=24, height=24,
            checkbox_width=18, checkbox_height=18,
            fg_color=COLORS["accent"],
            border_color=COLORS["border"],
            hover_color=COLORS["accent_hover"],
        )
        cb.pack(side="left", padx=(6, 2), pady=4)

        # Status icon
        status_icon = {"pending": "🟡", "processing": "🔵", "completed": "✅", "failed": "❌", "skipped": "⏭"}.get(status, "⚪")
        ctk.CTkLabel(
            item_frame, text=status_icon, font=FONTS["small"], width=20,
        ).pack(side="left", padx=(0, 4))

        # Project name
        name_label = ctk.CTkLabel(
            item_frame, text=name[:30],
            font=FONTS["small"], text_color=COLORS["text_primary"],
            anchor="w",
        )
        name_label.pack(side="left", fill="x", expand=True, padx=(0, 6))

        # Click to select
        for widget in (item_frame, name_label):
            widget.bind("<Button-1>", lambda e, idx=index: self._select_project(idx))

    def _select_project(self, index):
        self.selected_index = index
        self._refresh_list()
        self._show_detail(index)

    def _show_detail(self, index):
        """Show project detail in right panel. Placeholder for Phase 4."""
        # Clear existing detail
        for widget in self.detail_frame.winfo_children():
            widget.destroy()

        task = self.tasks[index]
        name = task.get("ten_san_pham", f"Dự án {index + 1}")

        ctk.CTkLabel(
            self.detail_frame,
            text=f"📌 {name}",
            font=FONTS["heading"], text_color=COLORS["text_primary"],
        ).pack(padx=SIZES["padding"], pady=SIZES["padding"], anchor="w")

        ctk.CTkLabel(
            self.detail_frame,
            text="Form chi tiết sẽ được xây dựng ở Phase 4",
            font=FONTS["body"], text_color=COLORS["text_muted"],
        ).pack(padx=SIZES["padding"])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  PROJECT MANAGEMENT (Add / Clone / Delete)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _add_project(self):
        new_task = {
            "ten_san_pham": f"Dự án mới {len(self.tasks) + 1}",
            "mo_ta_san_pham": "",
            "link_folder_anh": "",
            "prompt": "",
            "style": "cinematic",
            "link_folder_video": str(PROJECT_ROOT / "output"),
            "kenh_dang": "",
            "flow_settings": {
                "type": "VIDEO",
                "mode": "VIDEO_REFERENCES",
                "ratio": "PORTRAIT",
                "count": 2,
                "model": "Veo 3.1 - Fast",
                "download_quality": "720p",
                "download_method": "zip",
            },
            "status": "pending",
            "timestamp": None,
            "error": None,
            "video_path": None,
        }
        self.tasks.append(new_task)
        self._save_tasks()
        self.selected_index = len(self.tasks) - 1
        self._refresh_list()
        self._show_detail(self.selected_index)

    def _clone_project(self):
        if self.selected_index is None:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một dự án để clone")
            return

        source = self.tasks[self.selected_index]
        cloned = copy.deepcopy(source)
        cloned["ten_san_pham"] = f"{source.get('ten_san_pham', 'Dự án')} (Copy)"
        cloned["status"] = "pending"
        cloned["timestamp"] = None
        cloned["error"] = None
        cloned["video_path"] = None

        self.tasks.insert(self.selected_index + 1, cloned)
        self._save_tasks()
        self.selected_index = self.selected_index + 1
        self._refresh_list()
        self._show_detail(self.selected_index)

    def _delete_project(self):
        # 1. Check if there are checked items for bulk delete
        checked_indices = sorted([i for i, var in self.check_vars.items() if var.get()], reverse=True)

        if checked_indices:
            count = len(checked_indices)
            confirm = messagebox.askyesno("Xác nhận xóa", f"Bạn có chắc muốn xóa {count} dự án đã chọn không?")
            if not confirm:
                return

            # Remove from bottom to top to preserve indices
            for i in checked_indices:
                self.tasks.pop(i)

            self.selected_index = None

        # 2. Fallback to deleting the single selected item
        elif self.selected_index is not None:
            name = self.tasks[self.selected_index].get("ten_san_pham", "Dự án")
            confirm = messagebox.askyesno("Xác nhận xóa", f"Bạn có chắc muốn xóa:\n\n\"{name}\"?")
            if not confirm:
                return

            self.tasks.pop(self.selected_index)
            if self.selected_index >= len(self.tasks):
                self.selected_index = len(self.tasks) - 1 if self.tasks else None
        else:
            messagebox.showwarning("Chưa chọn", "Vui lòng tick ☑ hoặc chọn dự án muốn xóa")
            return

        # Save and refresh UI
        self._save_tasks()
        self._refresh_list()

        if self.selected_index is not None:
            self._show_detail(self.selected_index)
        else:
            # Reset detail panel
            for widget in self.detail_frame.winfo_children():
                widget.destroy()
            self.detail_placeholder = ctk.CTkLabel(
                self.detail_frame,
                text="👈 Chọn một dự án từ danh sách bên trái\nđể xem và chỉnh sửa chi tiết",
                font=FONTS["body"], text_color=COLORS["text_muted"],
                justify="center",
            )
            self.detail_placeholder.pack(expand=True)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  RUN (Placeholder — will be implemented in Phase 6)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _run_all(self):
        pending = [t for t in self.tasks if t.get("status") in ("pending", None)]
        if not pending:
            messagebox.showinfo("Không có", "Không có dự án pending nào để chạy")
            return
        messagebox.showinfo("Phase 6", f"Sẽ chạy {len(pending)} dự án pending.\n(Chức năng chạy sẽ được kết nối ở Phase 6)")

    def _run_selected(self):
        selected = [i for i, var in self.check_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning("Chưa chọn", "Vui lòng tick ☑ các dự án muốn chạy")
            return
        messagebox.showinfo("Phase 6", f"Sẽ chạy {len(selected)} dự án đã chọn.\n(Chức năng chạy sẽ được kết nối ở Phase 6)")

    def get_selected_tasks(self):
        return [self.tasks[i] for i, var in self.check_vars.items() if var.get()]

    def get_pending_tasks(self):
        return [t for t in self.tasks if t.get("status") in ("pending", None)]

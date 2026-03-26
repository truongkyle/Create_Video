"""
Config Panel — Tab "Cấu hình"
3 sections: JSON Input | Cookies Import | System Settings
"""

import json
import sys
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gui.theme import COLORS, FONTS, SIZES
from src.config import (
    COOKIES_PATH, JSON_INPUT_PATH,
    RENDER_TIMEOUT, DOWNLOAD_TIMEOUT,
    MAX_STEP_RETRY, MAX_RELOAD_RETRY, MAX_FULL_RESTART,
    HUMAN_DELAY_MIN, HUMAN_DELAY_MAX, BASE_DIR,
)
from src.cookie_manager import import_cookies_from_text, has_valid_cookies


class ConfigPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=SIZES["padding_sm"], pady=SIZES["padding_sm"])

        self._build_json_section()
        self._build_cookies_section()
        self._build_settings_section()

    # ── Section 1: JSON Input ──────────────────────────────────

    def _build_json_section(self):
        section = self._section("📋 JSON Input (Danh sách dự án)")

        btn_row = ctk.CTkFrame(section, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, SIZES["padding_sm"]))

        ctk.CTkButton(
            btn_row, text="📂 Mở file JSON", width=160,
            font=FONTS["body"], height=SIZES["button_height"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=self._open_json_file,
        ).pack(side="left", padx=(0, SIZES["padding_sm"]))

        ctk.CTkButton(
            btn_row, text="💾 Lưu JSON", width=120,
            font=FONTS["body"], height=SIZES["button_height"],
            fg_color=COLORS["bg_hover"], hover_color=COLORS["border"],
            command=self._save_json,
        ).pack(side="left")

        self.json_path_label = ctk.CTkLabel(
            btn_row, text=str(JSON_INPUT_PATH),
            font=FONTS["small"], text_color=COLORS["text_muted"],
        )
        self.json_path_label.pack(side="right")

        self.json_textbox = ctk.CTkTextbox(
            section, height=200, font=FONTS["mono"],
            fg_color=COLORS["bg_input"], text_color=COLORS["text_primary"],
            border_color=COLORS["border"], border_width=1,
            corner_radius=SIZES["corner_radius"],
        )
        self.json_textbox.pack(fill="x", pady=(0, SIZES["padding_sm"]))

        self._load_json_content()

    def _load_json_content(self, path=None):
        path = path or JSON_INPUT_PATH
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.json_textbox.delete("0.0", "end")
            self.json_textbox.insert("0.0", content)
            self.json_path_label.configure(text=str(path))
        except FileNotFoundError:
            self.json_textbox.delete("0.0", "end")
            self.json_textbox.insert("0.0", "[]")

    def _open_json_file(self):
        path = filedialog.askopenfilename(
            title="Chọn file JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(BASE_DIR / "data"),
        )
        if path:
            self._load_json_content(path)

    def _save_json(self):
        content = self.json_textbox.get("0.0", "end").strip()
        try:
            data = json.loads(content)
            path = self.json_path_label.cget("text")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Thành công", f"Đã lưu JSON vào {Path(path).name}")
        except json.JSONDecodeError as e:
            messagebox.showerror("Lỗi JSON", f"Nội dung JSON không hợp lệ:\n{e}")

    # ── Section 2: Cookies ─────────────────────────────────────

    def _build_cookies_section(self):
        section = self._section("🍪 Cookies (Đăng nhập Google)")

        self.cookie_status = ctk.CTkLabel(
            section, text="⏳ Đang kiểm tra...",
            font=FONTS["body"], text_color=COLORS["text_secondary"],
            anchor="w",
        )
        self.cookie_status.pack(fill="x", pady=(0, SIZES["padding_sm"]))

        btn_row = ctk.CTkFrame(section, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, SIZES["padding_sm"]))

        ctk.CTkButton(
            btn_row, text="📂 Import file cookies.json", width=220,
            font=FONTS["body"], height=SIZES["button_height"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=self._import_cookies_file,
        ).pack(side="left", padx=(0, SIZES["padding_sm"]))

        ctk.CTkButton(
            btn_row, text="✅ Validate & Lưu", width=160,
            font=FONTS["body"], height=SIZES["button_height"],
            fg_color=COLORS["success"], hover_color="#2ea043",
            command=self._validate_and_save_cookies,
        ).pack(side="left")

        hint = ctk.CTkLabel(
            section,
            text="💡 Dán cookies JSON từ browser extension (EditThisCookie, Cookie-Editor) vào ô bên dưới:",
            font=FONTS["small"], text_color=COLORS["text_muted"], anchor="w",
        )
        hint.pack(fill="x", pady=(0, 4))

        self.cookies_textbox = ctk.CTkTextbox(
            section, height=180, font=FONTS["mono"],
            fg_color=COLORS["bg_input"], text_color=COLORS["text_primary"],
            border_color=COLORS["border"], border_width=1,
            corner_radius=SIZES["corner_radius"],
        )
        self.cookies_textbox.pack(fill="x", pady=(0, SIZES["padding_sm"]))

        self._check_cookies_status()
        self._load_cookies_content()

    def _check_cookies_status(self):
        is_valid, msg = has_valid_cookies()
        color = COLORS["success"] if is_valid else COLORS["error"]
        self.cookie_status.configure(text=msg, text_color=color)
        return is_valid

    def _load_cookies_content(self):
        if COOKIES_PATH.exists():
            try:
                with open(COOKIES_PATH, "r", encoding="utf-8") as f:
                    content = f.read()
                self.cookies_textbox.delete("0.0", "end")
                self.cookies_textbox.insert("0.0", content)
            except Exception:
                pass

    def _import_cookies_file(self):
        path = filedialog.askopenfilename(
            title="Chọn file cookies.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(BASE_DIR / "config"),
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.cookies_textbox.delete("0.0", "end")
                self.cookies_textbox.insert("0.0", content)
                self._validate_and_save_cookies()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể đọc file:\n{e}")

    def _validate_and_save_cookies(self):
        content = self.cookies_textbox.get("0.0", "end").strip()
        if not content:
            messagebox.showwarning("Trống", "Vui lòng dán nội dung cookies JSON vào textbox")
            return

        success, msg = import_cookies_from_text(content)
        if success:
            self._check_cookies_status()
            messagebox.showinfo("Thành công", msg)
        else:
            self.cookie_status.configure(text=msg, text_color=COLORS["error"])
            messagebox.showerror("Lỗi Cookies", msg)

    # ── Section 3: System Settings ─────────────────────────────

    def _build_settings_section(self):
        section = self._section("⚙️ Cài đặt hệ thống")

        self.settings_entries = {}
        settings_config = [
            ("RENDER_TIMEOUT", "Thời gian chờ render (giây)", str(RENDER_TIMEOUT)),
            ("DOWNLOAD_TIMEOUT", "Thời gian chờ download (giây)", str(DOWNLOAD_TIMEOUT)),
            ("MAX_STEP_RETRY", "Số lần thử lại mỗi step", str(MAX_STEP_RETRY)),
            ("MAX_RELOAD_RETRY", "Số lần reload + retry", str(MAX_RELOAD_RETRY)),
            ("MAX_FULL_RESTART", "Số lần restart toàn bộ", str(MAX_FULL_RESTART)),
            ("HUMAN_DELAY_MIN", "Delay tối thiểu (giây)", str(HUMAN_DELAY_MIN)),
            ("HUMAN_DELAY_MAX", "Delay tối đa (giây)", str(HUMAN_DELAY_MAX)),
        ]

        grid = ctk.CTkFrame(section, fg_color="transparent")
        grid.pack(fill="x")

        for i, (key, label_text, default) in enumerate(settings_config):
            row = i // 2
            col = i % 2

            cell = ctk.CTkFrame(grid, fg_color="transparent")
            cell.grid(row=row, column=col, sticky="ew", padx=(0, SIZES["padding"]), pady=4)

            ctk.CTkLabel(
                cell, text=label_text, font=FONTS["small"],
                text_color=COLORS["text_secondary"], anchor="w",
            ).pack(fill="x")

            entry = ctk.CTkEntry(
                cell, font=FONTS["body"], height=SIZES["button_height"],
                fg_color=COLORS["bg_input"], text_color=COLORS["text_primary"],
                border_color=COLORS["border"], border_width=1,
                corner_radius=SIZES["corner_radius"],
            )
            entry.pack(fill="x")
            entry.insert(0, default)
            self.settings_entries[key] = entry

        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        ctk.CTkButton(
            section, text="💾 Lưu cài đặt", width=160,
            font=FONTS["body"], height=SIZES["button_height"],
            fg_color=COLORS["bg_hover"], hover_color=COLORS["border"],
            command=self._save_settings,
        ).pack(anchor="w", pady=(SIZES["padding_sm"], 0))

    def _save_settings(self):
        env_path = BASE_DIR / "config" / ".env"
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            lines = []

        updated = {}
        for key, entry in self.settings_entries.items():
            val = entry.get().strip()
            if val:
                updated[key] = val

        new_lines = []
        written_keys = set()
        for line in lines:
            key_match = line.split("=")[0].strip() if "=" in line else None
            if key_match and key_match in updated:
                new_lines.append(f"{key_match}={updated[key_match]}")
                written_keys.add(key_match)
            else:
                new_lines.append(line)

        for key, val in updated.items():
            if key not in written_keys:
                new_lines.append(f"{key}={val}")

        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        messagebox.showinfo("Thành công", "Đã lưu cài đặt vào .env")

    # ── Helpers ─────────────────────────────────────────────────

    def _section(self, title):
        frame = ctk.CTkFrame(
            self._scroll, fg_color=COLORS["bg_card"],
            corner_radius=SIZES["corner_radius"],
            border_color=COLORS["border"], border_width=1,
        )
        frame.pack(fill="x", pady=(0, SIZES["padding"]))

        ctk.CTkLabel(
            frame, text=title, font=FONTS["heading"],
            text_color=COLORS["text_primary"], anchor="w",
        ).pack(fill="x", padx=SIZES["padding"], pady=(SIZES["padding"], SIZES["padding_sm"]))

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill="x", padx=SIZES["padding"], pady=(0, SIZES["padding"]))
        return content

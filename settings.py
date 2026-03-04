import os
import sys
import json
import tkinter as tk
from tkinter import filedialog
from file_manager import BASE_DIR


def _get_resource_path(filename):
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)


SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "capture_mode":  "Full Screen",
    "auto_comment":  True,
    "ask_filename":  False,
    "export_folder": ""
}


def load_settings():
    """Loads user settings from disk. Returns defaults if no settings file exists yet."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            return {**DEFAULT_SETTINGS, **saved}
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings_to_disk(settings):
    """Writes the current settings dictionary to disk as JSON."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except IOError as e:
        print(f"Could not save settings: {e}")


class SettingsWindow:

    BG_COLOR     = "#1e1e1e"
    PANEL_COLOR  = "#2c2c2c"
    BTN_COLOR    = "#444444"
    ACCENT_COLOR = "#e67e22"
    TEXT_COLOR   = "#ffffff"
    SUBTLE_COLOR = "#aaaaaa"

    def __init__(self, parent, settings):
        self.settings = settings
        self.parent   = parent

        self.window = tk.Toplevel(parent)
        self.window.title("Docilio - Settings")
        try:
            self.window.iconbitmap(_get_resource_path("Docilio.ico"))
        except Exception:
            pass
        self.window.configure(bg=self.BG_COLOR)
        self.window.resizable(False, False)
        self.window.attributes("-topmost", True)
        self.window.geometry("400x420+200+200")

        self._build_ui()

    def _build_ui(self):
        title_bar = tk.Frame(self.window, bg=self.ACCENT_COLOR)
        title_bar.pack(fill="x")
        tk.Label(
            title_bar,
            text="Settings",
            bg=self.ACCENT_COLOR,
            fg="white",
            font=("Segoe UI", 11, "bold"),
            pady=8, padx=12
        ).pack(side="left")

        content = tk.Frame(self.window, bg=self.BG_COLOR, padx=20, pady=16)
        content.pack(fill="both", expand=True)

        self.capture_mode_var = tk.StringVar(
            value=self.settings.get("capture_mode", "Full Screen")
        )
        self._section_label(content, "Capture Mode")
        modes_frame = tk.Frame(content, bg=self.BG_COLOR)
        modes_frame.pack(fill="x", pady=(4, 14))
        for mode in ["Full Screen", "Region Select"]:
            tk.Radiobutton(
                modes_frame, text=mode,
                variable=self.capture_mode_var, value=mode,
                bg=self.BG_COLOR, fg=self.TEXT_COLOR,
                selectcolor=self.ACCENT_COLOR,
                activebackground=self.BG_COLOR,
                activeforeground=self.TEXT_COLOR,
                cursor="hand2"
            ).pack(side="left", padx=(0, 20))

        self.auto_comment_var = tk.BooleanVar(
            value=self.settings.get("auto_comment", True)
        )
        self._section_label(content, "After Each Capture")
        tk.Checkbutton(
            content,
            text="Ask me to add a comment / note",
            variable=self.auto_comment_var,
            bg=self.BG_COLOR, fg=self.TEXT_COLOR,
            selectcolor=self.ACCENT_COLOR,
            activebackground=self.BG_COLOR,
            activeforeground=self.TEXT_COLOR,
            cursor="hand2"
        ).pack(anchor="w", pady=(4, 14))

        self.ask_filename_var = tk.BooleanVar(
            value=self.settings.get("ask_filename", False)
        )
        self._section_label(content, "Export Filename")
        tk.Checkbutton(
            content,
            text="Ask me to name the file on export",
            variable=self.ask_filename_var,
            bg=self.BG_COLOR, fg=self.TEXT_COLOR,
            selectcolor=self.ACCENT_COLOR,
            activebackground=self.BG_COLOR,
            activeforeground=self.TEXT_COLOR,
            cursor="hand2"
        ).pack(anchor="w", pady=(4, 14))

        self._section_label(content, "Generated Files Save Location")
        location_frame = tk.Frame(content, bg=self.BG_COLOR)
        location_frame.pack(fill="x", pady=(4, 16))

        self.export_path_var = tk.StringVar(
            value=self.settings.get("export_folder") or "Not set - click Browse"
        )
        tk.Label(
            location_frame,
            textvariable=self.export_path_var,
            bg=self.PANEL_COLOR, fg=self.SUBTLE_COLOR,
            font=("Consolas", 8),
            padx=8, pady=6, anchor="w", width=32
        ).pack(side="left", fill="x", expand=True)

        tk.Button(
            location_frame, text="Browse",
            bg=self.BTN_COLOR, fg="white",
            relief="flat", padx=10, pady=5,
            cursor="hand2",
            command=self._browse_folder
        ).pack(side="left", padx=(6, 0))

        btn_frame = tk.Frame(content, bg=self.BG_COLOR)
        btn_frame.pack(fill="x", side="bottom")

        tk.Button(
            btn_frame, text="Cancel",
            bg=self.BTN_COLOR, fg="white",
            relief="flat", padx=16, pady=6,
            cursor="hand2", font=("Segoe UI", 10),
            command=self.window.destroy
        ).pack(side="right", padx=(6, 0))

        tk.Button(
            btn_frame, text="Save Settings",
            bg=self.ACCENT_COLOR, fg="white",
            relief="flat", padx=16, pady=6,
            cursor="hand2", font=("Segoe UI", 10),
            command=self._save_settings
        ).pack(side="right")

    def _browse_folder(self):
        chosen = filedialog.askdirectory(
            title="Choose where to save generated files",
            parent=self.window
        )
        if chosen:
            self.export_path_var.set(chosen)

    def _save_settings(self):
        self.settings["capture_mode"]  = self.capture_mode_var.get()
        self.settings["auto_comment"]  = self.auto_comment_var.get()
        self.settings["ask_filename"]  = self.ask_filename_var.get()

        # Only save the export folder if the user has actually selected one.
        # Avoids writing the placeholder string to settings.json.
        folder = self.export_path_var.get()
        self.settings["export_folder"] = folder if os.path.isdir(folder) else ""

        save_settings_to_disk(self.settings)
        self.window.destroy()

    def _section_label(self, parent, text):
        tk.Label(
            parent,
            text=text.upper(),
            bg=self.BG_COLOR, fg=self.SUBTLE_COLOR,
            font=("Segoe UI", 8)
        ).pack(anchor="w")
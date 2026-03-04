import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import tkinter as tk
from tkinter import messagebox
from settings import SettingsWindow, load_settings, save_settings_to_disk
from file_manager import count_screenshots, clear_screenshots, open_master_folder
from screenshot import take_fullscreen, take_region, take_timed

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


class DocilioToolbar:

    COLLAPSED_WIDTH = 200
    EXPANDED_WIDTH  = 795
    HEIGHT          = 48

    BG_COLOR      = "#2c2c2c"
    BTN_COLOR     = "#3d3d3d"
    BTN_HOVER     = "#555555"
    ACCENT_COLOR  = "#e67e22"
    DIVIDER_COLOR = "#555555"

    def __init__(self, root):
        self.root = root
        self.root.title("Docilio")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=self.BG_COLOR)
        self.root.resizable(False, False)

        self.is_expanded   = False
        self._resize_start = None

        self.settings         = load_settings()
        self.screenshot_count = tk.IntVar(value=count_screenshots())

        self.root.geometry(f"{self.COLLAPSED_WIDTH}x{self.HEIGHT}+100+100")
        self.root.minsize(self.COLLAPSED_WIDTH, self.HEIGHT)
        self.root.update_idletasks()

        self._build_toolbar()
        self._make_draggable()
        self._register_hotkeys()
        self.update_capture_label()

    def _build_toolbar(self):
        self.frame = tk.Frame(self.root, bg=self.BG_COLOR)
        self.frame.pack(fill="both", expand=True)

        # Capture button - always visible
        self.btn_capture = tk.Button(
            self.frame,
            text="Capture",
            bg=self.ACCENT_COLOR, fg="white",
            relief="flat", cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=22,
            command=self.on_capture_click
        )
        self.btn_capture.pack(side="left", padx=(8, 0), pady=7)
        self.btn_capture.bind("<Enter>", lambda e: self.btn_capture.config(bg="#d35400"))
        self.btn_capture.bind("<Leave>", lambda e: self.btn_capture.config(bg=self.ACCENT_COLOR))

        # Expand/collapse toggle - always visible
        self.btn_toggle = tk.Button(
            self.frame,
            text="»",
            bg=self.BTN_COLOR, fg="#aaaaaa",
            relief="flat", cursor="hand2",
            font=("Segoe UI", 10), width=3,
            command=self.toggle_expand
        )
        self.btn_toggle.pack(side="left", padx=(6, 0), pady=7)
        self._add_hover(self.btn_toggle)

        # All buttons below are hidden until the toolbar is expanded
        self._divider1 = tk.Frame(self.frame, bg=self.DIVIDER_COLOR, width=1)

        self.btn_export = tk.Menubutton(
            self.frame, text="Export",
            bg=self.BTN_COLOR, fg="white",
            relief="flat", cursor="hand2",
            font=("Segoe UI", 9), padx=10,
            indicatoron=False
        )
        export_menu = tk.Menu(
            self.btn_export, tearoff=False,
            bg="#3a3a3a", fg="white",
            activebackground=self.ACCENT_COLOR, activeforeground="white",
            relief="flat", bd=0, font=("Segoe UI", 9)
        )
        for fmt in ["Word", "Excel", "PDF", "PowerPoint"]:
            export_menu.add_command(label=fmt, command=lambda f=fmt: self.on_export_click(f))
        self.btn_export["menu"] = export_menu
        self._add_hover(self.btn_export)

        self.btn_timed = tk.Menubutton(
            self.frame, text="Timed",
            bg=self.BTN_COLOR, fg="white",
            relief="flat", cursor="hand2",
            font=("Segoe UI", 9), padx=10,
            indicatoron=False
        )
        timed_menu = tk.Menu(
            self.btn_timed, tearoff=False,
            bg="#3a3a3a", fg="white",
            activebackground=self.ACCENT_COLOR, activeforeground="white",
            relief="flat", bd=0, font=("Segoe UI", 9)
        )
        for seconds in [3, 5, 10]:
            timed_menu.add_command(
                label=f"{seconds}s delay",
                command=lambda s=seconds: self.on_timed_capture(s)
            )
        self.btn_timed["menu"] = timed_menu
        self._add_hover(self.btn_timed)

        self.btn_stitch = tk.Button(
            self.frame, text="Stitch",
            bg=self.BTN_COLOR, fg="white",
            relief="flat", cursor="hand2",
            font=("Segoe UI", 9), padx=10,
            command=self.on_stitch_click
        )
        self._add_hover(self.btn_stitch)

        self.btn_compare = tk.Button(
            self.frame, text="Compare",
            bg=self.BTN_COLOR, fg="white",
            relief="flat", cursor="hand2",
            font=("Segoe UI", 9), padx=10,
            command=self.on_compare_click
        )
        self._add_hover(self.btn_compare)

        self._divider2 = tk.Frame(self.frame, bg=self.DIVIDER_COLOR, width=1)

        self.btn_clear = tk.Button(
            self.frame, text="Clear",
            bg=self.BTN_COLOR, fg="white",
            relief="flat", cursor="hand2",
            font=("Segoe UI", 9), padx=10,
            command=self.on_clear_click
        )
        self._add_hover(self.btn_clear)

        self.btn_folder = tk.Button(
            self.frame, text="Folder",
            bg=self.BTN_COLOR, fg="white",
            relief="flat", cursor="hand2",
            font=("Segoe UI", 9), padx=10,
            command=self.on_folder_click
        )
        self._add_hover(self.btn_folder)

        self.btn_settings = tk.Button(
            self.frame, text="Settings",
            bg=self.BTN_COLOR, fg="white",
            relief="flat", cursor="hand2",
            font=("Segoe UI", 9), padx=10,
            command=self.on_settings_click
        )
        self._add_hover(self.btn_settings)

        self.btn_close = tk.Button(
            self.frame, text="x",
            bg="#c0392b", fg="white",
            relief="flat", cursor="hand2",
            font=("Segoe UI", 9), padx=8,
            command=self.root.destroy
        )
        self.btn_close.bind("<Enter>", lambda e: self.btn_close.config(bg="#e74c3c"))
        self.btn_close.bind("<Leave>", lambda e: self.btn_close.config(bg="#c0392b"))

        # Drag handle on the right edge for manual width adjustment
        self.resize_handle = tk.Frame(
            self.frame, bg=self.DIVIDER_COLOR, width=5, cursor="sb_h_double_arrow"
        )
        self.resize_handle.pack(side="right", fill="y", padx=(2, 0))
        self.resize_handle.bind("<ButtonPress-1>",   self._on_resize_start)
        self.resize_handle.bind("<B1-Motion>",       self._on_resize_drag)
        self.resize_handle.bind("<ButtonRelease-1>", self._on_resize_end)
        self.resize_handle.bind("<Enter>", lambda e: self.resize_handle.config(bg=self.ACCENT_COLOR))
        self.resize_handle.bind("<Leave>", lambda e: self.resize_handle.config(bg=self.DIVIDER_COLOR))

    def _register_hotkeys(self):
        """Registers global keyboard shortcuts. Requires the keyboard package."""
        if not KEYBOARD_AVAILABLE:
            return
        keyboard.add_hotkey("alt+x", lambda: self.root.after(0, self.on_capture_click))

    def toggle_expand(self):
        x = self.root.winfo_x()
        y = self.root.winfo_y()

        if self.is_expanded:
            for widget in [
                self._divider1, self.btn_export, self.btn_timed,
                self.btn_stitch, self.btn_compare, self._divider2,
                self.btn_clear, self.btn_folder, self.btn_settings, self.btn_close
            ]:
                widget.pack_forget()

            self.btn_toggle.config(text="»")
            self.root.minsize(self.COLLAPSED_WIDTH, self.HEIGHT)
            self.root.geometry(f"{self.COLLAPSED_WIDTH}x{self.HEIGHT}+{x}+{y}")
            self.is_expanded = False
        else:
            self._divider1.pack(side="left", fill="y", padx=(6, 0), pady=8)
            for btn in [self.btn_export, self.btn_timed, self.btn_stitch, self.btn_compare]:
                btn.pack(side="left", pady=7, padx=(4, 0))
            self._divider2.pack(side="left", fill="y", padx=(6, 0), pady=8)
            for btn in [self.btn_clear, self.btn_folder, self.btn_settings]:
                btn.pack(side="left", pady=7, padx=(4, 0))
            self.btn_close.pack(side="left", pady=7, padx=(8, 0))

            self.btn_toggle.config(text="«")
            self.root.minsize(self.EXPANDED_WIDTH, self.HEIGHT)
            self.root.geometry(f"{self.EXPANDED_WIDTH}x{self.HEIGHT}+{x}+{y}")
            self.is_expanded = True

    def _on_resize_start(self, event):
        self._resize_start  = self.root.winfo_x() + self.root.winfo_width()
        self._resize_origin = event.x_root

    def _on_resize_drag(self, event):
        if self._resize_start is None:
            return
        delta     = event.x_root - self._resize_origin
        new_width = self.root.winfo_width() + delta
        min_w     = self.COLLAPSED_WIDTH if not self.is_expanded else self.EXPANDED_WIDTH
        new_width = max(new_width, min_w)
        self._resize_origin = event.x_root
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.root.geometry(f"{new_width}x{self.HEIGHT}+{x}+{y}")

    def _on_resize_end(self, event):
        self._resize_start = None

    def update_capture_label(self):
        count = self.screenshot_count.get()
        self.btn_capture.config(
            text="Capture" if count == 0 else f"Capture ({count})"
        )

    def _make_draggable(self):
        self.frame.bind("<ButtonPress-1>", self._on_drag_start)
        self.frame.bind("<B1-Motion>",     self._on_drag_move)

    def _on_drag_start(self, event):
        if event.widget is self.resize_handle:
            return
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag_move(self, event):
        if not hasattr(self, "_drag_x"):
            return
        if isinstance(event.widget, (tk.Button, tk.Menubutton)):
            return
        x = self.root.winfo_x() + (event.x - self._drag_x)
        y = self.root.winfo_y() + (event.y - self._drag_y)
        self.root.geometry(f"+{x}+{y}")

    def _add_hover(self, widget):
        widget.bind("<Enter>", lambda e: widget.config(bg=self.BTN_HOVER))
        widget.bind("<Leave>", lambda e: widget.config(bg=self.BTN_COLOR))

    def on_capture_click(self):
        mode = self.settings.get("capture_mode", "Full Screen")
        if mode == "Full Screen":
            take_fullscreen(self.root, self.on_screenshot_saved)
        else:
            take_region(self.root, self.on_screenshot_saved)

    def on_timed_capture(self, seconds):
        take_timed(self.root, self.on_screenshot_saved, delay_seconds=seconds)

    def on_screenshot_saved(self, save_path):
        from comment_popup import CommentPopup
        def _after_save(_path):
            self.screenshot_count.set(self.screenshot_count.get() + 1)
            self.update_capture_label()
        CommentPopup(self.root, save_path, on_complete=_after_save)

    def on_export_click(self, format_choice):
        from exporter import export_word, export_excel, export_pdf, export_pptx
        exporters = {
            "Word":       export_word,
            "Excel":      export_excel,
            "PDF":        export_pdf,
            "PowerPoint": export_pptx,
        }
        func = exporters.get(format_choice)
        if func:
            func(self.settings, self.root)

    def on_stitch_click(self):
        from stitch_tool import StitchTool
        StitchTool(self.root, on_complete=self.on_screenshot_saved)

    def on_compare_click(self):
        from compare_tool import CompareTool
        CompareTool(self.root, on_complete=self.on_screenshot_saved)

    def on_clear_click(self):
        confirmed = messagebox.askyesno(
            "Clear All Screenshots",
            "This will permanently delete all captured screenshots.\n\nAre you sure?",
            icon="warning",
            parent=self.root
        )
        if confirmed:
            clear_screenshots()
            self.screenshot_count.set(0)
            self.update_capture_label()

    def on_folder_click(self):
        open_master_folder()

    def on_settings_click(self):
        SettingsWindow(self.root, self.settings)
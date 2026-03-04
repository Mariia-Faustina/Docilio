import os
import sys
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from file_manager import MASTER_FOLDER, get_next_screenshot_name


def _get_resource_path(filename):
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")


class StitchTool:
    """
    Lets the user select multiple screenshots from the capture folder,
    preview them as thumbnails, then merge them into a single image.
    On completion, passes the result to on_complete so the annotator
    opens automatically, matching the normal capture flow.
    """

    BG_COLOR     = "#1e1e1e"
    PANEL_COLOR  = "#2c2c2c"
    BTN_COLOR    = "#444444"
    ACCENT_COLOR = "#e67e22"
    TEXT_COLOR   = "#ffffff"
    SUBTLE_COLOR = "#aaaaaa"

    def __init__(self, parent, on_complete=None):
        self.parent      = parent
        self.on_complete = on_complete
        self.thumbnails  = {}

        self.window = tk.Toplevel(parent)
        self.window.title("Docilio - Stitch Screenshots")
        try:
            self.window.iconbitmap(_get_resource_path("Docilio.ico"))
        except Exception:
            pass
        self.window.configure(bg=self.BG_COLOR)
        self.window.geometry("700x520+100+80")
        self.window.resizable(True, True)
        self.window.attributes("-topmost", True)
        self.window.grab_set()

        self._build_ui()
        self._load_images()

    def _build_ui(self):
        title_bar = tk.Frame(self.window, bg=self.ACCENT_COLOR)
        title_bar.pack(fill="x")
        tk.Label(
            title_bar,
            text="Stitch Screenshots Together",
            bg=self.ACCENT_COLOR,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            pady=6, padx=12
        ).pack(side="left")

        # Bottom bar is packed before content so tkinter reserves its
        # space first and the scrollable grid fills the remaining area.
        bottom = tk.Frame(self.window, bg=self.BG_COLOR, padx=12, pady=8)
        bottom.pack(side="bottom", fill="x")

        content = tk.Frame(self.window, bg=self.BG_COLOR, padx=12, pady=10)
        content.pack(fill="both", expand=True)

        tk.Label(
            content,
            text="Tick the screenshots you want to stitch, in the order you want them:",
            bg=self.BG_COLOR,
            fg=self.SUBTLE_COLOR,
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(0, 8))

        grid_frame = tk.Frame(content, bg=self.BG_COLOR)
        grid_frame.pack(fill="both", expand=True)

        self.grid_canvas = tk.Canvas(grid_frame, bg=self.BG_COLOR, highlightthickness=0)
        scrollbar        = tk.Scrollbar(grid_frame, orient="vertical", command=self.grid_canvas.yview)
        self.grid_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.grid_canvas.pack(side="left", fill="both", expand=True)

        self.grid_inner = tk.Frame(self.grid_canvas, bg=self.BG_COLOR)
        self.grid_canvas.create_window((0, 0), window=self.grid_inner, anchor="nw")
        self.grid_inner.bind("<Configure>", lambda e: self.grid_canvas.configure(
            scrollregion=self.grid_canvas.bbox("all")
        ))

        def _on_mousewheel(event):
            self.grid_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.grid_canvas.bind("<MouseWheel>", _on_mousewheel)
        self.grid_inner.bind("<MouseWheel>", _on_mousewheel)

        tk.Label(
            bottom, text="Direction:",
            bg=self.BG_COLOR, fg=self.TEXT_COLOR,
            font=("Segoe UI", 9)
        ).pack(side="left", padx=(0, 8))

        self.direction_var = tk.StringVar(value="Vertical")
        for direction in ["Vertical", "Horizontal"]:
            tk.Radiobutton(
                bottom,
                text=direction,
                variable=self.direction_var,
                value=direction,
                bg=self.BG_COLOR,
                fg=self.TEXT_COLOR,
                selectcolor=self.ACCENT_COLOR,
                activebackground=self.BG_COLOR,
                font=("Segoe UI", 9),
                cursor="hand2"
            ).pack(side="left", padx=(0, 12))

        tk.Button(
            bottom, text="Cancel",
            bg=self.BTN_COLOR, fg="white",
            relief="flat", padx=12, pady=5,
            cursor="hand2", font=("Segoe UI", 9),
            command=self.window.destroy
        ).pack(side="right", padx=(6, 0))

        tk.Button(
            bottom, text="Stitch Selected",
            bg=self.ACCENT_COLOR, fg="white",
            relief="flat", padx=12, pady=5,
            cursor="hand2", font=("Segoe UI", 9, "bold"),
            command=self._stitch
        ).pack(side="right")

    def _load_images(self):
        if not os.path.exists(MASTER_FOLDER):
            return

        files = sorted([
            f for f in os.listdir(MASTER_FOLDER)
            if f.lower().endswith(IMAGE_EXTENSIONS)
        ])

        self.check_vars = {}
        cols = 4

        for i, filename in enumerate(files):
            path = os.path.join(MASTER_FOLDER, filename)

            img = Image.open(path)
            img.thumbnail((140, 100))
            thumb = ImageTk.PhotoImage(img)
            self.thumbnails[filename] = thumb

            cell = tk.Frame(self.grid_inner, bg=self.PANEL_COLOR, padx=4, pady=4)
            cell.grid(row=i // cols, column=i % cols, padx=6, pady=6)

            tk.Label(cell, image=thumb, bg=self.PANEL_COLOR).pack()

            var = tk.BooleanVar(value=False)
            self.check_vars[path] = var

            tk.Checkbutton(
                cell,
                text=filename,
                variable=var,
                bg=self.PANEL_COLOR,
                fg=self.TEXT_COLOR,
                selectcolor=self.ACCENT_COLOR,
                activebackground=self.PANEL_COLOR,
                font=("Segoe UI", 7),
                cursor="hand2",
                wraplength=140
            ).pack()

    def _stitch(self):
        selected_paths = [
            path for path, var in self.check_vars.items() if var.get()
        ]

        if len(selected_paths) < 2:
            messagebox.showwarning(
                "Select More",
                "Please tick at least 2 screenshots to stitch.",
                parent=self.window
            )
            return

        images    = [Image.open(p).convert("RGB") for p in selected_paths]
        direction = self.direction_var.get()

        if direction == "Vertical":
            total_w  = max(img.width for img in images)
            total_h  = sum(img.height for img in images)
            result   = Image.new("RGB", (total_w, total_h), (30, 30, 30))
            y_offset = 0
            for img in images:
                result.paste(img, (0, y_offset))
                y_offset += img.height
        else:
            total_w  = sum(img.width for img in images)
            total_h  = max(img.height for img in images)
            result   = Image.new("RGB", (total_w, total_h), (30, 30, 30))
            x_offset = 0
            for img in images:
                result.paste(img, (x_offset, 0))
                x_offset += img.width

        save_path = get_next_screenshot_name()
        result.save(save_path)
        self.window.destroy()

        if self.on_complete:
            self.on_complete(save_path)
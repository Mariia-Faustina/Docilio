import os
import sys
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageDraw, ImageFont, ImageTk
from file_manager import MASTER_FOLDER, get_next_screenshot_name


def _get_resource_path(filename):
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")


class CompareTool:
    """
    Lets the user assign two screenshots as Before and After, then generates
    a vertically stacked comparison image with an orange divider and labels.
    On completion, passes the result to on_complete so the annotator opens
    automatically, matching the normal capture flow.
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

        self.before_path = None
        self.after_path  = None
        self.before_var  = tk.StringVar(value="Not set")
        self.after_var   = tk.StringVar(value="Not set")

        self.window = tk.Toplevel(parent)
        self.window.title("Docilio - Before and After")
        try:
            self.window.iconbitmap(_get_resource_path("Docilio.ico"))
        except Exception:
            pass
        self.window.configure(bg=self.BG_COLOR)
        self.window.geometry("750x700+100+80")
        self.window.minsize(600, 500)
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
            text="Before and After Comparison",
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
            text="Click Before or After under each screenshot to assign it:",
            bg=self.BG_COLOR,
            fg=self.SUBTLE_COLOR,
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(0, 4))

        status_frame = tk.Frame(content, bg=self.PANEL_COLOR, padx=10, pady=6)
        status_frame.pack(fill="x", pady=(0, 8))

        tk.Label(status_frame, text="Before:", bg=self.PANEL_COLOR, fg=self.SUBTLE_COLOR,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w", padx=(0, 6))
        tk.Label(status_frame, textvariable=self.before_var, bg=self.PANEL_COLOR, fg=self.TEXT_COLOR,
                 font=("Segoe UI", 8)).grid(row=0, column=1, sticky="w")

        tk.Label(status_frame, text="After:", bg=self.PANEL_COLOR, fg=self.SUBTLE_COLOR,
                 font=("Segoe UI", 8)).grid(row=1, column=0, sticky="w", padx=(0, 6))
        tk.Label(status_frame, textvariable=self.after_var, bg=self.PANEL_COLOR, fg=self.TEXT_COLOR,
                 font=("Segoe UI", 8)).grid(row=1, column=1, sticky="w")

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

        self.show_labels_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            bottom,
            text="Show Before / After labels",
            variable=self.show_labels_var,
            bg=self.BG_COLOR,
            fg=self.TEXT_COLOR,
            selectcolor=self.ACCENT_COLOR,
            activebackground=self.BG_COLOR,
            font=("Segoe UI", 9),
            cursor="hand2"
        ).pack(side="left")

        tk.Button(
            bottom, text="Cancel",
            bg=self.BTN_COLOR, fg="white",
            relief="flat", padx=12, pady=5,
            cursor="hand2", font=("Segoe UI", 9),
            command=self.window.destroy
        ).pack(side="right", padx=(6, 0))

        tk.Button(
            bottom, text="Generate Comparison",
            bg=self.ACCENT_COLOR, fg="white",
            relief="flat", padx=12, pady=5,
            cursor="hand2", font=("Segoe UI", 9, "bold"),
            command=self._generate
        ).pack(side="right")

    def _load_images(self):
        if not os.path.exists(MASTER_FOLDER):
            return

        files = sorted([
            f for f in os.listdir(MASTER_FOLDER)
            if f.lower().endswith(IMAGE_EXTENSIONS)
        ])

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
            tk.Label(cell, text=filename, bg=self.PANEL_COLOR, fg=self.SUBTLE_COLOR,
                     font=("Segoe UI", 7), wraplength=140).pack()

            btn_row = tk.Frame(cell, bg=self.PANEL_COLOR)
            btn_row.pack(fill="x")

            tk.Button(
                btn_row, text="Before",
                bg="#2c3e50", fg="white", relief="flat",
                font=("Segoe UI", 7), cursor="hand2",
                command=lambda p=path, n=filename: self._assign("before", p, n)
            ).pack(side="left", expand=True, fill="x", padx=(0, 1))

            tk.Button(
                btn_row, text="After",
                bg="#1a5276", fg="white", relief="flat",
                font=("Segoe UI", 7), cursor="hand2",
                command=lambda p=path, n=filename: self._assign("after", p, n)
            ).pack(side="left", expand=True, fill="x", padx=(1, 0))

    def _assign(self, role, path, name):
        if role == "before":
            self.before_path = path
            self.before_var.set(name)
        else:
            self.after_path = path
            self.after_var.set(name)

    def _generate(self):
        if not self.before_path or not self.after_path:
            messagebox.showwarning(
                "Assign Both",
                "Please assign both a Before and an After screenshot.",
                parent=self.window
            )
            return

        img_before = Image.open(self.before_path).convert("RGB")
        img_after  = Image.open(self.after_path).convert("RGB")

        # Scale both images to the same width so they align cleanly when stacked
        target_w = max(img_before.width, img_after.width)
        img_before = img_before.resize(
            (target_w, int(img_before.height * (target_w / img_before.width))), Image.LANCZOS
        )
        img_after = img_after.resize(
            (target_w, int(img_after.height * (target_w / img_after.width))), Image.LANCZOS
        )

        divider_h = 6
        label_h   = 50 if self.show_labels_var.get() else 0
        total_h   = (label_h + img_before.height) + divider_h + (label_h + img_after.height)

        result = Image.new("RGB", (target_w, total_h), (20, 20, 20))
        result.paste(img_before, (0, label_h))

        after_top = label_h + img_before.height + divider_h
        result.paste(img_after, (0, after_top + label_h))

        draw = ImageDraw.Draw(result)

        # Orange horizontal divider between the two images
        divider_y = label_h + img_before.height
        draw.rectangle([0, divider_y, target_w, divider_y + divider_h], fill=(230, 126, 34))

        if self.show_labels_var.get():
            try:
                font = ImageFont.truetype("arialbd.ttf", size=28)
            except (OSError, IOError):
                try:
                    font = ImageFont.truetype("arial.ttf", size=28)
                except (OSError, IOError):
                    font = None

            # BEFORE label centred above the first image
            draw.rectangle([0, 0, target_w, label_h], fill=(20, 20, 20))
            before_bbox = draw.textbbox((0, 0), "BEFORE", font=font)
            draw.text(
                ((target_w - (before_bbox[2] - before_bbox[0])) // 2,
                 (label_h  - (before_bbox[3] - before_bbox[1])) // 2),
                "BEFORE", fill=(230, 126, 34), font=font
            )

            # AFTER label centred above the second image
            after_label_y = label_h + img_before.height + divider_h
            draw.rectangle([0, after_label_y, target_w, after_label_y + label_h], fill=(20, 20, 20))
            after_bbox = draw.textbbox((0, 0), "AFTER", font=font)
            draw.text(
                ((target_w  - (after_bbox[2] - after_bbox[0])) // 2,
                 after_label_y + (label_h - (after_bbox[3] - after_bbox[1])) // 2),
                "AFTER", fill=(230, 126, 34), font=font
            )

        save_path = get_next_screenshot_name()
        result.save(save_path)
        self.window.destroy()

        if self.on_complete:
            self.on_complete(save_path)
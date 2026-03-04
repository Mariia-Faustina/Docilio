import os
import sys
import math
import tkinter as tk
from tkinter import colorchooser, simpledialog, messagebox
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageTk
from file_manager import save_comment


def _get_resource_path(filename):
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)


class CommentPopup:

    BG_COLOR     = "#1e1e1e"
    PANEL_COLOR  = "#2c2c2c"
    BTN_COLOR    = "#444444"
    BTN_ACTIVE   = "#555555"
    ACCENT_COLOR = "#e67e22"
    TEXT_COLOR   = "#ffffff"
    SUBTLE_COLOR = "#aaaaaa"

    PRESET_COLORS = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#3498db", "#9b59b6", "#ffffff", "#000000"]

    def __init__(self, parent, image_path, on_complete=None):
        self.image_path        = image_path
        self.parent            = parent
        self.on_complete       = on_complete
        self.active_tool       = "pen"
        self.active_color      = "#e74c3c"
        self.fill_shape        = False
        self.highlight_mode    = False
        self.highlight_opacity = 80
        self.line_width        = 3
        self.eraser_size       = 20
        self.step_counter      = 1
        self.zoom_level        = 1.0
        self._last_watermark   = "DRAFT"

        self.undo_stack = []
        self.redo_stack = []

        self.orig_image   = Image.open(image_path).convert("RGBA")
        self.draw_layer   = Image.new("RGBA", self.orig_image.size, (0, 0, 0, 0))
        self.draw_context = ImageDraw.Draw(self.draw_layer)

        self._drag_start = None
        self._pen_points = []
        self._shift_held = False

        self.window = tk.Toplevel(parent)
        self.window.title("Docilio")
        try:
            self.window.iconbitmap(_get_resource_path("Docilio.ico"))
        except Exception:
            pass
        self.window.configure(bg=self.BG_COLOR)
        self.window.resizable(True, True)
        self.window.attributes("-topmost", True)
        self.window.grab_set()

        self._build_ui()
        self._render_canvas()
        self.window.focus_force()

        self.window.bind("<KeyPress-Shift_L>",   lambda e: setattr(self, "_shift_held", True))
        self.window.bind("<KeyRelease-Shift_L>", lambda e: setattr(self, "_shift_held", False))
        self.window.bind("<KeyPress-Shift_R>",   lambda e: setattr(self, "_shift_held", True))
        self.window.bind("<KeyRelease-Shift_R>", lambda e: setattr(self, "_shift_held", False))

        self.window.bind("<Control-z>", lambda e: self._undo())
        self.window.bind("<Control-y>", lambda e: self._redo())

    def _build_ui(self):
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()

        img_w, img_h = self.orig_image.size
        max_canvas_w = min(img_w, int(screen_w * 0.7))
        max_canvas_h = min(img_h, int(screen_h * 0.65))

        scale            = min(max_canvas_w / img_w, max_canvas_h / img_h, 1.0)
        self.canvas_w    = int(img_w * scale)
        self.canvas_h    = int(img_h * scale)
        self.image_scale = scale

        win_w = self.canvas_w + 236
        win_h = self.canvas_h + 110
        self.window.geometry(f"{win_w}x{win_h}+80+60")

        title_bar = tk.Frame(self.window, bg=self.ACCENT_COLOR)
        title_bar.pack(fill="x")
        tk.Label(title_bar, text="Annotate & Comment", bg=self.ACCENT_COLOR, fg="white", font=("Segoe UI", 10, "bold"), pady=6, padx=12).pack(side="left")
        tk.Button(title_bar, text="Clear", bg="#c0392b", fg="white", relief="flat", font=("Segoe UI", 9), cursor="hand2", padx=10, pady=4, command=self._clear_all).pack(side="right", padx=(4, 8), pady=4)
        tk.Button(title_bar, text="Undo", bg="#555555", fg="white", relief="flat", font=("Segoe UI", 9), cursor="hand2", padx=10, pady=4, command=self._undo).pack(side="right", padx=(4, 0), pady=4)
        tk.Label(title_bar, text="Ctrl+Z", bg=self.ACCENT_COLOR, fg="#ffcc99", font=("Segoe UI", 7)).pack(side="right", padx=(0, 2))

        main_area = tk.Frame(self.window, bg=self.BG_COLOR)
        main_area.pack(fill="both", expand=True, padx=8, pady=(6, 0))

        self.canvas = tk.Canvas(main_area, width=self.canvas_w, height=self.canvas_h, bg="#111111", highlightthickness=1, highlightbackground="#444444", cursor="crosshair")
        self.canvas.pack(side="left", fill="both", expand=True)

        self._build_right_toolbar(main_area)
        self._build_bottom_bar()

        self.canvas.bind("<ButtonPress-1>",   self._on_press)
        self.canvas.bind("<B1-Motion>",       self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    def _build_right_toolbar(self, parent):
        outer = tk.Frame(parent, bg=self.PANEL_COLOR, width=230)
        outer.pack(side="right", fill="y", padx=(6, 0))
        outer.pack_propagate(False)

        scroll_canvas = tk.Canvas(outer, bg=self.PANEL_COLOR, highlightthickness=0, width=228)
        scrollbar     = tk.Scrollbar(outer, orient="vertical", command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        scroll_canvas.pack(side="left", fill="both", expand=True)

        toolbar        = tk.Frame(scroll_canvas, bg=self.PANEL_COLOR)
        toolbar_window = scroll_canvas.create_window((0, 0), window=toolbar, anchor="nw")

        toolbar.bind("<Configure>", lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))
        scroll_canvas.bind("<Configure>", lambda e: scroll_canvas.itemconfig(toolbar_window, width=e.width))

        def on_mousewheel(event):
            scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        scroll_canvas.bind("<MouseWheel>", on_mousewheel)
        toolbar.bind("<MouseWheel>", on_mousewheel)

        self._tool_buttons = {}

        def section(text):
            tk.Label(toolbar, text=text, bg=self.PANEL_COLOR, fg=self.SUBTLE_COLOR, font=("Segoe UI", 7)).pack(pady=(8, 2))

        def tool_btn(label, tool, font_size=9):
            btn = tk.Button(toolbar, text=label, bg=self.BTN_COLOR, fg="white", relief="flat", font=("Segoe UI", font_size), cursor="hand2", anchor="w", padx=8, command=lambda t=tool: self._set_tool(t))
            btn.pack(fill="x", padx=6, pady=2)
            self._tool_buttons[tool] = btn

        section("DRAW")
        tool_btn("Pen", "pen"); tool_btn("Text", "text"); tool_btn("Eraser", "eraser")

        section("SHAPES")
        shape_grid = tk.Frame(toolbar, bg=self.PANEL_COLOR)
        shape_grid.pack(padx=6, pady=2)
        for i, (icon, tool) in enumerate([("▭","rect"),("○","circle"),("△","triangle"),("╱","line"),("➡","arrow")]):
            btn = tk.Button(shape_grid, text=icon, bg=self.BTN_COLOR, fg="white", relief="flat", font=("Segoe UI", 14), cursor="hand2", width=3, command=lambda t=tool: self._set_tool(t))
            btn.grid(row=i // 3, column=i % 3, padx=2, pady=2)
            self._tool_buttons[tool] = btn

        check_frame = tk.Frame(toolbar, bg=self.PANEL_COLOR)
        check_frame.pack(anchor="w", padx=6, pady=(4, 0))
        self.fill_var = tk.BooleanVar(value=False)
        tk.Checkbutton(check_frame, text="Fill", variable=self.fill_var, bg=self.PANEL_COLOR, fg="white", selectcolor=self.ACCENT_COLOR, activebackground=self.PANEL_COLOR, font=("Segoe UI", 8), cursor="hand2", command=lambda: setattr(self, "fill_shape", self.fill_var.get())).pack(side="left")
        self.highlight_var = tk.BooleanVar(value=False)
        tk.Checkbutton(check_frame, text="Highlight", variable=self.highlight_var, bg=self.PANEL_COLOR, fg="white", selectcolor=self.ACCENT_COLOR, activebackground=self.PANEL_COLOR, font=("Segoe UI", 8), cursor="hand2", command=lambda: setattr(self, "highlight_mode", self.highlight_var.get())).pack(side="left")

        section("HIGHLIGHT OPACITY")
        self.opacity_var = tk.IntVar(value=120)
        tk.Scale(toolbar, from_=200, to=10, orient="horizontal", variable=self.opacity_var, bg=self.PANEL_COLOR, fg="white", highlightthickness=0, troughcolor=self.BTN_COLOR, showvalue=False, command=lambda v: setattr(self, "highlight_opacity", int(v))).pack(fill="x", padx=6)

        section("ANNOTATIONS")
        tool_btn("Step Arrow", "step")
        tk.Button(toolbar, text="Reset Steps", bg=self.BTN_COLOR, fg="white", relief="flat", font=("Segoe UI", 9), cursor="hand2", anchor="w", padx=8, command=self._reset_steps).pack(fill="x", padx=6, pady=2)
        tool_btn("Callout Box", "callout"); tool_btn("Redact", "redact")

        section("BLUR")
        tool_btn("Inside", "blur_inside"); tool_btn("Outside", "blur_outside")

        section("OCR")
        tool_btn("Extract Text", "ocr")
        tk.Label(toolbar, text="Draw box over text\nto extract it", bg=self.PANEL_COLOR, fg=self.SUBTLE_COLOR, font=("Segoe UI", 7), justify="left").pack(padx=6, anchor="w")

        section("ZOOM")
        zoom_frame = tk.Frame(toolbar, bg=self.PANEL_COLOR)
        zoom_frame.pack(fill="x", padx=6, pady=2)
        tk.Button(zoom_frame, text="  +  ", bg=self.BTN_COLOR, fg="white", relief="flat", font=("Segoe UI", 10), cursor="hand2", command=self._zoom_in).pack(side="left", expand=True, fill="x", padx=(0, 2))
        tk.Button(zoom_frame, text="  -  ", bg=self.BTN_COLOR, fg="white", relief="flat", font=("Segoe UI", 10), cursor="hand2", command=self._zoom_out).pack(side="left", expand=True, fill="x", padx=(2, 0))
        tk.Button(toolbar, text="Reset Zoom", bg=self.BTN_COLOR, fg=self.SUBTLE_COLOR, relief="flat", font=("Segoe UI", 8), cursor="hand2", command=self._zoom_reset).pack(fill="x", padx=6, pady=(2, 0))

        section("STROKE")
        self.width_var = tk.IntVar(value=3)
        tk.Scale(toolbar, from_=1, to=10, orient="horizontal", variable=self.width_var, bg=self.PANEL_COLOR, fg="white", highlightthickness=0, troughcolor=self.BTN_COLOR, command=lambda v: setattr(self, "line_width", int(v))).pack(fill="x", padx=6)

        section("COLOUR")
        color_grid = tk.Frame(toolbar, bg=self.PANEL_COLOR)
        color_grid.pack(padx=6)
        for i, col in enumerate(self.PRESET_COLORS):
            tk.Button(color_grid, bg=col, width=2, height=1, relief="flat", cursor="hand2", command=lambda c=col: self._set_color(c)).grid(row=i // 4, column=i % 4, padx=1, pady=1)
        tk.Button(toolbar, text="Custom Colour", bg=self.BTN_COLOR, fg="white", relief="flat", font=("Segoe UI", 8), cursor="hand2", command=self._pick_custom_color).pack(fill="x", padx=6, pady=(4, 2))
        self.color_swatch = tk.Label(toolbar, bg=self.active_color, height=1)
        self.color_swatch.pack(fill="x", padx=6, pady=(0, 4))

        section("TEMPLATES")
        for name in ["Bug Report", "Step Complete", "Important", "Confidential", "Custom Watermark", "Clean Border"]:
            tk.Button(toolbar, text=name, bg=self.BTN_COLOR, fg="white", relief="flat", font=("Segoe UI", 8), cursor="hand2", anchor="w", padx=8, command=lambda n=name: self._apply_template(n)).pack(fill="x", padx=6, pady=2)

        self._set_tool("pen")

    def _build_bottom_bar(self):
        bottom = tk.Frame(self.window, bg=self.BG_COLOR, padx=8, pady=8)
        bottom.pack(fill="x")
        tk.Label(bottom, text="Comment:", bg=self.BG_COLOR, fg=self.SUBTLE_COLOR, font=("Segoe UI", 9)).pack(side="left", padx=(0, 6))
        self.comment_box = tk.Text(bottom, height=2, bg=self.PANEL_COLOR, fg=self.TEXT_COLOR, insertbackground="white", relief="flat", font=("Segoe UI", 10), padx=6, pady=4, wrap="word")
        self.comment_box.pack(side="left", fill="x", expand=True)
        self.comment_box.bind("<Control-Return>", lambda e: self._on_save())
        tk.Button(bottom, text="Skip", bg=self.BTN_COLOR, fg="white", relief="flat", padx=12, pady=4, cursor="hand2", font=("Segoe UI", 9), command=self._on_skip).pack(side="right", padx=(6, 0))
        tk.Button(bottom, text="Save", bg=self.ACCENT_COLOR, fg="white", relief="flat", padx=12, pady=4, cursor="hand2", font=("Segoe UI", 9), command=self._on_save).pack(side="right", padx=(6, 0))
        tk.Label(bottom, text="Ctrl+Enter to save", bg=self.BG_COLOR, fg=self.SUBTLE_COLOR, font=("Segoe UI", 7)).pack(side="right", padx=(0, 8))

    def _set_tool(self, tool):
        self.active_tool = tool
        for t, btn in self._tool_buttons.items():
            btn.config(bg=self.ACCENT_COLOR if t == tool else self.BTN_COLOR)

    def _set_color(self, color):
        self.active_color = color
        self.color_swatch.config(bg=color)

    def _pick_custom_color(self):
        result = colorchooser.askcolor(color=self.active_color, title="Pick a colour", parent=self.window)
        if result and result[1]:
            self._set_color(result[1])

    def _render_canvas(self):
        composite = Image.alpha_composite(self.orig_image, self.draw_layer)
        zoomed_w  = int(self.canvas_w * self.zoom_level)
        zoomed_h  = int(self.canvas_h * self.zoom_level)
        display   = composite.convert("RGB").resize((zoomed_w, zoomed_h), Image.LANCZOS)
        self._tk_image = ImageTk.PhotoImage(display)
        self.canvas.config(scrollregion=(0, 0, zoomed_w, zoomed_h))
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._tk_image)

    def _canvas_to_image(self, x, y):
        return int(x / (self.image_scale * self.zoom_level)), int(y / (self.image_scale * self.zoom_level))

    def _save_undo_state(self):
        self.redo_stack.clear()
        self.undo_stack.append({"draw": self.draw_layer.copy(), "orig": self.orig_image.copy()})
        if len(self.undo_stack) > 30:
            self.undo_stack.pop(0)

    def _zoom_in(self):
        self.zoom_level = min(self.zoom_level + 0.25, 3.0)
        self._render_canvas()

    def _zoom_out(self):
        self.zoom_level = max(self.zoom_level - 0.25, 0.25)
        self._render_canvas()

    def _zoom_reset(self):
        self.zoom_level = 1.0
        self._render_canvas()

    def _reset_steps(self):
        self.step_counter = 1

    def _snap_to_axis(self, x0, y0, x1, y1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        return (x0, y0, x1, y0) if dx > dy else (x0, y0, x0, y1)

    def _on_press(self, event):
        self._drag_start = (event.x, event.y)
        self._pen_points = [(event.x, event.y)]
        if self.active_tool == "text":
            self._handle_text(event)
        elif self.active_tool == "step":
            self._handle_step(event)
        elif self.active_tool == "eraser":
            self._save_undo_state()

    def _on_drag(self, event):
        if not self._drag_start:
            return
        x0, y0 = self._drag_start
        if self.active_tool == "pen":
            self._pen_points.append((event.x, event.y))
            if len(self._pen_points) >= 2:
                p1, p2 = self._pen_points[-2], self._pen_points[-1]
                self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=self.active_color, width=self.line_width, smooth=True, tags="preview")
        elif self.active_tool == "eraser":
            ix, iy = self._canvas_to_image(event.x, event.y)
            es = max(1, int(self.eraser_size / self.image_scale))
            ImageDraw.Draw(self.draw_layer).ellipse([ix - es, iy - es, ix + es, iy + es], fill=(0, 0, 0, 0))
            self.draw_context = ImageDraw.Draw(self.draw_layer)
            self._render_canvas()
        else:
            x1, y1 = event.x, event.y
            if self._shift_held and self.active_tool in ("line", "arrow", "rect"):
                x0, y0, x1, y1 = self._snap_to_axis(x0, y0, x1, y1)
            self.canvas.delete("preview")
            self._draw_shape_preview(x0, y0, x1, y1)

    def _on_release(self, event):
        if not self._drag_start:
            return
        x0, y0 = self._drag_start
        x1, y1 = event.x, event.y
        if self._shift_held and self.active_tool in ("line", "arrow", "rect"):
            x0, y0, x1, y1 = self._snap_to_axis(x0, y0, x1, y1)
        ix0, iy0 = self._canvas_to_image(x0, y0)
        ix1, iy1 = self._canvas_to_image(x1, y1)

        if self.active_tool == "pen":
            self._save_undo_state(); self._commit_pen(self._pen_points, width=self.line_width)
        elif self.active_tool in ("rect", "circle", "triangle", "line", "arrow"):
            self._save_undo_state(); self._commit_shape(ix0, iy0, ix1, iy1)
        elif self.active_tool == "callout":
            self._save_undo_state(); self._commit_callout(ix0, iy0, ix1, iy1)
        elif self.active_tool == "redact":
            self._save_undo_state(); self._commit_redact(ix0, iy0, ix1, iy1)
        elif self.active_tool in ("blur_inside", "blur_outside"):
            self._save_undo_state(); self._commit_blur(ix0, iy0, ix1, iy1)
        elif self.active_tool == "ocr":
            self._commit_ocr(ix0, iy0, ix1, iy1)

        self._drag_start = None
        self._pen_points = []
        self.canvas.delete("preview")
        self._render_canvas()

    def _commit_pen(self, points, width=3):
        if len(points) < 2:
            return
        img_points = [self._canvas_to_image(x, y) for x, y in points]
        r, g, b    = self._hex_to_rgb(self.active_color)
        for i in range(len(img_points) - 1):
            self.draw_context.line([img_points[i], img_points[i + 1]], fill=(r, g, b, 255), width=max(1, int(width / self.image_scale)))

    def _commit_shape(self, x0, y0, x1, y1):
        r, g, b = self._hex_to_rgb(self.active_color)
        w       = max(1, int(self.line_width / self.image_scale))
        if self.highlight_mode:
            fill = outline = (r, g, b, self.highlight_opacity)
        elif self.fill_shape:
            fill = outline = (r, g, b, 255)
        else:
            fill, outline = None, (r, g, b, 255)

        if self.active_tool == "rect":
            self.draw_context.rectangle([x0, y0, x1, y1], outline=outline, fill=fill, width=w)
        elif self.active_tool == "circle":
            self.draw_context.ellipse([x0, y0, x1, y1], outline=outline, fill=fill, width=w)
        elif self.active_tool == "triangle":
            self.draw_context.polygon([((x0+x1)//2, y0), (x0, y1), (x1, y1)], outline=outline, fill=fill)
        elif self.active_tool == "line":
            self.draw_context.line([x0, y0, x1, y1], fill=outline, width=w)
        elif self.active_tool == "arrow":
            self._draw_arrow_on_layer(x0, y0, x1, y1, outline, w)

    def _draw_arrow_on_layer(self, x0, y0, x1, y1, color, width):
        self.draw_context.line([x0, y0, x1, y1], fill=color, width=width)
        angle      = math.atan2(y1 - y0, x1 - x0)
        arrow_size = max(20, width * 8)
        self.draw_context.polygon([
            (x1, y1),
            (int(x1 - arrow_size * math.cos(angle - math.pi/6)), int(y1 - arrow_size * math.sin(angle - math.pi/6))),
            (int(x1 - arrow_size * math.cos(angle + math.pi/6)), int(y1 - arrow_size * math.sin(angle + math.pi/6)))
        ], fill=color)

    def _handle_step(self, event):
        self._save_undo_state()
        ix, iy  = self._canvas_to_image(event.x, event.y)
        r, g, b = self._hex_to_rgb(self.active_color)
        color   = (r, g, b, 255)
        radius  = max(14, int(16 / self.image_scale))
        self.draw_context.ellipse([ix-radius, iy-radius, ix+radius, iy+radius], fill=color, outline=color)
        num_text = str(self.step_counter)
        try:
            font = ImageFont.truetype("arialbd.ttf", size=max(12, int(14 / self.image_scale)))
        except (OSError, IOError):
            font = None
        bbox = self.draw_context.textbbox((0, 0), num_text, font=font)
        self.draw_context.text((ix - (bbox[2]-bbox[0])//2, iy - (bbox[3]-bbox[1])//2), num_text, fill=(255,255,255,255), font=font)
        tail_len = radius + max(20, int(24 / self.image_scale))
        self._draw_arrow_on_layer(ix+radius, iy, ix+tail_len, iy, color, max(1, int(2/self.image_scale)))
        self.step_counter += 1
        self._render_canvas()

    def _commit_callout(self, x0, y0, x1, y1):
        r, g, b  = self._hex_to_rgb(self.active_color)
        color    = (r, g, b, 255)
        w        = max(1, int(self.line_width / self.image_scale))
        bx0, by0 = min(x0,x1), min(y0,y1)
        bx1, by1 = max(x0,x1), max(y0,y1)
        self.draw_context.rounded_rectangle([bx0,by0,bx1,by1], radius=min(10,(bx1-bx0)//4,(by1-by0)//4), outline=color, fill=(r,g,b,40), width=w)
        tail_x = (bx0+bx1)//2
        self.draw_context.polygon([(tail_x-8,by1),(tail_x+8,by1),(tail_x, by1+max(16,int(20/self.image_scale)))], fill=color)
        text = simpledialog.askstring("Callout Text", "Enter callout text:", parent=self.window)
        if text:
            try:
                font = ImageFont.truetype("arial.ttf", size=max(12, int(13/self.image_scale)))
            except (OSError, IOError):
                font = None
            padding = max(6, int(8/self.image_scale))
            self.draw_context.text((bx0+padding, by0+padding), text, fill=color, font=font)

    def _commit_redact(self, x0, y0, x1, y1):
        bx0,by0 = min(x0,x1),min(y0,y1)
        bx1,by1 = max(x0,x1),max(y0,y1)
        self.draw_context.rectangle([bx0,by0,bx1,by1], fill=(0,0,0,255), outline=(0,0,0,255))

    def _commit_blur(self, x0, y0, x1, y1):
        bx0,by0 = min(x0,x1),min(y0,y1)
        bx1,by1 = max(x0,x1),max(y0,y1)
        if bx1<=bx0 or by1<=by0:
            return
        base    = Image.alpha_composite(self.orig_image, self.draw_layer).convert("RGBA")
        blurred = base.filter(ImageFilter.GaussianBlur(radius=15))
        if self.active_tool == "blur_inside":
            base.paste(blurred.crop((bx0,by0,bx1,by1)), (bx0,by0))
        else:
            clear = base.crop((bx0,by0,bx1,by1))
            base  = blurred.copy()
            base.paste(clear, (bx0,by0))
        self.orig_image   = base
        self.draw_layer   = Image.new("RGBA", self.orig_image.size, (0,0,0,0))
        self.draw_context = ImageDraw.Draw(self.draw_layer)

    def _commit_ocr(self, x0, y0, x1, y1):
        bx0,by0 = min(x0,x1),min(y0,y1)
        bx1,by1 = max(x0,x1),max(y0,y1)
        if bx1<=bx0 or by1<=by0:
            return
        try:
            import pytesseract, shutil
            pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            extracted = pytesseract.image_to_string(self.orig_image.crop((bx0,by0,bx1,by1)).convert("RGB")).strip()
            if extracted:
                self.comment_box.insert(tk.INSERT, extracted + " ")
                self.comment_box.focus_set()
            else:
                messagebox.showinfo("No Text Found", "Could not read any text in that area.", parent=self.window)
        except ImportError:
            messagebox.showwarning("Tesseract Not Installed", "Run: pip install pytesseract\nThen install Tesseract from:\nhttps://github.com/UB-Mannheim/tesseract/wiki", parent=self.window)
        except Exception as e:
            print(f"OCR failed: {e}")

    def _handle_text(self, event):
        text = simpledialog.askstring("Add Text", "Enter your label:", parent=self.window)
        if not text:
            return
        self._save_undo_state()
        ix, iy  = self._canvas_to_image(event.x, event.y)
        r, g, b = self._hex_to_rgb(self.active_color)
        try:
            font = ImageFont.truetype("arial.ttf", size=max(16, int(20/self.image_scale)))
        except (OSError, IOError):
            font = None
        self.draw_context.text((ix, iy), text, fill=(r,g,b,255), font=font)
        self._render_canvas()

    def _apply_template(self, name):
        self._save_undo_state()
        w, h = self.orig_image.size

        if name == "Bug Report":
            self.draw_context.rectangle([0,0,w-1,h-1], outline=(231,76,60,255), width=max(4,w//150))
            self._stamp_label("BUG", x=10, y=10, bg=(231,76,60,255))

        elif name == "Step Complete":
            font_size = max(16, w//20)
            padding   = max(8, font_size//3)
            self.draw_context.rectangle([0,0,w-1,h-1], outline=(46,204,113,255), width=max(4,w//150))
            try:
                font = ImageFont.truetype("arialbd.ttf", size=font_size)
            except (OSError, IOError):
                font = None
            bbox    = self.draw_context.textbbox((0,0), "DONE", font=font)
            stamp_w = bbox[2]-bbox[0] + padding*2
            self._stamp_label("DONE", x=w-stamp_w-10, y=10, bg=(46,204,113,255))

        elif name == "Important":
            banner_h  = max(40, h//15)
            font_size = max(18, banner_h//2)
            self.draw_context.rectangle([0,0,w,banner_h], fill=(241,196,15,220))
            try:
                font = ImageFont.truetype("arialbd.ttf", size=font_size)
            except (OSError, IOError):
                font = None
            padding = banner_h//4
            self.draw_context.text((padding, padding), "IMPORTANT", fill=(0,0,0,255), font=font)

        elif name == "Confidential":
            self._apply_watermark_text("CONFIDENTIAL", color=(200,0,0,90))

        elif name == "Custom Watermark":
            text = simpledialog.askstring("Custom Watermark", "Enter watermark text:", initialvalue=self._last_watermark, parent=self.window)
            if not text:
                return
            self._last_watermark = text
            r, g, b = self._hex_to_rgb(self.active_color)
            self._apply_watermark_text(text, color=(r,g,b,90))

        elif name == "Clean Border":
            self.draw_context.rectangle([0,0,w-1,h-1], outline=(80,80,80,255), width=max(4,w//150))

        self._render_canvas()

    def _apply_watermark_text(self, text, color):
        """
        Renders a diagonal centred watermark scaled to fit within the image.
        Font size is reduced iteratively until the text width fits within
        85% of the shorter image dimension before rotation, ensuring it
        remains fully visible after the 45-degree rotation is applied.
        """
        w, h      = self.orig_image.size
        max_width = min(w, h) * 0.85

        font_size = max(12, min(w, h) // 4)
        font      = None
        for _ in range(20):
            try:
                font = ImageFont.truetype("arialbd.ttf", size=font_size)
            except (OSError, IOError):
                font = None
            tmp  = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
            bbox = tmp.textbbox((0, 0), text, font=font)
            if (bbox[2] - bbox[0]) <= max_width:
                break
            font_size = max(10, int(font_size * 0.8))

        txt_img = Image.new("RGBA", self.orig_image.size, (0, 0, 0, 0))
        d       = ImageDraw.Draw(txt_img)
        bbox    = d.textbbox((0, 0), text, font=font)
        tw      = bbox[2] - bbox[0]
        th      = bbox[3] - bbox[1]
        d.text(((w - tw) // 2, (h - th) // 2), text, fill=color, font=font)
        txt_img = txt_img.rotate(45, expand=False)

        self.orig_image   = Image.alpha_composite(self.orig_image, txt_img)
        self.draw_layer   = Image.new("RGBA", self.orig_image.size, (0, 0, 0, 0))
        self.draw_context = ImageDraw.Draw(self.draw_layer)

    def _stamp_label(self, text, x, y, bg):
        font_size = max(12, self.orig_image.width // 40)
        try:
            font = ImageFont.truetype("arialbd.ttf", size=font_size)
        except (OSError, IOError):
            font = None
        padding = max(8, font_size//3)
        bbox    = self.draw_context.textbbox((0,0), text, font=font)
        tw      = bbox[2]-bbox[0] + padding*2
        th      = bbox[3]-bbox[1] + padding*2
        self.draw_context.rectangle([x, y, x+tw, y+th], fill=bg)
        self.draw_context.text((x+padding, y+padding), text, fill=(255,255,255,255), font=font)

    def _draw_shape_preview(self, x0, y0, x1, y1):
        col  = self.active_color
        w    = self.line_width
        fill = col if (self.fill_shape or self.highlight_mode) else ""
        if self.active_tool == "rect":
            self.canvas.create_rectangle(x0,y0,x1,y1, outline=col,fill=fill,width=w,tags="preview")
        elif self.active_tool == "circle":
            self.canvas.create_oval(x0,y0,x1,y1, outline=col,fill=fill,width=w,tags="preview")
        elif self.active_tool == "triangle":
            self.canvas.create_polygon((x0+x1)//2,y0,x0,y1,x1,y1, outline=col,fill=fill,width=w,tags="preview")
        elif self.active_tool == "line":
            self.canvas.create_line(x0,y0,x1,y1, fill=col,width=w,tags="preview")
        elif self.active_tool == "arrow":
            self.canvas.create_line(x0,y0,x1,y1, fill=col,width=w,arrow=tk.LAST,arrowshape=(16,20,6),tags="preview")
        elif self.active_tool == "callout":
            self.canvas.create_rectangle(x0,y0,x1,y1, outline=col,fill="",width=w,dash=(4,3),tags="preview")
        elif self.active_tool == "redact":
            self.canvas.create_rectangle(x0,y0,x1,y1, outline="#000000",fill="#000000",tags="preview")
        elif self.active_tool in ("blur_inside","blur_outside"):
            self.canvas.create_rectangle(x0,y0,x1,y1, outline="#3498db",fill="",width=2,dash=(6,4),tags="preview")
        elif self.active_tool == "ocr":
            self.canvas.create_rectangle(x0,y0,x1,y1, outline="#2ecc71",fill="",width=2,dash=(4,3),tags="preview")

    def _undo(self):
        if self.undo_stack:
            self.redo_stack.append({"draw": self.draw_layer.copy(), "orig": self.orig_image.copy()})
            state             = self.undo_stack.pop()
            self.draw_layer   = state["draw"]
            self.orig_image   = state["orig"]
            self.draw_context = ImageDraw.Draw(self.draw_layer)
            self._render_canvas()

    def _redo(self):
        if self.redo_stack:
            self._save_undo_state()
            state             = self.redo_stack.pop()
            self.draw_layer   = state["draw"]
            self.orig_image   = state["orig"]
            self.draw_context = ImageDraw.Draw(self.draw_layer)
            self._render_canvas()

    def _clear_all(self):
        self._save_undo_state()
        self.draw_layer   = Image.new("RGBA", self.orig_image.size, (0,0,0,0))
        self.draw_context = ImageDraw.Draw(self.draw_layer)
        self._render_canvas()

    def _on_save(self):
        final = Image.alpha_composite(self.orig_image, self.draw_layer).convert("RGB")
        final.save(self.image_path)
        comment = self.comment_box.get("1.0", "end-1c").strip()
        if comment:
            save_comment(self.image_path, comment)
        self.window.destroy()
        if self.on_complete:
            self.on_complete(self.image_path)

    def _on_skip(self):
        self.window.destroy()

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
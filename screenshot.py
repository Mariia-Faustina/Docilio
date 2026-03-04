import mss
import mss.tools
import time
import threading
import tkinter as tk
from PIL import ImageGrab
from file_manager import get_next_screenshot_name

MIN_REGION_SIZE = 10  # Minimum pixel dimensions for a region capture


def _restore_toolbar(toolbar_window, width, height, x, y, callback, path):
    """Restores the toolbar to its original position and triggers the callback."""
    toolbar_window.geometry(f"{width}x{height}+{x}+{y}")
    toolbar_window.minsize(width, height)
    toolbar_window.update_idletasks()
    toolbar_window.deiconify()
    toolbar_window.update()
    # Re-apply overrideredirect after deiconify, otherwise the toolbar border reappears
    toolbar_window.overrideredirect(True)
    toolbar_window.lift()
    toolbar_window.attributes("-topmost", True)
    toolbar_window.after(50, lambda: toolbar_window.geometry(f"{width}x{height}+{x}+{y}"))
    toolbar_window.after(100, lambda: callback(path))


def take_fullscreen(toolbar_window, on_complete):
    """Captures the full primary monitor. Runs on a background thread."""
    width  = toolbar_window.winfo_width()
    height = toolbar_window.winfo_height()
    x      = toolbar_window.winfo_x()
    y      = toolbar_window.winfo_y()

    def _capture():
        toolbar_window.withdraw()
        time.sleep(0.3)
        try:
            with mss.mss() as sct:
                screenshot = sct.grab(sct.monitors[1])
                save_path  = get_next_screenshot_name()
                mss.tools.to_png(screenshot.rgb, screenshot.size, output=save_path)
            toolbar_window.after(0, lambda: _restore_toolbar(
                toolbar_window, width, height, x, y, on_complete, save_path
            ))
        except Exception as e:
            print(f"Capture failed: {e}")
            toolbar_window.after(0, lambda: (
                toolbar_window.deiconify(),
                toolbar_window.overrideredirect(True),
                toolbar_window.attributes("-topmost", True)
            ))

    threading.Thread(target=_capture, daemon=True).start()


def take_region(toolbar_window, on_complete):
    """Shows a fullscreen overlay for the user to draw a selection region."""
    width  = toolbar_window.winfo_width()
    height = toolbar_window.winfo_height()
    x      = toolbar_window.winfo_x()
    y      = toolbar_window.winfo_y()

    toolbar_window.withdraw()
    toolbar_window.update_idletasks()
    time.sleep(0.2)

    overlay = tk.Toplevel()
    overlay.attributes("-fullscreen", True)
    overlay.attributes("-topmost", True)
    overlay.attributes("-alpha", 0.3)
    overlay.configure(bg="black")
    overlay.overrideredirect(True)

    canvas = tk.Canvas(overlay, cursor="cross", bg="grey11", highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    overlay.focus_force()
    canvas.focus_set()

    canvas.create_text(
        overlay.winfo_screenwidth() // 2, 40,
        text="Click and drag to select a region  |  Esc to cancel",
        fill="white", font=("Segoe UI", 14)
    )

    # Using lists here because inner functions cannot rebind outer-scope variables directly
    start   = [None, None]
    rect_id = [None]

    def on_mouse_press(event):
        start[0] = event.x
        start[1] = event.y
        rect_id[0] = canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline="#e67e22", width=3, fill=""
        )

    def on_mouse_drag(event):
        if rect_id[0] is not None:
            canvas.coords(rect_id[0], start[0], start[1], event.x, event.y)
            canvas.delete("corners")
            size = 4
            for cx, cy in [(start[0], start[1]), (event.x, start[1]),
                           (start[0], event.y), (event.x, event.y)]:
                canvas.create_oval(
                    cx - size, cy - size, cx + size, cy + size,
                    fill="#e67e22", outline="white", tags="corners"
                )

    def on_mouse_release(event):
        x1 = min(start[0], event.x)
        y1 = min(start[1], event.y)
        x2 = max(start[0], event.x)
        y2 = max(start[1], event.y)

        # Ignore accidental clicks with no meaningful drag
        if (x2 - x1) < MIN_REGION_SIZE or (y2 - y1) < MIN_REGION_SIZE:
            overlay.destroy()
            toolbar_window.after(0, lambda: _restore_toolbar(
                toolbar_window, width, height, x, y, lambda _: None, ""
            ))
            return

        overlay.destroy()
        time.sleep(0.1)

        img       = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        save_path = get_next_screenshot_name()
        img.save(save_path)

        toolbar_window.after(0, lambda: _restore_toolbar(
            toolbar_window, width, height, x, y, on_complete, save_path
        ))

    def on_cancel(event=None):
        overlay.destroy()
        toolbar_window.deiconify()
        toolbar_window.update()
        toolbar_window.overrideredirect(True)
        toolbar_window.lift()
        toolbar_window.attributes("-topmost", True)

    canvas.bind("<ButtonPress-1>",   on_mouse_press)
    canvas.bind("<B1-Motion>",       on_mouse_drag)
    canvas.bind("<ButtonRelease-1>", on_mouse_release)
    overlay.bind("<Escape>",         on_cancel)


def take_timed(toolbar_window, on_complete, delay_seconds=3):
    """
    Shows a small countdown indicator in the corner of the screen, then
    captures the full screen. The indicator is non-blocking so the user
    can freely interact with anything during the countdown.
    """
    width  = toolbar_window.winfo_width()
    height = toolbar_window.winfo_height()
    x      = toolbar_window.winfo_x()
    y      = toolbar_window.winfo_y()

    # A small corner widget is used instead of a fullscreen overlay.
    # A fullscreen Toplevel grabs focus and blocks interaction even with
    # WS_EX_TRANSPARENT set. A tiny always-on-top window avoids this entirely.
    screen_w = toolbar_window.winfo_screenwidth()
    screen_h = toolbar_window.winfo_screenheight()

    overlay = tk.Toplevel()
    overlay.overrideredirect(True)
    overlay.attributes("-topmost", True)
    overlay.attributes("-alpha", 0.85)
    overlay.configure(bg="#1e1e1e")

    # Position in the bottom-right corner, out of the way
    overlay.geometry(f"220x80+{screen_w - 240}+{screen_h - 160}")

    countdown_label = tk.Label(
        overlay, text="",
        bg="#1e1e1e", fg="#e67e22",
        font=("Segoe UI", 36, "bold")
    )
    countdown_label.pack(side="left", padx=(16, 8), pady=12)

    tk.Label(
        overlay,
        text="Capturing soon...",
        bg="#1e1e1e", fg="#aaaaaa",
        font=("Segoe UI", 10),
        justify="left"
    ).pack(side="left", pady=12)

    remaining = [delay_seconds]

    def tick():
        countdown_label.config(text=str(remaining[0]))
        if remaining[0] > 0:
            remaining[0] -= 1
            overlay.after(1000, tick)
        else:
            overlay.destroy()
            toolbar_window.withdraw()

            def _capture():
                time.sleep(0.3)
                try:
                    with mss.mss() as sct:
                        screenshot = sct.grab(sct.monitors[1])
                        save_path  = get_next_screenshot_name()
                        mss.tools.to_png(screenshot.rgb, screenshot.size, output=save_path)
                    toolbar_window.after(0, lambda: _restore_toolbar(
                        toolbar_window, width, height, x, y, on_complete, save_path
                    ))
                except Exception as e:
                    print(f"Timed capture failed: {e}")
                    toolbar_window.after(0, lambda: (
                        toolbar_window.deiconify(),
                        toolbar_window.overrideredirect(True),
                        toolbar_window.attributes("-topmost", True)
                    ))

            threading.Thread(target=_capture, daemon=True).start()

    tick()
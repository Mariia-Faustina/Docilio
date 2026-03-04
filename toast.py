"""
Minimal toast notification module.
Shows a small temporary popup in the bottom-right corner of the screen.
No external dependencies required.
"""
import tkinter as tk


def _show_toast(message, bg_color, duration_ms=3000):
    try:
        root = tk._default_root
        if not root:
            return

        toast = tk.Toplevel(root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.attributes("-alpha", 0.92)
        toast.configure(bg=bg_color)

        tk.Label(
            toast,
            text=message,
            bg=bg_color,
            fg="white",
            font=("Segoe UI", 9),
            padx=16, pady=10
        ).pack()

        toast.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        tw = toast.winfo_width()
        th = toast.winfo_height()
        toast.geometry(f"+{sw - tw - 20}+{sh - th - 60}")

        toast.after(duration_ms, toast.destroy)
    except Exception:
        pass  # Never crash the app over a notification


def toast_success(message):
    _show_toast(f"  {message}", bg_color="#27ae60")


def toast_error(message):
    _show_toast(f"  {message}", bg_color="#c0392b")


def toast_warning(message):
    _show_toast(f"  {message}", bg_color="#e67e22")
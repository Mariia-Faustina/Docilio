import tkinter as tk
import ctypes
import os
import sys
from ui import DocilioToolbar

__version__ = "1.0.0"

# Single-instance lock using a Windows mutex.
# If Docilio is already running, bring it to the front and exit.
_MUTEX_NAME = "DocilioSingleInstanceMutex"


def _get_resource_path(filename):
    """Returns the absolute path to a resource file.
    Works both when running as a script and as a PyInstaller executable."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)


def _acquire_single_instance_lock():
    """
    Creates a named Windows mutex. Returns the mutex handle if this is the
    first instance, or None if another instance is already running.
    """
    try:
        mutex = ctypes.windll.kernel32.CreateMutexW(None, True, _MUTEX_NAME)
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            return None
        return mutex
    except Exception:
        return True  # Non-Windows or API failure - allow launch


def _apply_icon(root):
    """
    Applies the Docilio icon via the Windows API.
    iconbitmap() does not work on overrideredirect windows,
    so WM_SETICON is sent directly to the window handle instead.
    """
    ico_path = _get_resource_path("Docilio.ico")
    try:
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        if not hwnd:
            hwnd = root.winfo_id()

        hicon = ctypes.windll.user32.LoadImageW(
            None, ico_path, 1, 0, 0, 0x00000010  # LR_LOADFROMFILE, 0 size = use actual
        )
        if hicon:
            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon)  # WM_SETICON SMALL
            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon)  # WM_SETICON BIG
    except Exception:
        pass


if __name__ == "__main__":
    mutex = _acquire_single_instance_lock()
    if mutex is None:
        # Another instance is already running - silently exit
        sys.exit(0)

    root = tk.Tk()
    app  = DocilioToolbar(root)

    # Icon must be applied after overrideredirect is set, so after(200) is used
    root.after(200, lambda: _apply_icon(root))

    root.mainloop()
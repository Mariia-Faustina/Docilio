import os
import sys

# Resolve the correct base directory whether running as a script or
# as a PyInstaller-bundled executable.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MASTER_FOLDER    = os.path.join(BASE_DIR, "master_folder")
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")


def count_screenshots():
    """Returns the number of image files currently in the capture folder."""
    if not os.path.exists(MASTER_FOLDER):
        return 0
    return len([
        f for f in os.listdir(MASTER_FOLDER)
        if f.lower().endswith(IMAGE_EXTENSIONS)
    ])


def get_next_screenshot_name():
    """
    Returns a unique file path for the next screenshot.

    Uses the highest existing capture number + 1 rather than the total
    count, so deleting files mid-session never causes filename collisions.
    Example: if capture_001 and capture_003 exist, the next will be capture_004.
    """
    os.makedirs(MASTER_FOLDER, exist_ok=True)

    existing = [
        f for f in os.listdir(MASTER_FOLDER)
        if f.lower().startswith("capture_") and f.lower().endswith(".png")
    ]

    if existing:
        nums = []
        for f in existing:
            try:
                nums.append(int(os.path.splitext(f)[0].split("_")[1]))
            except (IndexError, ValueError):
                pass
        next_num = max(nums) + 1 if nums else 1
    else:
        next_num = 1

    filename = f"capture_{str(next_num).zfill(3)}.png"
    return os.path.join(MASTER_FOLDER, filename)


def get_last_screenshot():
    """Returns the path of the most recently saved screenshot, or None."""
    if not os.path.exists(MASTER_FOLDER):
        return None

    images = sorted([
        f for f in os.listdir(MASTER_FOLDER)
        if f.lower().endswith(IMAGE_EXTENSIONS)
    ])

    return os.path.join(MASTER_FOLDER, images[-1]) if images else None


def delete_last_screenshot():
    """
    Deletes the most recent screenshot and its associated comment file.
    Returns True if a file was deleted, False if the folder was empty.
    """
    path = get_last_screenshot()
    if not path:
        return False

    os.remove(path)

    txt_path = os.path.splitext(path)[0] + ".txt"
    if os.path.exists(txt_path):
        os.remove(txt_path)

    return True


def save_comment(image_path, comment):
    """Saves a comment as a .txt file alongside the given image."""
    txt_path = os.path.splitext(image_path)[0] + ".txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(comment)


def load_comment(image_path):
    """Loads and returns the comment for a given image, or an empty string."""
    txt_path = os.path.splitext(image_path)[0] + ".txt"
    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def clear_screenshots():
    """
    Deletes all screenshots and their comment files from the capture folder.
    Returns the number of image files deleted.
    """
    if not os.path.exists(MASTER_FOLDER):
        return 0

    deleted = 0
    for file in os.listdir(MASTER_FOLDER):
        if file.lower().endswith(IMAGE_EXTENSIONS + (".txt",)):
            os.remove(os.path.join(MASTER_FOLDER, file))
            if file.lower().endswith(IMAGE_EXTENSIONS):
                deleted += 1

    return deleted


def open_master_folder():
    """Opens the capture folder in the system file explorer."""
    os.makedirs(MASTER_FOLDER, exist_ok=True)
    try:
        os.startfile(MASTER_FOLDER)
    except AttributeError:
        import subprocess
        import platform
        if platform.system() == "Darwin":
            subprocess.Popen(["open", MASTER_FOLDER])
        else:
            subprocess.Popen(["xdg-open", MASTER_FOLDER])
import ctypes
import ctypes.wintypes as wintypes
import time


user32 = ctypes.windll.user32


def find_explorer_window(filepath, timeout=3.0):
    """Find the Explorer window that shows the given file, return its RECT."""
    import os
    folder = os.path.dirname(filepath)
    filename = os.path.basename(filepath)

    start = time.time()
    while time.time() - start < timeout:
        result = _scan_explorer_windows(folder, filename)
        if result:
            return result
        time.sleep(0.3)
    return None


def _scan_explorer_windows(folder, filename):
    """Scan all windows to find an Explorer showing our folder."""
    results = []

    def enum_callback(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)
        if class_name.value == "CabinetWClass":
            title = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, title, 512)
            window_title = title.value
            folder_name = folder.split("\\")[-1] if "\\" in folder else folder
            if folder_name and (folder_name in window_title or filename in window_title):
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                cx = (rect.left + rect.right) // 2
                cy = (rect.top + rect.bottom) // 2
                results.append((cx, cy, rect.left, rect.top, rect.right, rect.bottom))
                return False
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

    if results:
        return results[0]
    return None


def get_newest_explorer_rect(timeout=3.0):
    """Get the most recently activated Explorer window position."""
    start = time.time()
    while time.time() - start < timeout:
        hwnd = _find_foreground_explorer()
        if hwnd:
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            cx = (rect.left + rect.right) // 2
            cy = (rect.top + rect.bottom) // 2
            return (cx, cy, rect.left, rect.top, rect.right, rect.bottom)
        time.sleep(0.2)
    return None


def _find_foreground_explorer():
    """Check if the foreground window is an Explorer window."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    class_name = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, class_name, 256)
    if class_name.value == "CabinetWClass":
        return hwnd
    return None

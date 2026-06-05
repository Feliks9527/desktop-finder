import ctypes
import ctypes.wintypes as wintypes
import struct
import os

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
MEM_COMMIT = 0x1000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04

LVM_FIRST = 0x1000
LVM_GETITEMCOUNT = LVM_FIRST + 4
LVM_GETITEMPOSITION = LVM_FIRST + 16
LVM_GETITEMTEXTW = LVM_FIRST + 115

LVIF_TEXT = 0x0001


class LVITEMW(ctypes.Structure):
    _fields_ = [
        ("mask", wintypes.UINT),
        ("iItem", ctypes.c_int),
        ("iSubItem", ctypes.c_int),
        ("state", wintypes.UINT),
        ("stateMask", wintypes.UINT),
        ("pszText", ctypes.c_void_p),
        ("cchTextMax", ctypes.c_int),
        ("iImage", ctypes.c_int),
        ("lParam", ctypes.c_void_p),
    ]


def find_desktop_listview():
    progman = user32.FindWindowW("Progman", "Program Manager")
    if not progman:
        return None

    def enum_child(hwnd, lparam):
        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)
        if "SysListView32" in class_name.value:
            results.append(hwnd)
            return False
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    results = []

    shelldll = user32.FindWindowW("SHELLDLL_DefView", None)

    if not shelldll:
        def find_shelldll(hwnd, lparam):
            class_name = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_name, 256)
            if class_name.value == "SHELLDLL_DefView":
                nonlocal shelldll
                shelldll = hwnd
                return False
            return True

        user32.EnumChildWindows(progman, WNDENUMPROC(find_shelldll), 0)

        if not shelldll:
            def find_worker(hwnd, lparam):
                nonlocal shelldll
                class_name = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, class_name, 256)
                if class_name.value == "WorkerW":
                    def check_child(child_hwnd, lp):
                        nonlocal shelldll
                        cn = ctypes.create_unicode_buffer(256)
                        user32.GetClassNameW(child_hwnd, cn, 256)
                        if cn.value == "SHELLDLL_DefView":
                            shelldll = child_hwnd
                            return False
                        return True
                    user32.EnumChildWindows(hwnd, WNDENUMPROC(check_child), 0)
                    if shelldll:
                        return False
                return True

            user32.EnumWindows(WNDENUMPROC(find_worker), 0)

    if shelldll:
        user32.EnumChildWindows(shelldll, WNDENUMPROC(enum_child), 0)

    return results[0] if results else None


def get_desktop_icon_positions():
    listview = find_desktop_listview()
    if not listview:
        return {}

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(listview, ctypes.byref(pid))

    process = kernel32.OpenProcess(
        PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE,
        False, pid.value
    )
    if not process:
        return {}

    positions = {}

    try:
        count = user32.SendMessageW(listview, LVM_GETITEMCOUNT, 0, 0)

        remote_point = kernel32.VirtualAllocEx(
            process, None, 8, MEM_COMMIT, PAGE_READWRITE
        )

        lvi_size = ctypes.sizeof(LVITEMW)
        remote_lvi = kernel32.VirtualAllocEx(
            process, None, lvi_size + 520, MEM_COMMIT, PAGE_READWRITE
        )
        remote_text = remote_lvi + lvi_size

        for i in range(count):
            user32.SendMessageW(listview, LVM_GETITEMPOSITION, i, remote_point)
            point_buf = (ctypes.c_byte * 8)()
            bytes_read = ctypes.c_size_t()
            kernel32.ReadProcessMemory(
                process, remote_point, point_buf, 8, ctypes.byref(bytes_read)
            )
            x, y = struct.unpack("ii", bytes(point_buf))

            lvi = LVITEMW()
            lvi.mask = LVIF_TEXT
            lvi.iItem = i
            lvi.iSubItem = 0
            lvi.pszText = remote_text
            lvi.cchTextMax = 260

            written = ctypes.c_size_t()
            kernel32.WriteProcessMemory(
                process, remote_lvi, ctypes.byref(lvi), lvi_size, ctypes.byref(written)
            )

            user32.SendMessageW(listview, LVM_GETITEMTEXTW, i, remote_lvi)

            text_buf = (ctypes.c_byte * 520)()
            kernel32.ReadProcessMemory(
                process, remote_text, text_buf, 520, ctypes.byref(bytes_read)
            )
            raw = bytes(text_buf).decode("utf-16-le")
            null_idx = raw.find("\x00")
            name = raw[:null_idx] if null_idx >= 0 else raw

            if name:
                rect = wintypes.RECT()
                user32.GetWindowRect(listview, ctypes.byref(rect))
                screen_x = rect.left + x + 20
                screen_y = rect.top + y + 20
                positions[name] = (screen_x, screen_y)

    finally:
        if remote_point:
            kernel32.VirtualFreeEx(process, remote_point, 0, MEM_RELEASE)
        if remote_lvi:
            kernel32.VirtualFreeEx(process, remote_lvi, 0, MEM_RELEASE)
        kernel32.CloseHandle(process)

    return positions


if __name__ == "__main__":
    icons = get_desktop_icon_positions()
    print(f"Found {len(icons)} desktop icons:")
    for name, pos in sorted(icons.items()):
        print(f"  {name}: ({pos[0]}, {pos[1]})")

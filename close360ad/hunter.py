import ctypes
from ctypes import wintypes

import win32gui
import win32con
import win32api
import win32process
from config import AD_TITLE_KEYWORDS, AD_CLASS_NAMES, AD_MODULE_PATTERNS, EXCLUDE_TITLE_KEYWORDS, KILL_AD_PROCESS
import whitelist
import processes


_close_callback = None
_stubborn_windows = set()


def set_close_callback(cb):
    global _close_callback
    _close_callback = cb


def _text(hwnd):
    try:
        return win32gui.GetWindowText(hwnd)
    except:
        return ''


def _cls(hwnd):
    try:
        return win32gui.GetClassName(hwnd)
    except:
        return ''


def _exe_path(hwnd):
    try:
        pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
            0, pid
        )
        if handle:
            try:
                return win32process.GetModuleFileNameEx(handle, 0)
            finally:
                win32api.CloseHandle(handle)
    except:
        pass

    try:
        pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_LIMITED_INFORMATION, 0, pid
        )
        if handle:
            try:
                buf = ctypes.create_unicode_buffer(260)
                size = ctypes.c_uint32(260)
                if ctypes.windll.kernel32.QueryFullProcessImageNameW(
                    handle, 0, buf, ctypes.byref(size)
                ):
                    return buf.value
            finally:
                win32api.CloseHandle(handle)
    except:
        pass

    try:
        pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        name = _process_name_by_pid(pid)
        if name:
            return name
    except:
        pass

    return ''


def _process_name_by_pid(pid):
    try:
        snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
        if snapshot == -1:
            return None
        try:
            class PROCESSENTRY32W(ctypes.Structure):
                _fields_ = [
                    ('dwSize', ctypes.c_uint32),
                    ('cntUsage', ctypes.c_uint32),
                    ('th32ProcessID', ctypes.c_uint32),
                    ('th32DefaultHeapID', ctypes.POINTER(ctypes.c_uint32)),
                    ('th32ModuleID', ctypes.c_uint32),
                    ('cntThreads', ctypes.c_uint32),
                    ('th32ParentProcessID', ctypes.c_uint32),
                    ('pcPriClassBase', ctypes.c_uint32),
                    ('dwFlags', ctypes.c_uint32),
                    ('szExeFile', ctypes.c_wchar * 260),
                ]
            pe = PROCESSENTRY32W()
            pe.dwSize = ctypes.sizeof(pe)
            if ctypes.windll.kernel32.Process32FirstW(snapshot, ctypes.byref(pe)):
                while True:
                    if pe.th32ProcessID == pid:
                        return pe.szExeFile
                    if not ctypes.windll.kernel32.Process32NextW(snapshot, ctypes.byref(pe)):
                        break
        finally:
            ctypes.windll.kernel32.CloseHandle(snapshot)
    except:
        pass
    return None


def _exe_name(hwnd):
    p = _exe_path(hwnd)
    return p.split('\\')[-1] if p else '—'


def _excluded(title):
    t = title.lower()
    return any(kw.lower() in t for kw in EXCLUDE_TITLE_KEYWORDS)


def _style_str(hwnd):
    try:
        s = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    except:
        return ''
    parts = []
    if s & win32con.WS_POPUP: parts.append('POPUP')
    if s & win32con.WS_CAPTION: parts.append('CAPTION')
    if s & win32con.WS_DLGFRAME: parts.append('DLGFRAME')
    if s & win32con.WS_THICKFRAME: parts.append('THICK')
    if s & win32con.WS_SYSMENU: parts.append('SYSMENU')
    if s & win32con.WS_MINIMIZEBOX: parts.append('MIN')
    if s & win32con.WS_MAXIMIZEBOX: parts.append('MAX')
    if ex & win32con.WS_EX_TOOLWINDOW: parts.append('TOOL')
    if ex & win32con.WS_EX_NOACTIVATE: parts.append('NOACT')
    if ex & win32con.WS_EX_TOPMOST: parts.append('TOPMOST')
    if ex & win32con.WS_EX_LAYERED: parts.append('LAYERED')
    return '|'.join(parts)


def _is_ad(hwnd):
    title = _text(hwnd)
    class_name = _cls(hwnd)

    if not win32gui.IsWindowVisible(hwnd):
        return False
    if _excluded(title):
        return False

    exe = _exe_path(hwnd)
    if exe and 'close360ad' in exe.lower():
        return False

    if whitelist.is_whitelisted(title, _exe_name(hwnd), class_name):
        return False

    is_360 = any(p in exe.lower() for p in AD_MODULE_PATTERNS) if exe else False

    if title:
        if is_360 and any(k in title for k in AD_TITLE_KEYWORDS):
            return True
        if is_360 and class_name in AD_CLASS_NAMES:
            return True
    else:
        if is_360:
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            if style & win32con.WS_POPUP:
                return True
        return False

    return False


def _enum_child_buttons(hwnd):
    buttons = []
    def cb(child, _):
        buttons.append((child, _cls(child), _text(child)))
        return True
    try:
        win32gui.EnumChildWindows(hwnd, cb, None)
    except:
        pass
    return buttons


def _try_kill_process(hwnd):
    try:
        pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        handle = win32api.OpenProcess(win32con.PROCESS_TERMINATE, 0, pid)
        if handle:
            try:
                win32api.TerminateProcess(handle, 0)
                return True
            finally:
                win32api.CloseHandle(handle)
    except:
        pass
    return False


def _close_offsets(hwnd):
    try:
        rect = win32gui.GetWindowRect(hwnd)
    except:
        return []
    w = rect[2] - rect[0]
    # Right-to-left offsets from top-right corner
    dx_list = [20, 30, 40, 50, 60]
    dy_list = [8, 12, 15, 18, 22]
    pts = []
    for dx in dx_list:
        for dy in dy_list:
            x = rect[2] - dx
            y = rect[1] + dy
            if 0 <= x - rect[0] < w:
                pts.append((x, y))
    return pts


def _try_close(hwnd):
    win32gui.SendMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    if not win32gui.IsWindow(hwnd):
        return

    win32gui.SendMessage(hwnd, win32con.WM_DESTROY, 0, 0)
    if not win32gui.IsWindow(hwnd):
        return

    win32gui.PostMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_CLOSE, 0)
    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    if not win32gui.IsWindow(hwnd):
        return

    for child, cls, text in _enum_child_buttons(hwnd):
        try:
            if cls in ('Button', 'QWidget', 'ToolbarWindow32', ''):
                if text in ('关闭', 'Close', '\u00D7', '', 'x'):
                    win32gui.SendMessage(child, win32con.BM_CLICK, 0, 0)
                else:
                    win32gui.SendMessage(child, win32con.WM_LBUTTONDOWN, 0, 0)
                    win32gui.SendMessage(child, win32con.WM_LBUTTONUP, 0, 0)
        except:
            pass
    if not win32gui.IsWindow(hwnd):
        return

    for cx, cy in _close_offsets(hwnd):
        pt = win32gui.ScreenToClient(hwnd, (cx, cy))
        lparam = (pt[1] << 16) | (pt[0] & 0xFFFF)
        win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, 0, lparam)
        win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)
        if not win32gui.IsWindow(hwnd):
            return

        target = win32gui.WindowFromPoint((cx, cy))
        if target and target != hwnd:
            try:
                sc = win32gui.ScreenToClient(target, (cx, cy))
                slp = (sc[1] << 16) | (sc[0] & 0xFFFF)
                win32gui.SendMessage(target, win32con.WM_LBUTTONDOWN, 0, slp)
                win32gui.SendMessage(target, win32con.WM_LBUTTONUP, 0, slp)
            except:
                pass
        if not win32gui.IsWindow(hwnd):
            return

    win32gui.ShowWindow(hwnd, win32con.SW_HIDE)

    if KILL_AD_PROCESS:
        _try_kill_process(hwnd)


def hide_process_windows(pid):
    count = 0
    def cb(hwnd, _):
        nonlocal count
        if not win32gui.IsWindowVisible(hwnd):
            return True
        try:
            tid, wpid = win32process.GetWindowThreadProcessId(hwnd)
            if wpid == pid:
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                _stubborn_windows.add(hwnd)
                count += 1
        except:
            pass
        return True
    try:
        win32gui.EnumWindows(cb, None)
    except:
        pass
    return count


def find_and_close_ads():
    global _stubborn_windows
    _stubborn_windows = {hwnd for hwnd in _stubborn_windows if win32gui.IsWindow(hwnd)}

    for hwnd in _stubborn_windows:
        try:
            if win32gui.IsWindowVisible(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
        except:
            pass

    def cb(hwnd, _):
        if _is_ad(hwnd):
            title = _text(hwnd)
            class_name = _cls(hwnd)
            exe = _exe_name(hwnd)
            try:
                _try_close(hwnd)
                if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
                    _stubborn_windows.discard(hwnd)
                    if _close_callback:
                        _close_callback(title, class_name, exe)
                else:
                    _stubborn_windows.add(hwnd)
            except:
                pass
        return True

    try:
        win32gui.EnumWindows(cb, None)
    except:
        pass


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('PageFaultCount', wintypes.DWORD),
        ('PeakWorkingSetSize', ctypes.c_size_t),
        ('WorkingSetSize', ctypes.c_size_t),
        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
        ('PagefileUsage', ctypes.c_size_t),
        ('PeakPagefileUsage', ctypes.c_size_t),
    ]


def get_memory_mb():
    try:
        pmc = PROCESS_MEMORY_COUNTERS()
        pmc.cb = ctypes.sizeof(pmc)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if ctypes.windll.psapi.GetProcessMemoryInfo(
            handle, ctypes.byref(pmc), ctypes.sizeof(pmc)
        ):
            return pmc.WorkingSetSize // (1024 * 1024)
    except:
        pass
    return 0


def list_windows(show_all=False):
    windows = []

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = _text(hwnd)
        class_name = _cls(hwnd)
        exe = _exe_path(hwnd)
        is_ad = _is_ad(hwnd)
        exc = _excluded(title)
        styles = _style_str(hwnd)
        windows.append((hwnd, title, class_name, exe, is_ad, exc, styles))
        return True

    win32gui.EnumWindows(cb, None)

    print(f'{"HWND":>10} | {"Ad":>2} | {"Ex":>2} | {"Title":<40} | {"Class":<25} | {"Exe":<18} | Styles')
    print('-' * 150)
    for hwnd, title, cls, exe, is_ad, exc, styles in windows:
        if not show_all and not title and not is_ad:
            continue
        ad_flag = 'Y' if is_ad else '.'
        ex_flag = 'Y' if exc else '.'
        disp_title = title if title else '\u2014'
        short_exe = exe.split('\\')[-1] if exe else '\u2014'
        print(f'0x{hwnd:08X} | {ad_flag:>2} | {ex_flag:>2} | {disp_title:<40s} | {cls:<25s} | {short_exe:<18s} | {styles}')


def kill_blacklisted():
    return processes.kill_blacklisted()

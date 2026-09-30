import ctypes
import sys
from ctypes import wintypes

_MUTEX_NAME = 'TranslateTool_SingleInstance'
_mutex_handle = None

ERROR_ALREADY_EXISTS = 183
SW_RESTORE = 9
SWP_NOMOVE = 0x0001
SWP_NOSIZE = 0x0002
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2

_kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
_user32 = ctypes.WinDLL('user32', use_last_error=True)

_kernel32.CreateMutexW.restype = wintypes.HANDLE
_kernel32.CreateMutexW.argtypes = [wintypes.HANDLE, wintypes.BOOL, wintypes.LPCWSTR]
_user32.FindWindowW.restype = wintypes.HWND
_user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
_user32.IsIconic.argtypes = [wintypes.HWND]
_user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.SetForegroundWindow.argtypes = [wintypes.HWND]
_user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                 ctypes.c_uint]


def acquire():
    global _mutex_handle
    if sys.platform != 'win32':
        return True
    _mutex_handle = _kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    return _kernel32.GetLastError() != ERROR_ALREADY_EXISTS


def activate_existing(window_title):
    hwnd = _user32.FindWindowW(None, window_title)
    if not hwnd:
        return
    if _user32.IsIconic(hwnd):
        _user32.ShowWindow(hwnd, SW_RESTORE)
    _user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
    _user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
    _user32.SetForegroundWindow(hwnd)


def ensure_single(window_title):
    if acquire():
        return True
    activate_existing(window_title)
    return False

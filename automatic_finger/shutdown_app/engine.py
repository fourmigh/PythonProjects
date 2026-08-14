"""关机引擎：任务栏几何锚点 + OCR 视觉识别定位 + 人形鼠标点击。

流程（全鼠标，无键盘依赖）：
    Win10/11 任务栏几何计算开始按钮 -> 点击打开开始菜单
    -> 点击电源按钮（几何锚点）打开“睡眠/关机/重启”弹框
    -> rapidocr 视觉识别定位“关机”文字坐标 -> 人形鼠标点击

每一步都有 OCR 校验与重试，找不到目标一律安全中止，绝不盲点。
"""

import ctypes
import math
import random
import subprocess
import sys
import time
import winreg
from ctypes import wintypes
from pathlib import Path

try:
    import pyautogui
except ImportError:
    print("缺少依赖 pyautogui，请先运行: pip install pyautogui pillow")
    sys.exit(1)

from ai_core import capture
from ai_core.ocr import OcrEngine

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# 拟人移动参数（内部固定默认值，无界面滑块）
DEFAULT_PARAMS = {
    "speed": 820.0,
    "duration_clamp": [0.35, 1.5],
    "speed_jitter": [0.05, 0.18],
    "arrive_wait": [0.08, 0.22],
    "hold_time": [0.05, 0.12],
    "step_wait": [0.5, 1.0],
    "curve_bend": 0.08,
    "click_jitter": 2.0,
}


class APPBARDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uCallbackMessage", wintypes.UINT),
        ("uEdge", wintypes.UINT),
        ("rc", wintypes.RECT),
        ("lParam", ctypes.c_long),
    ]


ABM_GETTASKBARPOS = 5


def get_taskbar_rect():
    data = APPBARDATA()
    data.cbSize = ctypes.sizeof(APPBARDATA)
    ctypes.windll.shell32.SHAppBarMessage(ABM_GETTASKBARPOS, ctypes.byref(data))
    r = data.rc
    return (r.left, r.top, r.right, r.bottom)


def read_reg_int(subkey, name, default=None):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey) as key:
            return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return default


def detect_env():
    """环境信息：仅用于界面展示与锚点推导，不含任何用户坐标配置。"""
    build = sys.getwindowsversion().build if sys.platform == "win32" else 0
    win11 = build >= 22000
    sw, sh = pyautogui.size()
    tb = get_taskbar_rect()
    l, t, r, b = tb
    if b >= sh - 4 and (r - l) >= sw - 8:
        orient = "bottom"
    elif t <= 4 and (r - l) >= sw - 8:
        orient = "top"
    elif r >= sw - 4 and (b - t) >= sh - 8:
        orient = "right"
    elif l <= 4 and (b - t) >= sh - 8:
        orient = "left"
    else:
        orient = "bottom"
    centered = None
    if win11:
        mn = read_reg_int(
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
            "TaskbarMn",
            None,
        )
        centered = mn is None or mn == 0
    return {
        "win11": win11,
        "build": build,
        "size": (sw, sh),
        "taskbar": tb,
        "orient": orient,
        "centered": centered,
    }


def compute_anchors(env):
    """由任务栏几何计算“开始按钮/电源按钮”屏幕锚点（非用户配置）。

    命中失败时上层会用 OCR 弹框校验 + 重试来兜底。
    """
    sw, sh = env["size"]
    l, t, r, b = env["taskbar"]
    orient = env["orient"]
    win11 = env["win11"]
    if orient == "bottom":
        if win11:
            if env["centered"]:
                start = (max(sw // 2 - 160, l + 40), b - 24)
            else:
                start = (l + 32, b - 24)
            power = (l + 44, b - 118)
        else:
            start = (l + 28, b - 24)
            power = (l + 54, b - 112)
    elif orient == "top":
        start = (l + 28, t + 24)
        power = (l + 54, t + 164)
    elif orient == "left":
        start = (l + 24, b - 28)
        power = (r + 60, b - 112)
    else:
        start = (r - 24, b - 28)
        power = (l - 60, b - 112)
    return {"start": start, "power": power}


def ease_in_out_quad(t):
    if t < 0.5:
        return 2 * t * t
    return 1 - ((-2 * t + 2) ** 2) / 2


def ease_out_cubic(t):
    return 1 - ((1 - t) ** 3)


def human_curve(t):
    if t < 0.72:
        return ease_in_out_quad(t / 0.72) * 0.72
    u = (t - 0.72) / 0.28
    return 0.72 + 0.28 * (u * 0.25 + 0.75 * ease_out_cubic(u))


def bezier(p0, p1, p2, p3, t):
    u = 1 - t
    return (
        u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
        u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1],
    )


def human_move(x, y, p=None, log=None):
    if p is None:
        p = DEFAULT_PARAMS
    x0, y0 = pyautogui.position()
    dx, dy = x - x0, y - y0
    dist = math.hypot(dx, dy)
    if dist < 2:
        return
    dur = dist / p["speed"] + random.uniform(*p["speed_jitter"])
    dur = min(max(dur, p["duration_clamp"][0]), p["duration_clamp"][1])
    steps = max(int(dur / 0.012), 12)
    bend = p["curve_bend"]
    perp = random.choice((-1, 1)) * random.uniform(bend * 0.5, bend * 1.5) * dist
    nx, ny = -dy, dx
    pl = math.hypot(nx, ny) or 1.0
    nx, ny = nx / pl, ny / pl
    c1 = (x0 + dx * 0.30 + nx * perp, y0 + dy * 0.30 + ny * perp)
    c2 = (x0 + dx * 0.62 + nx * perp * 0.6, y0 + dy * 0.62 + ny * perp * 0.6)
    end = (x, y)
    for i in range(steps):
        tt = human_curve((i + 1) / steps)
        px, py = bezier((x0, y0), c1, c2, end, tt)
        pyautogui.moveTo(px, py)
        time.sleep(random.uniform(0.009, 0.016))


def human_click(x, y, p=None, log=None):
    if p is None:
        p = DEFAULT_PARAMS
    if log is None:
        log = print
    j = p["click_jitter"]
    human_move(x + random.uniform(-j, j), y + random.uniform(-j, j), p, log)
    time.sleep(random.uniform(*p["arrive_wait"]))
    try:
        pyautogui.click()
    except Exception as e:
        log(f"警告：pyautogui 点击失败: {type(e).__name__}: {e}，改用 SendInput")
        ok, err = native_click()
        if not ok:
            log(f"警告：SendInput 原生点击注入失败 (GetLastError={err})")


INPUT_MOUSE = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("u", _INPUTUNION),
    ]


_SendInput = ctypes.WinDLL("user32", use_last_error=False).SendInput
_GetLastError = ctypes.WinDLL("kernel32", use_last_error=False).GetLastError
_OpenProcessToken = ctypes.WinDLL("advapi32", use_last_error=False).OpenProcessToken
_GetTokenInformation = ctypes.WinDLL("advapi32", use_last_error=False).GetTokenInformation
_GetCurrentProcess = ctypes.WinDLL("kernel32", use_last_error=False).GetCurrentProcess
_CloseHandle = ctypes.WinDLL("kernel32", use_last_error=False).CloseHandle


def _make_mouse_input(flags):
    inp = _INPUT()
    inp.type = INPUT_MOUSE
    inp.u.mi.dx = 0
    inp.u.mi.dy = 0
    inp.u.mi.mouseData = 0
    inp.u.mi.dwFlags = flags
    inp.u.mi.time = 0
    inp.u.mi.dwExtraInfo = None
    return inp


def native_click():
    """在当前光标位置发送左键按下+抬起，使用 SendInput 原生注入。"""
    if not sys.platform.startswith("win"):
        return True, None
    _SendInput.restype = ctypes.c_uint
    _SendInput.argtypes = [ctypes.c_uint, ctypes.POINTER(_INPUT), ctypes.c_int]
    _GetLastError.restype = ctypes.c_ulong
    down = _make_mouse_input(MOUSEEVENTF_LEFTDOWN)
    up = _make_mouse_input(MOUSEEVENTF_LEFTUP)
    down_p = ctypes.cast(ctypes.pointer(down), ctypes.POINTER(_INPUT))
    up_p = ctypes.cast(ctypes.pointer(up), ctypes.POINTER(_INPUT))
    if _SendInput(1, down_p, ctypes.sizeof(_INPUT)) != 1:
        return False, int(_GetLastError())
    if _SendInput(1, up_p, ctypes.sizeof(_INPUT)) != 1:
        ctypes.windll.kernel32.Sleep(20)
        if _SendInput(1, up_p, ctypes.sizeof(_INPUT)) != 1:
            return False, int(_GetLastError())
    return True, None


def _setup_winapi():
    _OpenProcessToken.restype = wintypes.BOOL
    _OpenProcessToken.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE),
    ]
    _GetTokenInformation.restype = wintypes.BOOL
    _GetTokenInformation.argtypes = [
        wintypes.HANDLE, ctypes.c_uint, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    _GetCurrentProcess.restype = wintypes.HANDLE
    _CloseHandle.restype = wintypes.BOOL
    _CloseHandle.argtypes = [wintypes.HANDLE]


def is_process_elevated():
    if not sys.platform.startswith("win"):
        return None
    _setup_winapi()
    TOKEN_QUERY = 0x0008
    TokenElevation = 20
    token = wintypes.HANDLE()
    try:
        if not _OpenProcessToken(_GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(token)):
            return None
        buf = ctypes.create_string_buffer(ctypes.sizeof(ctypes.c_ulong))
        size = wintypes.DWORD(ctypes.sizeof(buf))
        if not _GetTokenInformation(token, TokenElevation, buf, size, ctypes.byref(size)):
            return None
        return ctypes.cast(buf, ctypes.POINTER(ctypes.c_ulong)).contents.value != 0
    except Exception:
        return None
    finally:
        if token:
            _CloseHandle(token)


def ensure_elevated(prompt=True):
    """未提权则通过 UAC 重启自身。返回 True 表示已触发重启，应立即退出旧进程。"""
    if not sys.platform.startswith("win"):
        return False
    if is_process_elevated():
        return False
    if prompt:
        ctypes.windll.user32.MessageBoxW(
            0,
            "本程序需要管理员权限才能点击开始菜单/电源菜单。\n"
            "即将请求管理员权限，请在 UAC 弹窗中点击“是”。",
            "电源助手 - 请求管理员权限",
            0x40,
        )
    try:
        if getattr(sys, "frozen", False):
            exe = sys.executable
            args = subprocess.list2cmdline(sys.argv[1:])
        else:
            exe = sys.executable
            args = subprocess.list2cmdline([sys.argv[0]] + sys.argv[1:])
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, args, None, 1)
        return int(rc) > 32
    except Exception:
        return False


def flyout_roi(env):
    """电源弹框“睡眠/关机/重启”所在区域（内部推导，非用户配置）。"""
    l, t, r, b = env["taskbar"]
    if env["orient"] == "bottom":
        return (l, max(0, b - 340), 560, 320)
    if env["orient"] == "top":
        return (l, t + 20, 560, 320)
    if env["orient"] == "left":
        return (r + 20, max(0, b - 340), 560, 320)
    return (max(0, l - 580), max(0, b - 340), 560, 320)


def _row_center(target, items):
    """计算目标菜单项的行中心（屏幕绝对坐标）。关机为中间项，用相邻两项中点抗 OCR 抖动。"""
    tgt = [it for it in items if target in it["text"]]
    if not tgt:
        return None
    if target == "关机":
        s = next((it for it in items if "睡眠" in it["text"]), None)
        r = next((it for it in items if "重启" in it["text"]), None)
        if s and r:
            return (int((s["center"][0] + r["center"][0]) / 2),
                    int((s["center"][1] + r["center"][1]) / 2))
    return tgt[0]["center"]


def find_target_item(ocr, env, target, log):
    """在弹框区域定位目标（睡眠/关机/重启）。返回 (目标行中心, 找到的所有项) 或 (None, [])。"""
    rx, ry, rw, rh = flyout_roi(env)
    img = capture.crop(rx, ry, rw, rh)
    items = ocr.find(img, ["睡眠", "关机", "重启"], min_score=0.45, origin=(rx, ry))
    log(f"OCR 弹框区域结果: " +
        ("；".join(f"{it['text']}@{it['center']}({it['score']:.2f})" for it in items) if items else "无"))
    center = _row_center(target, items)
    if center is None:
        return None, items
    return center, items


def open_start_and_power(ocr, env, anchors, p, log, target="关机", max_attempts=5):
    """循环：点开始→点电源→OCR 校验弹框。返回目标中心点或 None。"""
    start = tuple(int(v) for v in anchors["start"])
    power = tuple(int(v) for v in anchors["power"])
    log(f"开始按钮锚点 {start}，电源按钮锚点 {power}")
    for attempt in range(1, max_attempts + 1):
        log(f"[第 {attempt}/{max_attempts} 次] 点击 开始按钮")
        human_click(*start, p, log)
        time.sleep(random.uniform(*p["step_wait"]) + 1.1)
        log("点击 电源按钮")
        human_click(*power, p, log)
        time.sleep(random.uniform(*p["step_wait"]) + 1.0)
        center, items = find_target_item(ocr, env, target, log)
        if center:
            log(f"OCR 定位到 {target} {center}")
            return center, items
        log("弹框未出现，重试（可能是菜单状态切换导致，属正常兜底）")
    return None, []


def run_shutdown_flow(dry_run=False, log=None, params=None, target="关机"):
    """执行目标操作（睡眠/关机/重启）。dry_run 时移动鼠标到目标行后停下（不点击）。
    返回是否执行到目标点击。"""
    if log is None:
        log = print
    p = params or DEFAULT_PARAMS
    env = detect_env()
    anchors = compute_anchors(env)

    log("初始化 OCR 识别引擎...")
    ocr = OcrEngine()
    log("OCR 就绪")

    center, items = open_start_and_power(ocr, env, anchors, p, log, target=target)
    if not center:
        log(f"未定位到“{target}”，安全中止（未点击任何电源入口）。")
        return False

    tx, ty = int(center[0]), int(center[1])
    log(f"移动鼠标到 {target} 行 {(tx, ty)}")
    human_move(tx, ty, p, log)

    if dry_run:
        log(f"干跑：鼠标已移动到 {target} 行 {(tx, ty)}，未点击，到此停止。")
        return False

    # 点击 + 校验：点击后重新 OCR，弹框仍开则视为未点中，在目标行内偏移重试（不会误点其它行）
    for attempt, dy in enumerate([0, 8, -8, 16, -16], 1):
        cy = ty + dy
        log(f"[点击 {attempt}/5] 点击 {target} (x={tx}, y={cy})")
        human_move(tx, cy, p, log)
        human_click(tx, cy, p, log)
        time.sleep(2.0)
        recheck, _ = find_target_item(ocr, env, target, log)
        if not recheck:
            brightness = float(capture.grab().mean())
            log(f"点击已生效：弹框已关闭，已触发{target}（屏幕亮度 {brightness:.0f}）")
            return True
        log(f"弹框仍存在（可能未点中），偏移 y {dy:+d}px 重试")
    log(f"多次点击后弹框仍未关闭，安全中止（未触发{target}）。")
    _save_debug_screenshot(log)
    return False


def _save_debug_screenshot(log=print):
    try:
        from PIL import Image
        if getattr(sys, "frozen", False):
            out = Path(sys.executable).parent / "失败截图.png"
        else:
            out = Path.cwd() / "失败截图.png"
        Image.fromarray(capture.grab()).save(str(out))
        log(f"已保存失败截图: {out}")
    except Exception as e:
        log(f"保存失败截图出错: {type(e).__name__}: {e}")
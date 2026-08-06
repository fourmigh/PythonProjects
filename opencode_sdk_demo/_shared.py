"""Opencode SDK Demo — 共享模块（数据 + 逻辑）

被 run_all.py 和 desktop/ 共同导入，消除代码重复。
"""
import importlib.util
import os
import pathlib
import subprocess
import sys
import time


# ── 路径探测（兼容开发模式和 PyInstaller 打包模式） ──────────────

def _get_base_dir():
    try:
        return pathlib.Path(sys.argv[0]).resolve().parent
    except Exception:
        return pathlib.Path(".").resolve()


BASE_DIR = _get_base_dir()
BASE_URL = "http://localhost:4096"


# ── Demo 注册表（唯一数据源） ──────────────────────────────────

DEMO_ORDER = [
    ("01_基础入门", [
        "01_HelloWorld", "02_获取应用信息", "03_查看提供商和配置", "04_配置本地模型",
    ]),
    ("02_会话管理", [
        "01_创建会话", "02_发送消息", "04_分析应用", "05_消息历史",
        "06_撤回与恢复", "07_分享与取消分享", "08_总结会话", "09_中止请求",
    ]),
    ("03_高级用法", [
        "01_异步客户端", "02_错误处理", "03_流式事件",
    ]),
    ("04_文件操作", [
        "01_读取文件", "02_文件状态",
    ]),
    ("05_代码搜索", [
        "01_搜索文件", "02_搜索文本", "03_搜索符号",
    ]),
    ("06_TUI交互", [
        "01_追加提示", "02_打开帮助",
    ]),
]

DEMOS = []
_num = 0
for cat, names in DEMO_ORDER:
    for name in names:
        _num += 1
        DEMOS.append((_num, cat, name))


# ── Demo 加载与描述 ──────────────────────────────────────────

def load_module(category, name):
    filepath = BASE_DIR / category / f"{name}.py"
    if not filepath.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")
    module_name = f"{category}.{name}"
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def get_description(category, name):
    try:
        filepath = BASE_DIR / category / f"{name}.py"
        content = filepath.read_text(encoding="utf-8")
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith('"""') and len(line) > 3:
                return line[3:].strip().rstrip('"""').strip()
            if line.startswith("'''") and len(line) > 3:
                return line[3:].strip().rstrip("'''").strip()
        return ""
    except Exception:
        return ""


# ── opencode 服务管理 ────────────────────────────────────────

_OPENCODE_PROC = None


def detect_opencode_binary():
    candidates = []
    try:
        r = subprocess.run(["where", "opencode"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            candidates.append(("win", r.stdout.strip().split("\n")[0]))
    except Exception:
        pass
    try:
        r = subprocess.run(["wsl", "which", "opencode"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            candidates.append(("wsl", r.stdout.strip()))
    except Exception:
        pass
    try:
        r = subprocess.run(["wsl", "test", "-f", "/root/.opencode/bin/opencode"], capture_output=True, timeout=5)
        if r.returncode == 0:
            candidates.append(("wsl", "/root/.opencode/bin/opencode"))
    except Exception:
        pass
    for p in [
        os.path.expanduser("~/.opencode/bin/opencode"),
        "/usr/local/bin/opencode",
        "/opt/homebrew/bin/opencode",
    ]:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            candidates.append(("native", p))
    return candidates


def _ping():
    try:
        import httpx
        r = httpx.get(f"{BASE_URL}/session", timeout=2)
        return r.status_code < 500
    except Exception:
        return False


def start_opencode(print_fn=print):
    global _OPENCODE_PROC
    candidates = detect_opencode_binary()
    if not candidates:
        print_fn("  未找到 opencode 可执行文件。")
        return False
    for env_type, binary in candidates:
        try:
            print_fn(f"  正在启动: {binary}")
            if env_type == "wsl":
                _OPENCODE_PROC = subprocess.Popen(
                    ["wsl", binary, "serve", "--port", "4096"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            else:
                _OPENCODE_PROC = subprocess.Popen(
                    [binary, "serve", "--port", "4096"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            for _ in range(20):
                time.sleep(0.5)
                if _ping():
                    print_fn(f"  服务已就绪 (PID {_OPENCODE_PROC.pid})")
                    return True
            stop_opencode()
        except FileNotFoundError:
            continue
    print_fn("  启动失败，请手动运行: opencode serve --port 4096")
    return False


def stop_opencode():
    global _OPENCODE_PROC
    if _OPENCODE_PROC is not None:
        try:
            _OPENCODE_PROC.terminate()
            _OPENCODE_PROC.wait(timeout=5)
        except Exception:
            try:
                _OPENCODE_PROC.kill()
            except Exception:
                pass
        _OPENCODE_PROC = None


def check_connection(print_fn=print):
    if _ping():
        return True
    print_fn()
    print_fn("opencode 服务未运行，正在自动启动...")
    if start_opencode(print_fn=print_fn):
        return True
    print_fn()
    print_fn("=" * 56)
    print_fn("  无法连接到 opencode 服务")
    print_fn("=" * 56)
    print_fn()
    print_fn("请确认 opencode 服务端已安装并在端口 4096 上运行:")
    print_fn()
    print_fn("  1. 手动启动: opencode serve --port 4096")
    print_fn("  2. 然后重试: python run_all.py")
    print_fn()
    return False

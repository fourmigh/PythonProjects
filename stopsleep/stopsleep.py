import time
import ctypes
import sys
from ctypes import wintypes

# --- Windows API 定义 ---
user32 = ctypes.windll.user32

# 模拟鼠标移动的 API
user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_ulong)]
user32.mouse_event.restype = None

MOUSEEVENTF_MOVE = 0x0001

# 用于防止系统进入睡眠的 API（替代方案，更底层）
kernel32 = ctypes.windll.kernel32
kernel32.SetThreadExecutionState.argtypes = [wintypes.DWORD]
kernel32.SetThreadExecutionState.restype = wintypes.DWORD

ES_SYSTEM_REQUIRED = 0x00000001
ES_CONTINUOUS = 0x80000000
ES_DISPLAY_REQUIRED = 0x00000002  # 如果需要屏幕常亮可以加上


def move_mouse_slightly():
    """让鼠标向右移动 1 像素再移回，模拟用户活动"""
    # 获取当前鼠标位置（可选，用于更精确控制）
    # 这里直接用相对移动
    user32.mouse_event(MOUSEEVENTF_MOVE, 1, 0, 0, None)   # 右移 1 像素
    time.sleep(0.01)  # 短暂停顿确保系统识别
    user32.mouse_event(MOUSEEVENTF_MOVE, -1, 0, 0, None)  # 移回


def keep_awake_with_mouse(interval=60, keep_screen_on=False):
    """
    通过模拟鼠标移动保持系统唤醒
    
    Args:
        interval: 每次模拟操作的间隔（秒），建议 30~120
        keep_screen_on: 是否同时阻止屏幕关闭（需要系统支持）
    """
    print("🟢 StopSleep 已启动，按 Ctrl+C 停止运行")
    print(f"⚙️  间隔: {interval} 秒 | 屏幕保持: {'是' if keep_screen_on else '否'}")
    
    # 先设置一次系统状态（增强兼容性）
    flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    if keep_screen_on:
        flags |= ES_DISPLAY_REQUIRED
    kernel32.SetThreadExecutionState(flags)
    
    try:
        while True:
            # 方式1: 模拟鼠标移动（主要手段）
            move_mouse_slightly()
            
            # 方式2: 同时通过 API 重置系统空闲计时器（双保险）
            kernel32.SetThreadExecutionState(flags)
            
            # 等待下一个周期
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n🔴 已退出，系统电源策略已恢复")
        # 恢复默认状态（清除连续标志即可）
        kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        sys.exit(0)


if __name__ == "__main__":
    # 参数说明：
    # - 第一个参数: 间隔秒数（建议 30~120）
    # - 第二个参数: True 表示保持屏幕常亮，False 只保持系统唤醒
    keep_awake_with_mouse(interval=60, keep_screen_on=False)
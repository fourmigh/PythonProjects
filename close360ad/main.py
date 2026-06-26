import argparse
import ctypes
import msvcrt
import threading
import time

import win32event
import win32api
import winerror

from config import SCAN_INTERVAL
from hunter import find_and_close_ads, set_close_callback, get_memory_mb, list_windows
from tray import run_tray, notify, set_tooltip, set_show_stats_callback

MUTEX_NAME = 'Global\\Close360Ad_SingleInstance'

closed_list = []
start_time = time.time()


def _enforce_single_instance():
    try:
        handle = win32event.CreateMutex(None, False, MUTEX_NAME)
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            print('Close360Ad is already running.')
            exit(0)
    except Exception:
        pass


def _scan_loop(stop_event, pause_event):
    while not stop_event.is_set():
        if not pause_event.is_set():
            try:
                find_and_close_ads()
            except Exception:
                pass
        stop_event.wait(SCAN_INTERVAL)


def _on_closed(title, class_name, exe):
    t = time.strftime('%H:%M:%S')
    closed_list.append((t, title, class_name, exe))
    count = len(closed_list)
    disp = title if title else '(无标题)'
    notify('Close360Ad', f'已关闭广告窗口 (第{count}个)\n[{t}] {disp}')
    _update_tooltip()


def _update_tooltip():
    mem = get_memory_mb()
    elapsed = int(time.time() - start_time)
    mins = elapsed // 60
    secs = elapsed % 60
    count = len(closed_list)
    status = '已暂停' if _pause_event and _pause_event.is_set() else '运行中'
    set_tooltip(f'Close360Ad | {status} {mins}:{secs:02d} | 已关 {count} | 内存 {mem} MB')


def _show_stats():
    threading.Thread(target=_show_stats_impl, daemon=True).start()

def _show_stats_impl():
    import os
    elapsed = int(time.time() - start_time)
    mins = elapsed // 60
    secs = elapsed % 60
    count = len(closed_list)
    lines = [f'运行 {mins}分{secs}秒，共关闭 {count} 个广告窗口\n']
    for t, title, cls, exe in closed_list:
        lines.append(f'[{t}] {title or "(无标题)"}  |  {cls}  |  {exe}')
    path = os.path.join(os.environ['TEMP'], 'Close360Ad_stats.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    os.startfile(path)


def _init_console():
    ctypes.windll.kernel32.AllocConsole()
    sys.stdout = open('CONOUT$', 'w', encoding='utf-8')


def main():
    import sys

    parser = argparse.ArgumentParser(description='Close360Ad - 关闭360广告弹窗')
    parser.add_argument('--list', action='store_true', help='列出可见窗口（含标题）')
    parser.add_argument('--listall', action='store_true', help='列出所有窗口（含无标题）')
    args = parser.parse_args()

    if args.list or args.listall:
        _init_console()
        list_windows(show_all=args.listall)
        print('\n按任意键退出...')
        msvcrt.getch()
        ctypes.windll.kernel32.FreeConsole()
        return

    _enforce_single_instance()

    set_close_callback(_on_closed)
    set_show_stats_callback(_show_stats)

    global _pause_event
    _pause_event = threading.Event()
    stop_event = threading.Event()

    t = threading.Thread(
        target=_scan_loop, args=(stop_event, _pause_event),
        daemon=True
    )
    t.start()

    def _tooltip_loop():
        while not stop_event.is_set():
            _update_tooltip()
            stop_event.wait(5)

    threading.Thread(target=_tooltip_loop, daemon=True).start()

    run_tray(stop_event, _pause_event)


if __name__ == '__main__':
    main()

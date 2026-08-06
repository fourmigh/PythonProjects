import argparse
import ctypes
import msvcrt
import sys
import threading
import time

import win32event
import win32api
import winerror

from config import SCAN_INTERVAL
from hunter import find_and_close_ads, set_close_callback, get_memory_mb, list_windows, kill_blacklisted
from tray import run_tray, notify, set_tooltip, set_show_stats_callback, set_show_procs_callback
import dialog

MUTEX_NAME = 'Global\\Close360Ad_SingleInstance'

closed_list = []
_last_closed_key = (None, None)
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
            try:
                killed = kill_blacklisted()
                if killed:
                    _on_closed('(黑名单)', '—', killed[0])
            except Exception:
                pass
        stop_event.wait(SCAN_INTERVAL)


def _on_closed(title, class_name, exe):
    global _last_closed_key
    t = time.strftime('%H:%M:%S')
    closed_list.append((t, title, class_name, exe))
    count = len(closed_list)
    key = (title, exe)
    if key != _last_closed_key:
        disp = title if title else '(无标题)'
        notify('Close360Ad', f'已关闭广告窗口 (第{count}个)\n[{t}] {disp}')
    _last_closed_key = key
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
    def _run():
        try:
            dialog.show_stats(list(closed_list))
        except Exception as e:
            notify('Close360Ad', f'\u7edf\u8ba1\u7a97\u53e3\u6253\u5f00\u5931\u8d25: {e}')
    threading.Thread(target=_run, daemon=True).start()


def _show_processes():
    def _run():
        try:
            dialog.show_processes()
        except Exception as e:
            notify('Close360Ad', f'\u8fdb\u7a0b\u5217\u8868\u6253\u5f00\u5931\u8d25: {e}')
    threading.Thread(target=_run, daemon=True).start()


def _init_console():
    ctypes.windll.kernel32.AllocConsole()
    sys.stdout = open('CONOUT$', 'w', encoding='utf-8')


def main():
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
    set_show_procs_callback(_show_processes)

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

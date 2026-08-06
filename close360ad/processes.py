import json
import os
import subprocess

import win32gui
import win32process
import win32api
import win32con
import win32security


BLACKLIST_FILE = os.path.join(
    os.environ.get('APPDATA', os.path.expanduser('~')), 'Close360Ad', 'blacklist.json'
)


def _ensure_dir():
    os.makedirs(os.path.dirname(BLACKLIST_FILE), exist_ok=True)


def load_blacklist():
    try:
        with open(BLACKLIST_FILE, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'exe_names': []}


def save_blacklist(data):
    _ensure_dir()
    with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_to_blacklist(exe_name):
    data = load_blacklist()
    name = exe_name.lower().strip()
    if name and name not in data['exe_names']:
        data['exe_names'].append(name)
    save_blacklist(data)


def is_blacklisted(exe_name):
    data = load_blacklist()
    return exe_name.lower().strip() in data['exe_names']


def _enable_debug_privilege():
    try:
        token = win32security.OpenProcessToken(
            win32api.GetCurrentProcess(),
            win32con.TOKEN_ADJUST_PRIVILEGES | win32con.TOKEN_QUERY,
        )
        luid = win32security.LookupPrivilegeValue(None, win32security.SE_DEBUG_NAME)
        win32security.AdjustTokenPrivileges(token, False, [(luid, win32con.SE_PRIVILEGE_ENABLED)])
    except:
        pass


def kill_process(pid):
    try:
        handle = win32api.OpenProcess(win32con.PROCESS_TERMINATE, 0, pid)
        if handle:
            try:
                win32api.TerminateProcess(handle, 0)
                return True
            finally:
                win32api.CloseHandle(handle)
    except:
        pass

    _enable_debug_privilege()
    try:
        handle = win32api.OpenProcess(win32con.PROCESS_TERMINATE, 0, pid)
        if handle:
            try:
                win32api.TerminateProcess(handle, 0)
                return True
            finally:
                win32api.CloseHandle(handle)
    except:
        pass

    try:
        subprocess.run(['taskkill', '/f', '/pid', str(pid)],
                       capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            h = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, 0, pid)
            if h:
                win32api.CloseHandle(h)
        except:
            return True
    except:
        pass

    return False


def enum_visible_processes():
    proc_info = {}
    seen_pids = set()

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        try:
            tid, pid = win32process.GetWindowThreadProcessId(hwnd)
        except:
            return True
        if pid in seen_pids:
            proc_info[pid]['window_count'] += 1
        else:
            seen_pids.add(pid)
            try:
                handle = win32api.OpenProcess(
                    win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, 0, pid
                )
                exe = ''
                if handle:
                    try:
                        exe = win32process.GetModuleFileNameEx(handle, 0)
                    finally:
                        win32api.CloseHandle(handle)
            except:
                exe = ''
            exe_name = exe.split('\\')[-1] if exe else '—'
            title = win32gui.GetWindowText(hwnd) or '(无标题)'
            proc_info[pid] = {
                'pid': pid,
                'exe_name': exe_name,
                'window_count': 1,
                'sample_title': title,
                'exe_path': exe,
            }
        return True

    win32gui.EnumWindows(cb, None)

    result = list(proc_info.values())
    result.sort(key=lambda x: x['exe_name'].lower())
    return result


def kill_blacklisted():
    killed = []
    procs = enum_visible_processes()
    for p in procs:
        if is_blacklisted(p['exe_name']):
            if kill_process(p['pid']):
                killed.append(p['exe_name'])
    return killed

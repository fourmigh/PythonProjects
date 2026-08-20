# -*- coding: utf-8 -*-
"""DiskCleaner 磁盘清理工具

Windows 磁盘清理工具：软件卸载、临时文件/缓存、大文件、重复文件、
空目录检测、软件残留检测。
所有删除操作默认进入回收站，删除前需要手动勾选并二次确认。
"""

import ctypes
import glob
import hashlib
import os
import queue
import re
import stat
import subprocess
import sys
import threading
import time
import traceback
import winreg

import tkinter as tk
from tkinter import ttk, messagebox

APP_TITLE = "DiskCleaner 磁盘清理工具"
VERSION = "2.0.0"

MB = 1024 * 1024


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def human_size(n):
    if n is None:
        return "-"
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "-"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            if unit == "B":
                return "%d B" % int(n)
            return "%.1f %s" % (n, unit)
        n /= 1024.0
    return "%d B" % int(n)


def format_delete_progress(info, elapsed):
    """把删除进度字典格式化为可读文本。"""
    done = info.get("done", 0)
    total = info.get("total", 0)
    parts = ["删除中 %d/%d" % (done, total)]
    parts.append("%d线程(活跃%d)" % (info.get("total_threads", 1), info.get("active", 0)))
    ok = info.get("ok", 0)
    fail = info.get("fail", 0)
    if ok or fail:
        parts.append("成功%d 失败%d" % (ok, fail))
    b = info.get("bytes") or 0
    if b > 0:
        parts.append("已删 %s" % human_size(b))
    rate = done / elapsed if elapsed > 0 else 0
    if rate > 0:
        parts.append("%.1f 项/秒" % rate)
        remain = total - done
        if remain > 0:
            parts.append("剩余约 %ds" % max(1, int(remain / rate)))
    return " · ".join(parts)


def build_sizes_for_paths(paths, records):
    """根据记录为路径构建并行字节数组（多路径按比例分摊，避免重复计数）。"""
    path_set = set(paths)
    size_map = {}
    for rec in records:
        rec_paths = [p for p in rec.get("paths", []) if p in path_set]
        if not rec_paths:
            continue
        per = (rec.get("size") or 0) / len(rec_paths)
        for p in rec_paths:
            if p not in size_map:
                size_map[p] = per
    return [size_map.get(p) for p in paths]


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 回收站删除（Windows API，可恢复）
# ---------------------------------------------------------------------------
FO_DELETE = 3
FOF_ALLOWUNDO = 0x40
FOF_NOCONFIRMATION = 0x10
FOF_SILENT = 0x0004
FOF_NOERRORUI = 0x0400


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("wFunc", ctypes.c_uint),
        ("pFrom", ctypes.c_wchar_p),
        ("pTo", ctypes.c_wchar_p),
        ("fFlags", ctypes.c_uint),
        ("fAnyOperationsAborted", ctypes.c_int),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", ctypes.c_wchar_p),
    ]


def send_to_recycle_bin(paths):
    """将路径列表移动到回收站（可恢复），失败返回 False。"""
    paths = [str(p) for p in paths]
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        return True
    buf = "\0".join(paths) + "\0\0"
    op = SHFILEOPSTRUCTW()
    op.hwnd = None
    op.wFunc = FO_DELETE
    op.pFrom = buf
    op.pTo = None
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    try:
        result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
        return result == 0
    except Exception:
        return False


def empty_recycle_bin():
    """清空回收站（不可恢复，需在界面二次确认后调用）。"""
    SHERB_NOCONFIRMATION = 0x0001
    SHERB_NOPROGRESSUI = 0x0002
    SHERB_NOSOUND = 0x0004
    try:
        res = ctypes.windll.shell32.SHEmptyRecycleBinW(
            None, None, SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        )
        return res == 0
    except Exception:
        return False


DELETE_BATCH = 50
DELETE_WORKERS = 4


def _coinit():
    try:
        ctypes.windll.ole32.CoInitializeEx(None, 0)
    except Exception:
        pass


def _couninit():
    try:
        ctypes.windll.ole32.CoUninitialize()
    except Exception:
        pass


def collect_all_files(path):
    """递归收集目录下所有文件路径（跳过符号链接/联接点）。"""
    files = []
    for _dir, _subdirs, fl in scan_tree(path, skip_system=False):
        for f, _s in fl:
            files.append(f)
    return files


def remove_empty_dirs(path):
    """自底向上删除已清空的子目录（尽力而为，失败忽略）。"""
    dirs = []
    for d, _subdirs, _fl in scan_tree(path, skip_system=False):
        dirs.append(d)
    for d in sorted(dirs, key=lambda x: x.count("\\"), reverse=True):
        try:
            os.rmdir(d)
        except OSError:
            pass


def delete_to_recycle_bin(paths, on_progress=None, cancel_event=None, sizes=None):
    """多线程分批将路径列表移动到回收站（加快删除且界面友好）。
    返回 (成功数, 失败数, 失败路径列表)。
    - 目录整删失败时降级为逐文件删除，跳过被占用的文件；
      failed_paths 中目录用 "路径（N 个文件被占用）" 摘要表示。
    on_progress(info) 每批回调一次，info 为字典：
      done/total  已处理/总项数
      active      当前正在工作的线程数
      total_threads 本次实际启用的线程数
      ok/fail     已成功/失败项数
      bytes       已删除字节（传入 sizes 时才有意义）
    sizes 为与 paths 平行的字节数组（可为 None 项）。"""
    total = len(paths)
    if total == 0:
        return 0, 0, []
    nworkers = min(DELETE_WORKERS, max(1, total // DELETE_BATCH + 1))
    state = {"ok": 0, "fail": 0, "done": 0, "active": 0, "bytes": 0}
    failed_paths = []
    lock = threading.Lock()

    def delete_item(p, size):
        """尝试删除单个路径，返回 (失败摘要列表, 已删字节)。"""
        if not os.path.exists(p):
            return [], 0
        if send_to_recycle_bin([p]):
            return [], (size or 0)
        if os.path.isdir(p):
            files = collect_all_files(p)
            failed = []
            deleted_bytes = 0
            for i in range(0, len(files), DELETE_BATCH):
                if cancel_event and cancel_event.is_set():
                    break
                batch = files[i:i + DELETE_BATCH]
                batch_sizes = [os.path.getsize(f) for f in batch if os.path.exists(f)]
                if send_to_recycle_bin(batch):
                    deleted_bytes += sum(batch_sizes)
                    continue
                for f in batch:
                    if cancel_event and cancel_event.is_set():
                        break
                    if os.path.exists(f):
                        sz = os.path.getsize(f)
                        if send_to_recycle_bin([f]):
                            deleted_bytes += sz
                        else:
                            failed.append(f)
            remove_empty_dirs(p)
            if failed:
                return ["%s（%d 个文件被占用）" % (p, len(failed))], deleted_bytes
            return [], deleted_bytes
        return [p], 0

    def worker(tid):
        _coinit()
        try:
            i = tid
            while True:
                if cancel_event and cancel_event.is_set():
                    return
                with lock:
                    start = i * DELETE_BATCH
                    i += nworkers
                if start >= total:
                    return
                chunk = paths[start:start + DELETE_BATCH]
                chunk_sizes = sizes[start:start + DELETE_BATCH] if sizes else None
                with lock:
                    state["active"] += 1
                success = send_to_recycle_bin(chunk)
                local_failed = []
                local_bytes = 0
                if not success:
                    for j, p in enumerate(chunk):
                        if cancel_event and cancel_event.is_set():
                            break
                        try:
                            size = chunk_sizes[j] if chunk_sizes else None
                            failed, dbytes = delete_item(p, size)
                        except Exception:
                            failed, dbytes = [str(p)], 0
                        local_failed.extend(failed)
                        local_bytes += dbytes
                    n_ok = len(chunk) - len(local_failed)
                else:
                    n_ok = len(chunk)
                    if chunk_sizes:
                        local_bytes = sum(s for s in chunk_sizes if s)
                with lock:
                    state["active"] -= 1
                    state["ok"] += n_ok
                    state["fail"] += len(local_failed)
                    state["done"] += len(chunk)
                    state["bytes"] += local_bytes
                    failed_paths.extend(local_failed)
                    if on_progress:
                        on_progress({
                            "done": state["done"],
                            "total": total,
                            "active": state["active"],
                            "total_threads": nworkers,
                            "ok": state["ok"],
                            "fail": state["fail"],
                            "bytes": state["bytes"],
                        })
        finally:
            _couninit()

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(nworkers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return state["ok"], state["fail"], failed_paths


# ---------------------------------------------------------------------------
# 文件系统扫描
# ---------------------------------------------------------------------------
SKIP_DIR_NAMES = {
    "$RECYCLE.BIN",
    "SYSTEM VOLUME INFORMATION",
    "PERFLOGS",
    "RECOVERY",
    "CONFIG.MSI",
    "$WINDOWS.~BT",
    "$WINDOWS.~WS",
    "WINDOWS.OLD",
}

SKIP_FILE_NAMES = {"PAGEFILE.SYS", "HIBERFIL.SYS", "SWAPFILE.SYS"}


def should_skip_dir(path):
    name = os.path.basename(path).upper()
    if name in SKIP_DIR_NAMES:
        return True
    if name == "WINDOWS":
        return True
    return False


def scan_tree(root, skip_system=True, on_error=None):
    """递归遍历目录树，yield (dirpath, [subdirs], [(filepath, size)])。
    跳过符号链接/联接点以避免死循环，忽略无权限的目录。"""
    root = os.path.abspath(root)

    def rec(path):
        try:
            with os.scandir(path) as it:
                entries = list(it)
        except OSError as e:
            if on_error:
                on_error(path, e)
            return
        dirs, files = [], []
        for e in entries:
            try:
                if e.is_symlink():
                    continue
                if hasattr(e, "is_junction") and e.is_junction():
                    continue
                st = e.stat(follow_symlinks=False)
            except OSError:
                continue
            if stat.S_ISDIR(st.st_mode):
                if skip_system and should_skip_dir(e.path):
                    continue
                dirs.append(e.path)
            elif stat.S_ISREG(st.st_mode):
                if os.path.basename(e.path).upper() in SKIP_FILE_NAMES:
                    continue
                files.append((e.path, st.st_size))
        yield path, dirs, files
        for d in dirs:
            for item in rec(d):
                yield item

    for item in rec(root):
        yield item


def path_size(path):
    """返回 (总字节, 文件数)。"""
    try:
        if os.path.isfile(path):
            return os.path.getsize(path), 1
        if not os.path.isdir(path):
            return 0, 0
    except OSError:
        return 0, 0
    total, cnt = 0, 0
    for _p, _d, fl in scan_tree(path, skip_system=False):
        for _f, s in fl:
            total += s
            cnt += 1
    return total, cnt


def scan_large_files(root, min_size, on_progress=None, cancel_event=None, skip_system=True):
    """扫描大文件，返回 (file_records, 一级文件夹占用排行)。"""
    files = []
    dir_sizes = {}
    count = 0
    for path, _dirs, flist in scan_tree(root, skip_system=skip_system):
        for f, size in flist:
            if size >= min_size:
                files.append({"path": f, "size": size})
            rel = os.path.relpath(f, root)
            if rel == ".":
                continue
            top = rel.split(os.sep)[0]
            dir_sizes[top] = dir_sizes.get(top, 0) + size
            count += 1
            if on_progress and count % 50 == 0:
                on_progress(count)
            if cancel_event and cancel_event.is_set():
                files.sort(key=lambda x: x["size"], reverse=True)
                return files, dir_sizes
    files.sort(key=lambda x: x["size"], reverse=True)
    return files, dir_sizes


def partial_hash(path, chunk=64 * 1024):
    """快速哈希：文件大小 + 首尾各 64KB。"""
    try:
        size = os.path.getsize(path)
    except OSError:
        return None
    h = hashlib.sha256()
    h.update(b"size:%d" % size)
    try:
        with open(path, "rb") as f:
            h.update(f.read(chunk))
            if size > chunk:
                f.seek(-chunk, os.SEEK_END)
                h.update(f.read(chunk))
    except OSError:
        return None
    return h.hexdigest()


def full_hash(path, chunk=1024 * 1024):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                data = f.read(chunk)
                if not data:
                    break
                h.update(data)
    except OSError:
        return None
    return h.hexdigest()


def scan_duplicates(root, on_progress=None, cancel_event=None, skip_system=True):
    """检测重复文件，返回分组列表 [{size, files:[path]}]。"""
    by_size = {}
    count = 0
    for _path, _dirs, flist in scan_tree(root, skip_system=skip_system):
        for f, size in flist:
            if size == 0:
                continue
            by_size.setdefault(size, []).append(f)
            count += 1
            if on_progress and count % 100 == 0:
                on_progress(count)
            if cancel_event and cancel_event.is_set():
                return []
    groups = []
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        buckets = {}
        for p in paths:
            h = partial_hash(p)
            if h is None:
                continue
            buckets.setdefault(h, []).append(p)
        for _h, cands in buckets.items():
            if len(cands) < 2:
                continue
            fulls = {}
            for p in cands:
                fh = full_hash(p)
                if fh is None:
                    continue
                fulls.setdefault(fh, []).append(p)
            for _fh, group in fulls.items():
                if len(group) >= 2:
                    groups.append({"size": size, "files": group})
    return groups


def scan_empty_dirs(root, skip_system=True, on_progress=None, cancel_event=None):
    """扫描空目录树，返回 [(目录路径, 该空树包含的目录数)]。
    一个目录视为"空树"：不含任何文件，且所有子目录递归为空树。
    只返回每棵空树最顶层的一个目录，删除它即可连带移除其下所有空子目录。"""
    info = {}
    count = 0
    for path, dirs, files in scan_tree(root, skip_system=skip_system):
        info[path] = (len(files), dirs)
        count += 1
        if on_progress and count % 500 == 0:
            on_progress(count)
        if cancel_event and cancel_event.is_set():
            return []

    fully = {}

    def is_fully_empty(p):
        if p in fully:
            return fully[p]
        nf, children = info[p]
        if nf > 0:
            fully[p] = False
            return False
        ok = True
        for c in children:
            if c not in info or not is_fully_empty(c):
                ok = False
                break
        fully[p] = ok
        return ok

    for p in list(info):
        is_fully_empty(p)

    topcount = {}
    for p in info:
        if not fully[p]:
            continue
        key = p
        anc = os.path.dirname(p)
        while anc in fully and fully[anc]:
            key = anc
            anc = os.path.dirname(anc)
        topcount[key] = topcount.get(key, 0) + 1

    items = sorted(topcount.items(), key=lambda kv: kv[1], reverse=True)
    return items


# ---------------------------------------------------------------------------
# 临时文件/缓存类别
# ---------------------------------------------------------------------------
def build_temp_categories():
    local = os.environ.get("LOCALAPPDATA", "")
    temp = os.environ.get("TEMP", "")
    win = os.environ.get("SystemRoot", r"C:\Windows")
    recycle = os.environ.get("SystemDrive", "C:") + r"\$Recycle.Bin"

    def C(pat):
        return os.path.expandvars(pat)

    cats = [
        {
            "name": "用户临时文件 (TEMP)",
            "paths": [p for p in (temp, os.path.join(local, "Temp")) if p],
            "note": "程序运行时产生的临时文件，可安全清理",
        },
        {
            "name": "系统临时文件",
            "paths": [C(r"%SystemRoot%\Temp")],
            "note": "需要管理员权限，普通用户下可能为空",
        },
        {
            "name": "Windows 更新缓存",
            "paths": [C(r"%SystemRoot%\SoftwareDistribution\Download")],
            "note": "已安装更新的下载缓存，清理不影响系统更新",
        },
        {
            "name": "Windows 传递优化缓存",
            "paths": [
                C(r"%SystemRoot%\SoftwareDistribution\DeliveryOptimization"),
                C(r"%LOCALAPPDATA%\Microsoft\Windows\DeliveryOptimization"),
            ],
            "note": "系统更新的对等分发缓存",
        },
        {
            "name": "Windows.old (旧版系统)",
            "paths": [C(r"%SystemRoot%.old")],
            "note": "升级系统留下的旧文件，占用极大，删除不可恢复，请谨慎",
        },
        {
            "name": "pip 缓存",
            "paths": [C(r"%LOCALAPPDATA%\pip\cache")],
            "note": "pip 下载的安装包缓存，可安全清理",
        },
        {
            "name": "npm 缓存",
            "paths": [C(r"%LOCALAPPDATA%\npm-cache")],
            "note": "npm 包缓存，可安全清理",
        },
        {
            "name": "Chrome 浏览器缓存",
            "paths": [
                C(r"%LOCALAPPDATA%\Google\Chrome\User Data\*\Cache"),
                C(r"%LOCALAPPDATA%\Google\Chrome\User Data\*\Code Cache"),
                C(r"%LOCALAPPDATA%\Google\Chrome\User Data\*\GPUCache"),
                C(r"%LOCALAPPDATA%\Google\Chrome\User Data\*\Service Worker\CacheStorage"),
            ],
            "note": "清理前请关闭 Chrome",
        },
        {
            "name": "Edge 浏览器缓存",
            "paths": [
                C(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\*\Cache"),
                C(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\*\Code Cache"),
                C(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\*\GPUCache"),
                C(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\*\Service Worker\CacheStorage"),
            ],
            "note": "清理前请关闭 Edge",
        },
        {
            "name": "Firefox 浏览器缓存",
            "paths": [C(r"%LOCALAPPDATA%\Mozilla\Firefox\Profiles\*\cache2")],
            "note": "清理前请关闭 Firefox",
        },
        {
            "name": "缩略图缓存",
            "paths": [
                C(r"%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*.db"),
                C(r"%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache_*.db"),
            ],
            "note": "资源管理器自动重建，可安全清理",
        },
        {
            "name": "错误报告 / 崩溃转储",
            "paths": [
                C(r"%LOCALAPPDATA%\CrashDumps"),
                C(r"%LOCALAPPDATA%\Microsoft\Windows\WER"),
            ],
            "note": "程序崩溃报告，可安全清理",
        },
        {
            "name": "JetBrains IDE 缓存",
            "paths": [
                C(r"%LOCALAPPDATA%\JetBrains\*\caches"),
                C(r"%LOCALAPPDATA%\JetBrains\*\log"),
                C(r"%LOCALAPPDATA%\JetBrains\*\tmp"),
            ],
            "note": "IntelliJ/PyCharm 等 IDE 的索引与日志缓存，常达数 GB",
        },
        {
            "name": "微信缓存",
            "paths": [
                C(r"%USERPROFILE%\Documents\WeChat Files\*\FileStorage\Cache"),
                C(r"%USERPROFILE%\Documents\WeChat Files\*\FileStorage\Temp"),
                C(r"%USERPROFILE%\Documents\WeChat Files\*\FileStorage\Thumb"),
            ],
            "note": "仅缓存/临时目录，不删除聊天记录；请先退出微信",
        },
        {
            "name": "QQ 缓存",
            "paths": [
                C(r"%USERPROFILE%\Documents\Tencent Files\*\Image"),
                C(r"%USERPROFILE%\Documents\Tencent Files\*\FileRecv"),
            ],
            "note": "图片与接收文件缓存；请先退出 QQ",
        },
        {
            "name": "网易云音乐缓存",
            "paths": [
                C(r"%APPDATA%\NetEase\CloudMusic\Cache"),
                C(r"%APPDATA%\NetEase\CloudMusic\Temp"),
            ],
            "note": "在线播放缓存，可安全清理",
        },
        {
            "name": "Steam 缓存",
            "paths": [
                C(r"%ProgramFiles(x86)%\Steam\appcache"),
                C(r"%ProgramFiles(x86)%\Steam\depotcache"),
                C(r"%ProgramFiles(x86)%\Steam\logs"),
            ],
            "note": "Steam 客户端缓存与日志，可安全清理",
        },
        {
            "name": "NVIDIA 着色器缓存",
            "paths": [
                C(r"%LOCALAPPDATA%\NVIDIA\DXCache"),
                C(r"%LOCALAPPDATA%\NVIDIA\GLCache"),
                C(r"%LOCALAPPDATA%\NVIDIA\ComputeCache"),
            ],
            "note": "显卡编译缓存，会自动重建；游戏可能短暂卡顿",
        },
        {
            "name": "D3D 着色器缓存",
            "paths": [C(r"%LOCALAPPDATA%\D3DSCache")],
            "note": "DirectX 着色器缓存，可安全清理",
        },
        {
            "name": "pnpm 缓存",
            "paths": [C(r"%LOCALAPPDATA%\pnpm\store")],
            "note": "pnpm 包存储缓存，可安全清理",
        },
        {
            "name": "yarn 缓存",
            "paths": [C(r"%LOCALAPPDATA%\Yarn\Cache")],
            "note": "yarn 包缓存，可安全清理",
        },
        {
            "name": "Unity 缓存",
            "paths": [C(r"%LOCALAPPDATA%\Unity\cache")],
            "note": "Unity 导入缓存，可安全清理",
        },
        {
            "name": "回收站",
            "paths": [recycle],
            "note": "清空回收站，不可恢复！",
            "empty_recycle": True,
        },
    ]
    return cats


# ---------------------------------------------------------------------------
# 注册表软件残留
# ---------------------------------------------------------------------------
UNINSTALL_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"


def _extract_exe_path(cmd):
    cmd = cmd.strip()
    m = re.match(r'"?(?P<path>[A-Za-z]:[^"]*?\.exe)"?', cmd, re.IGNORECASE)
    if m:
        p = m.group("path").strip()
        if p:
            return p
    m = re.search(r'(?P<path>[A-Za-z]:[^"\s]+\.exe)', cmd, re.IGNORECASE)
    if m:
        return m.group("path")
    return None


def _get_entries(key):
    entries = {}
    for name in ("DisplayName", "DisplayVersion", "Publisher", "InstallLocation",
                 "InstallDate", "DisplayIcon", "UninstallString", "QuietUninstallString"):
        try:
            entries[name] = winreg.QueryValueEx(key, name)[0] or ""
        except OSError:
            entries[name] = ""
    return entries


def _iter_uninstall():
    """遍历注册表所有卸载项（HKLM 64/32 位 + HKCU）。
    yield (hkey_name, full_sub_path, entries, sub_name)。"""
    VIEW_32 = winreg.KEY_WOW64_32KEY
    VIEW_64 = winreg.KEY_WOW64_64KEY
    WOW64_PREFIX = r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    for root, view, prefix in (
        (winreg.HKEY_LOCAL_MACHINE, VIEW_64, None),
        (winreg.HKEY_LOCAL_MACHINE, VIEW_32, WOW64_PREFIX),
        (winreg.HKEY_CURRENT_USER, 0, None),
    ):
        try:
            k = winreg.OpenKey(root, UNINSTALL_KEY, 0, winreg.KEY_READ | view)
        except OSError:
            continue
        try:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(k, i)
                    i += 1
                except OSError:
                    break
                try:
                    with winreg.OpenKey(k, sub) as sk:
                        entries = _get_entries(sk)
                except OSError:
                    continue
                hkey_name = "HKLM" if root == winreg.HKEY_LOCAL_MACHINE else "HKCU"
                full_sub = (prefix + "\\" + sub) if prefix else (UNINSTALL_KEY + "\\" + sub)
                yield hkey_name, full_sub, entries, sub
        finally:
            k.Close()


def _looks_like_update(name):
    n = (name or "").lower().strip()
    if "${{" in n or "{{" in n:
        return True
    if re.match(r'^kb\d+', n):
        return True
    for prefix in ("update for", "security update for", "hotfix for", "service pack", "update for windows"):
        if n.startswith(prefix):
            return True
    if "windows update" in n:
        return True
    return False


def _enum_installed_apps():
    """枚举已安装的桌面软件。返回记录列表。"""
    apps = []
    seen = set()
    for hkey_name, full_sub, entries, sub in _iter_uninstall():
        name = entries.get("DisplayName") or sub
        if _looks_like_update(name):
            continue
        uninst = entries.get("UninstallString") or entries.get("QuietUninstallString")
        install = entries.get("InstallLocation")
        if not uninst and not install:
            continue
        if full_sub in seen:
            continue
        seen.add(full_sub)
        apps.append({
            "name": name,
            "version": entries.get("DisplayVersion") or "",
            "publisher": entries.get("Publisher") or "",
            "install_location": install or "",
            "install_date": entries.get("InstallDate") or "",
            "uninstall": entries.get("UninstallString") or "",
            "quiet_uninstall": entries.get("QuietUninstallString") or "",
            "regkey": (hkey_name, full_sub),
            "msi_code": _extract_msi_code(entries.get("UninstallString") or ""),
        })
    apps.sort(key=lambda a: a["name"].lower())
    return apps


def _extract_msi_code(cmd):
    if not cmd:
        return None
    m = re.search(r'\{([0-9A-Fa-f-]{36})\}', cmd)
    if m and re.search(r'msi', cmd, re.IGNORECASE):
        return m.group(1)
    return None


def _reg_key_exists(hkey_name, full_sub):
    root = winreg.HKEY_LOCAL_MACHINE if hkey_name == "HKLM" else winreg.HKEY_CURRENT_USER
    try:
        winreg.OpenKey(root, full_sub, 0, winreg.KEY_READ)
        return True
    except OSError:
        return False


def launch_uninstaller(record):
    """启动官方卸载程序（管理员权限，触发 UAC）。返回 (ok, message)。"""
    cmd = record.get("uninstall") or record.get("quiet_uninstall")
    if not cmd:
        return False, "该软件没有卸载命令，请使用系统「设置 → 应用」卸载。"
    msi = record.get("msi_code")
    if msi:
        exe, args, wd = r"C:\Windows\System32\msiexec.exe", "/x {%s}" % msi, None
    else:
        exe = _extract_exe_path(cmd)
        if not exe or not os.path.exists(exe):
            return False, "无法定位卸载程序: %s" % cmd
        rest = cmd
        m = re.match(r'"?%s"?\s*(.*)$' % re.escape(exe), cmd, re.IGNORECASE)
        args = m.group(1).strip() if m else ""
        wd = os.path.dirname(exe)
    try:
        r = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, args, wd, 1)
        if r <= 32:
            r2 = ctypes.windll.shell32.ShellExecuteW(None, "open", exe, args, wd, 1)
            if r2 <= 32:
                return False, "无法启动卸载程序（错误码 %d）。" % r
        return True, "已启动官方卸载程序，请按向导完成。完成后点击「扫描残留」检查遗留文件。"
    except Exception as e:
        return False, "启动失败: %s" % e


def scan_leftovers(record):
    """卸载后残留检测。返回 (残留目录列表, 注册表项是否仍存在)。"""
    name = record.get("name") or ""
    leftovers = []
    dirs = []
    il = record.get("install_location")
    if il and os.path.isdir(il):
        dirs.append(il)
    for env in (r"%APPDATA%", r"%LOCALAPPDATA%", r"%ProgramData%", r"%USERPROFILE%\Documents"):
        base = os.path.expandvars(env)
        cand = os.path.join(base, name)
        if os.path.isdir(cand):
            dirs.append(cand)
    for d in dict.fromkeys(dirs):
        size, n = path_size(d)
        if n > 0:
            leftovers.append({"path": d, "size": size, "count": n})
    reg_exists = _reg_key_exists(record["regkey"][0], record["regkey"][1])
    return leftovers, reg_exists


def scan_software_remnants():
    """检测已卸载但残留注册表项的软件。返回记录列表。"""
    found = {}
    for hkey_name, full_sub, entries, sub in _iter_uninstall():
        name = entries.get("DisplayName") or sub
        candidates = _candidate_paths(entries)
        if not candidates:
            continue
        missing = [p for p in candidates if not os.path.exists(p)]
        if not missing:
            continue
        found[full_sub] = {
            "name": name,
            "missing": missing[0],
            "uninstall": (entries.get("UninstallString") or entries.get("QuietUninstallString") or ""),
            "regkey": (hkey_name, full_sub),
        }
    return list(found.values())


def _candidate_paths(entries):
    paths = []
    il = entries.get("InstallLocation", "")
    if il:
        paths.append(il)
    icon = entries.get("DisplayIcon", "")
    if icon:
        p = icon.split(",")[0].strip()
        if p:
            paths.append(p)
    us = entries.get("UninstallString", "") or entries.get("QuietUninstallString", "")
    if us:
        p = _extract_exe_path(us)
        if p:
            paths.append(p)
    cleaned = []
    for p in paths:
        p = os.path.expandvars(p).strip().strip('"').strip()
        if p and os.path.isabs(p):
            cleaned.append(p)
    return cleaned


def backup_and_delete_regkey(hkey_name, sub):
    """先导出 .reg 备份，再删除注册表项。返回 (ok, message)。"""
    backup_dir = os.path.join(app_dir(), "reg_backups")
    try:
        os.makedirs(backup_dir, exist_ok=True)
        stamp = time_str()
        backup_file = os.path.join(backup_dir, "%s_%s.reg" % (sub.replace("\\", "_")[:60], stamp))
    except OSError:
        backup_file = ""
    try:
        if backup_file:
            subprocess.run(
                ["reg", "export", "%s\\%s" % (hkey_name, sub), backup_file, "/y"],
                capture_output=True, creationflags=0x08000000, timeout=60,
            )
        r = subprocess.run(
            ["reg", "delete", "%s\\%s" % (hkey_name, sub), "/f"],
            capture_output=True, creationflags=0x08000000, timeout=60,
        )
        if r.returncode != 0:
            return False, "reg delete 失败: %s" % (r.stderr.decode("gbk", "ignore").strip() or r.stdout.decode("gbk", "ignore").strip())
        return True, "已删除，备份在 %s" % backup_file if backup_file else "已删除（无备份）"
    except Exception as e:
        return False, "删除失败: %s" % e


def time_str():
    import time
    return time.strftime("%Y%m%d_%H%M%S")


# ---------------------------------------------------------------------------
# 后台任务基类
# ---------------------------------------------------------------------------
class ScanTab(ttk.Frame):
    KEEP_ONE = False

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._q = None
        self._busy = False
        self._delete_mode = False
        self.cancel_event = threading.Event()
        self.records = []
        self.checked = set()
        self._by_iid = {}
        self._build_ui()

    # ---- UI ----
    def _columns(self):
        raise NotImplementedError

    def _build_ui(self):
        cols = self._columns()
        self._col_ids = [c[0] for c in cols]
        self._col_titles = [c[1] for c in cols]

        top = ttk.Frame(self)
        top.pack(fill="x", padx=6, pady=(6, 2))
        self._build_controls(top)

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=6, pady=2)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("chk",) + tuple(self._col_ids),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
        )
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.tree.heading("chk", text="√")
        self.tree.column("chk", width=40, anchor="center", stretch=False)
        for cid, title, width in cols:
            self.tree.heading(cid, text=title)
            anchor = "e" if cid in ("size", "cnt") else "w"
            self.tree.column(cid, width=width, anchor=anchor)
        self.tree.tag_configure("miss", background="#ffe2e2")
        self.tree.tag_configure("band0", background="#f4f4f4")
        self.tree.tag_configure("band1", background="#ffffff")
        self.tree.bind("<Button-1>", self._on_tree_click)

        self.info_var = tk.StringVar(value="")
        info = ttk.Label(self, textvariable=self.info_var, anchor="w")
        info.pack(fill="x", padx=6)

        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=6, pady=(2, 4))

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=6, pady=(2, 6))
        ttk.Button(bottom, text="全选", width=10, command=self._select_all).pack(side="left", padx=2)
        ttk.Button(bottom, text="取消全选", width=10, command=self._select_none).pack(side="left", padx=2)
        if self.KEEP_ONE:
            ttk.Button(bottom, text="每组保留一个，删除其余", command=self._keep_one_delete).pack(side="left", padx=2)
        ttk.Button(bottom, text="删除选中", width=12, command=self._delete_selected).pack(side="right", padx=2)

    def _build_controls(self, parent):
        self.scan_btn = ttk.Button(parent, text="开始扫描", command=self._start_scan)
        self.scan_btn.pack(side="left", padx=(0, 6))
        self.cancel_btn = ttk.Button(parent, text="取消", command=self.cancel_event.set, state=tk.DISABLED)
        self.cancel_btn.pack(side="left", padx=(0, 6))

    # ---- 扫描流程 ----
    def _start_scan(self):
        if self._busy:
            return
        self._busy = True
        self._delete_mode = False
        self.cancel_event.clear()
        self.scan_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)
        self._q = queue.Queue()
        self.app.set_status("正在扫描……")

        def run():
            try:
                result = self._scan_worker(self._q)
                self._q.put(("done", result))
            except Exception:
                self._q.put(("error", traceback.format_exc()))

        threading.Thread(target=run, daemon=True).start()
        self._poll()

    def _scan_worker(self, q):
        raise NotImplementedError

    def _poll(self):
        try:
            while True:
                msg = self._q.get_nowait()
                kind = msg[0]
                if kind == "progress":
                    self._on_progress(msg[1])
                elif kind == "log":
                    self.app.set_status(msg[1])
                elif kind == "del_progress":
                    info = msg[1]
                    self.progress.configure(maximum=max(info.get("total", 1), 1), value=info.get("done", 0))
                    elapsed = time.time() - getattr(self, "_del_start", time.time())
                    self.info_var.set(format_delete_progress(info, elapsed))
                elif kind == "done":
                    if self._delete_mode:
                        self._delete_finish(msg[1])
                    else:
                        self._finish(msg[1])
                    return
                elif kind == "error":
                    if self._delete_mode:
                        self._delete_error(msg[1])
                    else:
                        self._finish_error(msg[1])
                    return
        except queue.Empty:
            pass
        if self._busy:
            self.after(120, self._poll)

    def _finish(self, result):
        self._busy = False
        self.progress.stop()
        self.scan_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.populate(result)
        self.app.set_status("扫描完成")

    def _finish_error(self, err):
        self._busy = False
        self.progress.stop()
        self.scan_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.app.set_status("扫描出错")
        messagebox.showerror("扫描出错", err)

    def _on_progress(self, payload):
        self.info_var.set("已处理 %s 项……" % payload)

    def populate(self, result):
        raise NotImplementedError

    def _populate_records(self, records, band_groups=False):
        self.records = records
        self.checked.clear()
        self._by_iid.clear()
        self.tree.delete(*self.tree.get_children())
        for idx, rec in enumerate(records):
            iid = str(idx)
            self._by_iid[iid] = rec
            tag = ""
            if band_groups and rec.get("group") is not None:
                tag = "band%d" % (rec["group"] % 2)
            if rec.get("miss"):
                tag = "miss"
            self.tree.insert("", "end", iid=iid, values=("☐",) + tuple(rec["cells"]), tags=(tag,))
        self.info_var.set("共 %d 项" % len(records))

    # ---- 勾选 ----
    def _on_tree_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        self._toggle(iid)

    def _toggle(self, iid):
        if iid not in self._by_iid:
            return
        if iid in self.checked:
            self.checked.discard(iid)
            self.tree.set(iid, "chk", "☐")
        else:
            self.checked.add(iid)
            self.tree.set(iid, "chk", "☑")

    def _select_all(self):
        for iid in self._by_iid:
            self.checked.add(iid)
            self.tree.set(iid, "chk", "☑")

    def _select_none(self):
        for iid in list(self.checked):
            self.tree.set(iid, "chk", "☐")
        self.checked.clear()

    def _selected_records(self):
        return [self._by_iid[i] for i in self.checked if i in self._by_iid]

    def _selected_total_size(self):
        return sum(r.get("size") or 0 for r in self._selected_records())

    # ---- 删除 ----
    def _delete_selected(self):
        recs = self._selected_records()
        if not recs:
            messagebox.showinfo("提示", "请先勾选要清理的项目。")
            return
        paths = []
        for r in recs:
            for p in r.get("paths", []):
                if os.path.exists(p):
                    paths.append(p)
        paths = list(dict.fromkeys(paths))
        specials = {r.get("special") for r in recs if r.get("special")}
        regkeys = [r["regkey"] for r in recs if r.get("regkey")]
        total = self._selected_total_size()

        lines = ["将删除 %d 个文件/目录，共 %s" % (len(paths), human_size(total))]
        if "recycle" in specials:
            lines.append("注意：清空回收站不可恢复！")
        if regkeys:
            lines.append("将删除 %d 个失效的注册表项（会先导出 .reg 备份）" % len(regkeys))
        lines.append("删除的内容会进入回收站，可恢复。")
        if not messagebox.askokcancel("确认删除", "\n".join(lines)):
            return
        sizes = build_sizes_for_paths(paths, recs)
        self._start_delete(paths, specials, regkeys, sizes)

    def _start_delete(self, paths, specials, regkeys, sizes=None):
        """后台线程分批删除到回收站，界面不卡顿，进度条显示进度。"""
        self._busy = True
        self._delete_mode = True
        self._del_start = time.time()
        self.scan_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.DISABLED)
        self.progress.configure(mode="determinate", maximum=max(len(paths), 1), value=0)
        self._q = queue.Queue()
        self.app.set_status("正在删除……")

        def work():
            try:
                fail = 0
                failed = []
                if paths:
                    _ok, fail, failed = delete_to_recycle_bin(
                        paths,
                        on_progress=lambda info: self._q.put(("del_progress", info)),
                        cancel_event=self.cancel_event,
                        sizes=sizes,
                    )
                msgs = []
                if "recycle" in specials:
                    if not empty_recycle_bin():
                        fail += 1
                        failed.append("回收站")
                for hk, sub in regkeys:
                    r_ok, msg = backup_and_delete_regkey(hk, sub)
                    if not r_ok:
                        fail += 1
                        failed.append(sub[:60])
                    msgs.append("%s -> %s" % (sub[:40], msg))
                self._q.put(("done", (fail, failed, msgs)))
            except Exception:
                self._q.put(("error", traceback.format_exc()))

        threading.Thread(target=work, daemon=True).start()
        self._poll()

    def _delete_finish(self, result):
        failures, failed, msgs = result
        self._busy = False
        self._delete_mode = False
        self.progress.stop()
        self.progress.configure(mode="indeterminate")
        self.scan_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        if failures:
            lines = ["有 %d 项未能删除（可能被占用或权限不足）：" % failures]
            lines += ["- " + f for f in failed[:20]]
            if len(failed) > 20:
                lines.append("…共 %d 项" % len(failed))
            messagebox.showwarning("完成", "\n".join(lines))
        else:
            messagebox.showinfo("完成", "清理完成！%s" % ("\n".join(msgs) if msgs else ""))
        self.app.set_status("清理完成")
        self._start_scan()

    def _delete_error(self, err):
        self._busy = False
        self._delete_mode = False
        self.progress.stop()
        self.progress.configure(mode="indeterminate")
        self.scan_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.app.set_status("删除出错")
        messagebox.showerror("删除出错", err)
        self._start_scan()

    def _keep_one_delete(self):
        pass


# ---------------------------------------------------------------------------
# 标签页 1：临时文件/缓存
# ---------------------------------------------------------------------------
class TempTab(ScanTab):
    def _columns(self):
        return [
            ("cat", "清理类别", 240),
            ("cnt", "项目数", 100),
            ("size", "占用空间", 120),
            ("note", "说明", 320),
        ]

    def _scan_worker(self, q):
        cats = build_temp_categories()
        records = []
        for c in cats:
            q.put(("log", "正在统计：%s" % c["name"]))
            total, cnt = 0, 0
            matched_all = []
            for p in c["paths"]:
                matched = self._expand(p)
                matched_all.extend(matched)
                for m in matched:
                    s, n = path_size(m)
                    total += s
                    cnt += n
            # 回收站由 empty_recycle_bin 单独处理，不放进普通删除列表
            if c.get("empty_recycle"):
                matched_all = []
            records.append({
                "paths": matched_all,
                "size": total,
                "cells": [c["name"], str(cnt), human_size(total), c.get("note", "")],
                "special": "recycle" if c.get("empty_recycle") else None,
            })
        return records

    def _expand(self, pattern):
        pattern = os.path.expandvars(pattern)
        if any(ch in pattern for ch in "*?"):
            return [m for m in glob.glob(pattern, recursive=False)]
        return [pattern] if os.path.exists(pattern) else []

    def populate(self, result):
        self._populate_records(result)
        total = sum(r["size"] for r in result)
        self.info_var.set("共 %d 类，可清理约 %s" % (len(result), human_size(total)))

    def _delete_selected(self):
        # 类别之间可能路径重叠，先合并
        recs = self._selected_records()
        if not recs:
            messagebox.showinfo("提示", "请先勾选要清理的项目。")
            return
        paths = []
        specials = set()
        for r in recs:
            for p in r.get("paths", []):
                paths.append(p)
            if r.get("special"):
                specials.add(r["special"])
        # 只删除实际存在的（排除回收站本身，回收站由 empty_recycle_bin 清空）
        recycle_root = (os.environ.get("SystemDrive", "C:") + r"\$Recycle.Bin").lower()
        real = [p for p in dict.fromkeys(paths)
                if os.path.exists(p) and p.lower() != recycle_root]
        total = self._selected_total_size()
        if "recycle" in specials and not real:
            lines = ["将清空回收站。", "注意：清空回收站不可恢复！"]
        else:
            lines = ["将删除 %d 个文件/目录，共 %s" % (len(real), human_size(total))]
            if "recycle" in specials:
                lines.append("注意：清空回收站不可恢复！")
            lines.append("删除的内容会进入回收站，可恢复。")
        if not messagebox.askokcancel("确认删除", "\n".join(lines)):
            return
        sizes = build_sizes_for_paths(real, recs)
        self._start_delete(real, specials, [], sizes)


# ---------------------------------------------------------------------------
# 标签页 2：大文件扫描
# ---------------------------------------------------------------------------
class LargeTab(ScanTab):
    def _build_controls(self, parent):
        ttk.Label(parent, text="扫描位置:").pack(side="left")
        self.root_var = tk.StringVar(value="C:\\")
        ent = ttk.Entry(parent, textvariable=self.root_var, width=24)
        ent.pack(side="left", padx=(2, 6))
        ttk.Button(parent, text="…", width=3, command=self._browse).pack(side="left")
        ttk.Label(parent, text="  最小大小(MB):").pack(side="left")
        self.size_var = tk.StringVar(value="100")
        ttk.Spinbox(parent, from_=1, to=100000, textvariable=self.size_var, width=8).pack(side="left", padx=(2, 6))
        self.include_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(parent, text="包含系统目录(不推荐)", variable=self.include_var).pack(side="left")
        self.scan_btn = ttk.Button(parent, text="开始扫描", command=self._start_scan)
        self.scan_btn.pack(side="right", padx=2)
        self.cancel_btn = ttk.Button(parent, text="取消", command=self.cancel_event.set, state=tk.DISABLED)
        self.cancel_btn.pack(side="right", padx=2)

    def _browse(self):
        from tkinter import filedialog
        d = filedialog.askdirectory(title="选择要扫描的文件夹")
        if d:
            self.root_var.set(d)

    def _scan_worker(self, q):
        root = self.root_var.get().strip() or "C:\\"
        try:
            min_size = int(float(self.size_var.get()) * MB)
        except ValueError:
            min_size = 100 * MB
        files, dirs = scan_large_files(root, min_size,
                                       on_progress=lambda n: q.put(("progress", n)),
                                       cancel_event=self.cancel_event,
                                       skip_system=not self.include_var.get())
        records = [{"paths": [f["path"]], "size": f["size"], "cells": [f["path"], human_size(f["size"])]} for f in files]
        return {"records": records, "dirs": dirs}

    def populate(self, result):
        self._populate_records(result["records"])
        # 左侧一级文件夹排行
        self.tree2.delete(*self.tree2.get_children())
        dirs = sorted(result["dirs"].items(), key=lambda kv: kv[1], reverse=True)[:40]
        for name, size in dirs:
            self.tree2.insert("", "end", values=(name, human_size(size)))
        total = sum(r["size"] for r in result["records"])
        self.info_var.set("共 %d 个大文件，合计 %s（双击左侧可进入子文件夹扫描）" % (len(result["records"]), human_size(total)))

    def _build_ui(self):
        cols = self._columns()
        self._col_ids = [c[0] for c in cols]

        top = ttk.Frame(self)
        top.pack(fill="x", padx=6, pady=(6, 2))
        self._build_controls(top)

        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=6, pady=2)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=3)

        ttk.Label(left, text="一级文件夹占用排行(估算)", anchor="w").pack(fill="x", padx=2)
        lf = ttk.Frame(left)
        lf.pack(fill="both", expand=True)
        lvsb = ttk.Scrollbar(lf, orient="vertical")
        self.tree2 = ttk.Treeview(lf, columns=("dir", "size"), show="headings", yscrollcommand=lvsb.set)
        lvsb.config(command=self.tree2.yview)
        self.tree2.heading("dir", text="文件夹")
        self.tree2.heading("size", text="大小")
        self.tree2.column("dir", width=180)
        self.tree2.column("size", width=90, anchor="e")
        self.tree2.grid(row=0, column=0, sticky="nsew")
        lvsb.grid(row=0, column=1, sticky="ns")
        lf.rowconfigure(0, weight=1)
        lf.columnconfigure(0, weight=1)
        self.tree2.bind("<Double-1>", self._drill_in)

        # 右侧主列表
        ttk.Label(right, text="大文件列表（点击行勾选）", anchor="w").pack(fill="x", padx=2)
        rf = ttk.Frame(right)
        rf.pack(fill="both", expand=True)
        vsb = ttk.Scrollbar(rf, orient="vertical")
        hsb = ttk.Scrollbar(rf, orient="horizontal")
        self.tree = ttk.Treeview(rf, columns=("chk",) + tuple(self._col_ids), show="headings",
                                 yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        rf.rowconfigure(0, weight=1)
        rf.columnconfigure(0, weight=1)
        self.tree.heading("chk", text="√")
        self.tree.column("chk", width=40, anchor="center", stretch=False)
        for cid, title, width in self._columns():
            self.tree.heading(cid, text=title)
            self.tree.column(cid, width=width)
        self.tree.bind("<Button-1>", self._on_tree_click)

        self.info_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.info_var, anchor="w").pack(fill="x", padx=6)
        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=6, pady=(2, 4))

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=6, pady=(2, 6))
        ttk.Button(bottom, text="全选", width=10, command=self._select_all).pack(side="left", padx=2)
        ttk.Button(bottom, text="取消全选", width=10, command=self._select_none).pack(side="left", padx=2)
        ttk.Button(bottom, text="删除选中", width=12, command=self._delete_selected).pack(side="right", padx=2)

    def _drill_in(self, event):
        iid = self.tree2.identify_row(event.y)
        if not iid:
            return
        name = self.tree2.item(iid, "values")[0]
        root = self.root_var.get().strip() or "C:\\"
        new_root = os.path.join(root, name)
        if os.path.isdir(new_root):
            self.root_var.set(new_root)
            self._start_scan()

    def _on_progress(self, payload):
        self.info_var.set("已扫描 %s 个文件……（勾选“包含系统目录”会非常慢）" % payload)

    def _columns(self):
        return [
            ("path", "文件路径", 700),
            ("size", "大小", 120),
        ]


# ---------------------------------------------------------------------------
# 标签页 3：重复文件
# ---------------------------------------------------------------------------
class DupTab(ScanTab):
    KEEP_ONE = True

    def _build_controls(self, parent):
        ttk.Label(parent, text="扫描位置:").pack(side="left")
        self.root_var = tk.StringVar(value="C:\\")
        ent = ttk.Entry(parent, textvariable=self.root_var, width=24)
        ent.pack(side="left", padx=(2, 6))
        ttk.Button(parent, text="…", width=3, command=self._browse).pack(side="left")
        self.include_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(parent, text="包含系统目录(不推荐)", variable=self.include_var).pack(side="left")
        self.scan_btn = ttk.Button(parent, text="开始扫描", command=self._start_scan)
        self.scan_btn.pack(side="right", padx=2)
        self.cancel_btn = ttk.Button(parent, text="取消", command=self.cancel_event.set, state=tk.DISABLED)
        self.cancel_btn.pack(side="right", padx=2)

    def _browse(self):
        from tkinter import filedialog
        d = filedialog.askdirectory(title="选择要扫描的文件夹")
        if d:
            self.root_var.set(d)

    def _columns(self):
        return [
            ("gid", "组", 50),
            ("path", "文件路径", 560),
            ("size", "大小", 120),
        ]

    def _scan_worker(self, q):
        root = self.root_var.get().strip() or "C:\\"
        groups = scan_duplicates(root,
                                 on_progress=lambda n: q.put(("progress", n)),
                                 cancel_event=self.cancel_event,
                                 skip_system=not self.include_var.get())
        records = []
        for gi, g in enumerate(groups):
            for f in g["files"]:
                records.append({
                    "paths": [f],
                    "size": g["size"],
                    "cells": [str(gi + 1), f, human_size(g["size"])],
                    "group": gi,
                })
        return records

    def populate(self, result):
        self._populate_records(result, band_groups=True)
        total = sum(r["size"] for r in result)
        groups = {r["group"] for r in result}
        per_group = {}
        for r in result:
            entry = per_group.setdefault(r["group"], [0, 0])
            entry[0] += 1
            entry[1] = r["size"]
        reclaim = sum((cnt - 1) * size for cnt, size in per_group.values())
        self.info_var.set("共 %d 组重复文件 %d 个文件（合计 %s），若每组保留一个约可释放 %s" % (
            len(groups), len(result), human_size(total), human_size(reclaim)))

    def _keep_one_delete(self):
        if not self.records:
            messagebox.showinfo("提示", "请先扫描。")
            return
        groups = {}
        for iid, rec in self._by_iid.items():
            groups.setdefault(rec["group"], []).append((iid, rec))
        delete_paths = []
        kept = []
        for g, items in groups.items():
            # 保留路径最短的一个
            items.sort(key=lambda t: len(t[1]["paths"][0]))
            keep = items[0]
            kept.append(keep[1]["paths"][0])
            for iid, rec in items[1:]:
                delete_paths.append(rec["paths"][0])
        total = sum(os.path.getsize(p) for p in delete_paths if os.path.exists(p))
        if not delete_paths:
            messagebox.showinfo("提示", "没有可删除的重复文件。")
            return
        if not messagebox.askokcancel("确认删除",
                                      "将在每个重复组中保留一个，删除其余 %d 个文件，约 %s。\n"
                                      "删除的内容会进入回收站，可恢复。\n\n保留清单：\n%s" % (
                                          len(delete_paths), human_size(total), "\n".join(kept[:10]))):
            return
        sizes = [os.path.getsize(p) if os.path.exists(p) else 0 for p in delete_paths]
        self._start_delete(delete_paths, set(), [], sizes)


# ---------------------------------------------------------------------------
# 标签页 0：软件卸载
# ---------------------------------------------------------------------------
class UninstallTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._apps = []
        self._by_iid = {}
        self._residuals = []
        self._res_by_iid = {}
        self._res_checked = set()
        self._busy = False
        self._deleting = False
        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=6, pady=(6, 2))
        self.refresh_btn = ttk.Button(top, text="刷新已安装软件", command=self._refresh)
        self.refresh_btn.pack(side="left", padx=(0, 6))
        ttk.Label(top, text="点击选中一行软件，再使用下方按钮", anchor="w").pack(side="left", padx=8)

        upper = ttk.Frame(self)
        upper.pack(fill="both", expand=True, padx=6, pady=2)
        usb = ttk.Scrollbar(upper, orient="vertical")
        self.tree = ttk.Treeview(upper, columns=("name", "version", "publisher", "install", "date"),
                                 show="headings", yscrollcommand=usb.set)
        usb.config(command=self.tree.yview)
        self.tree.heading("name", text="软件名称")
        self.tree.heading("version", text="版本")
        self.tree.heading("publisher", text="发行商")
        self.tree.heading("install", text="安装路径")
        self.tree.heading("date", text="安装日期")
        self.tree.column("name", width=300, anchor="w")
        self.tree.column("version", width=90, anchor="center")
        self.tree.column("publisher", width=160, anchor="w")
        self.tree.column("install", width=280, anchor="w")
        self.tree.column("date", width=90, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        usb.grid(row=0, column=1, sticky="ns")
        upper.rowconfigure(0, weight=1)
        upper.columnconfigure(0, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=6, pady=2)
        ttk.Button(bar, text="卸载所选软件", width=18, command=self._uninstall_selected).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="扫描所选软件的残留", command=self._scan_residuals).pack(side="left", padx=(0, 6))
        self.info_var = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self.info_var, anchor="w").pack(side="left", padx=8)

        ttk.Label(self, text="卸载后残留（可勾选，删除到回收站）", anchor="w").pack(fill="x", padx=6)
        lower = ttk.Frame(self)
        lower.pack(fill="both", expand=True, padx=6, pady=2)
        lsb = ttk.Scrollbar(lower, orient="vertical")
        self.rtree = ttk.Treeview(lower, columns=("chk", "path", "size"),
                                  show="headings", yscrollcommand=lsb.set)
        lsb.config(command=self.rtree.yview)
        self.rtree.heading("chk", text="√")
        self.rtree.heading("path", text="残留路径")
        self.rtree.heading("size", text="大小")
        self.rtree.column("chk", width=40, anchor="center", stretch=False)
        self.rtree.column("path", width=600, anchor="w")
        self.rtree.column("size", width=120, anchor="e")
        self.rtree.grid(row=0, column=0, sticky="nsew")
        lsb.grid(row=0, column=1, sticky="ns")
        lower.rowconfigure(0, weight=1)
        lower.columnconfigure(0, weight=1)
        self.rtree.bind("<Button-1>", self._on_res_click)

        rbar = ttk.Frame(self)
        rbar.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(rbar, text="全选", width=8, command=self._res_all).pack(side="left", padx=2)
        ttk.Button(rbar, text="取消全选", width=8, command=self._res_none).pack(side="left", padx=2)
        ttk.Button(rbar, text="删除勾选的残留", width=16, command=self._delete_residuals).pack(side="right", padx=2)

        self.del_progress = ttk.Progressbar(self, mode="determinate", maximum=1, value=0)
        self.del_progress.pack(fill="x", padx=6, pady=(0, 6))

    def _refresh(self):
        if self._busy:
            return
        self._busy = True
        self.refresh_btn.config(state=tk.DISABLED)
        self.app.set_status("正在读取已安装软件……")
        threading.Thread(target=self._load_async, daemon=True).start()

    def _load_async(self):
        try:
            apps = _enum_installed_apps()
            self.after(0, lambda: self._finish_load(apps))
        except Exception:
            err = traceback.format_exc()
            self.after(0, lambda: self._fail_load(err))

    def _finish_load(self, apps):
        self._busy = False
        self.refresh_btn.config(state=tk.NORMAL)
        self._apps = apps
        self._by_iid.clear()
        self.tree.delete(*self.tree.get_children())
        for i, a in enumerate(apps):
            iid = str(i)
            self._by_iid[iid] = a
            self.tree.insert("", "end", iid=iid, values=(
                a["name"], a["version"], a["publisher"],
                a["install_location"] or "-", a["install_date"] or ""))
        self.info_var.set("共 %d 个已安装软件（卸载会启动官方卸载程序并请求管理员权限）" % len(apps))
        self.app.set_status("已安装软件读取完成")

    def _fail_load(self, err):
        self._busy = False
        self.refresh_btn.config(state=tk.NORMAL)
        messagebox.showerror("读取失败", err)

    def _selected_app(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self._by_iid.get(sel[0])

    def _on_select(self, _event):
        app = self._selected_app()
        if app:
            self.info_var.set("已选中：%s（卸载将启动官方卸载程序并请求管理员权限）" % app["name"])

    def _uninstall_selected(self):
        app = self._selected_app()
        if not app:
            messagebox.showinfo("提示", "请先在列表中选择一个软件。")
            return
        if not messagebox.askokcancel(
                "确认卸载",
                "将启动「%s」的官方卸载程序。\n\n"
                "此操作只负责启动卸载向导，不会自动删除任何文件；\n"
                "卸载程序可能请求管理员权限（UAC）。\n"
                "请按卸载向导操作，完成后可点击「扫描所选软件的残留」检查遗留文件。" % app["name"]):
            return
        ok, msg = launch_uninstaller(app)
        if not ok:
            messagebox.showerror("卸载失败", msg)
        else:
            self.info_var.set(msg)
            self.app.set_status(msg)

    def _scan_residuals(self):
        app = self._selected_app()
        if not app:
            messagebox.showinfo("提示", "请先在列表中选择一个软件。")
            return
        self.info_var.set("正在扫描「%s」的残留……" % app["name"])
        self.app.set_status("正在扫描残留……")

        def work():
            try:
                leftovers, reg_exists = scan_leftovers(app)
                self.after(0, lambda: self._finish_residuals(leftovers, reg_exists, app["name"]))
            except Exception:
                err = traceback.format_exc()
                self.after(0, lambda: self._fail_residuals(err))

        threading.Thread(target=work, daemon=True).start()

    def _finish_residuals(self, leftovers, reg_exists, name):
        self._residuals = leftovers
        self._res_by_iid.clear()
        self._res_checked.clear()
        self.rtree.delete(*self.rtree.get_children())
        for i, r in enumerate(leftovers):
            iid = str(i)
            self._res_by_iid[iid] = r
            self.rtree.insert("", "end", iid=iid, values=("☐", r["path"], human_size(r["size"])))
        total = sum(r["size"] for r in leftovers)
        state = "注册表项仍存在（可去「软件残留」页清理）" if reg_exists else "注册表项已清除"
        self.info_var.set("「%s」残留：%d 个目录，共 %s；%s" % (name, len(leftovers), human_size(total), state))
        self.app.set_status("残留扫描完成")

    def _fail_residuals(self, err):
        self.app.set_status("残留扫描出错")
        messagebox.showerror("扫描出错", err)

    def _on_res_click(self, event):
        iid = self.rtree.identify_row(event.y)
        if not iid or iid not in self._res_by_iid:
            return
        if iid in self._res_checked:
            self._res_checked.discard(iid)
            self.rtree.set(iid, "chk", "☐")
        else:
            self._res_checked.add(iid)
            self.rtree.set(iid, "chk", "☑")

    def _res_all(self):
        for iid in self._res_by_iid:
            self._res_checked.add(iid)
            self.rtree.set(iid, "chk", "☑")

    def _res_none(self):
        for iid in list(self._res_checked):
            self.rtree.set(iid, "chk", "☐")
        self._res_checked.clear()

    def _delete_residuals(self):
        if not self._res_checked:
            messagebox.showinfo("提示", "请先勾选要删除的残留目录。")
            return
        if self._deleting:
            return
        paths = []
        for iid in self._res_checked:
            r = self._res_by_iid[iid]
            if os.path.exists(r["path"]):
                paths.append(r["path"])
        total = sum(self._res_by_iid[i]["size"] for i in self._res_checked)
        if not paths:
            messagebox.showinfo("提示", "勾选的残留已不存在。")
            return
        if not messagebox.askokcancel(
                "确认删除",
                "将删除 %d 个残留目录，共 %s。\n删除的内容会进入回收站，可恢复。" % (len(paths), human_size(total))):
            return
        self._deleting = True
        self._del_start = time.time()
        self.del_progress.configure(mode="determinate", maximum=max(len(paths), 1), value=0)
        self.app.set_status("正在删除残留……")
        q = queue.Queue()
        self._del_q = q

        def work():
            try:
                sizes = []
                for iid in self._res_checked:
                    r = self._res_by_iid[iid]
                    sizes.append(r["size"] if os.path.exists(r["path"]) else 0)
                _ok, fail, failed = delete_to_recycle_bin(
                    paths,
                    on_progress=lambda info: q.put(("p", info)),
                    sizes=sizes)
                q.put(("done", fail, failed))
            except Exception:
                q.put(("error", traceback.format_exc()))

        threading.Thread(target=work, daemon=True).start()
        self._del_poll()

    def _del_poll(self):
        try:
            while True:
                msg = self._del_q.get_nowait()
                kind = msg[0]
                if kind == "p":
                    info = msg[1]
                    self.del_progress.configure(maximum=max(info.get("total", 1), 1), value=info.get("done", 0))
                    elapsed = time.time() - getattr(self, "_del_start", time.time())
                    self.info_var.set(format_delete_progress(info, elapsed))
                elif kind == "done":
                    fail, failed = msg[1], msg[2]
                    self._deleting = False
                    self.del_progress.configure(value=0)
                    if fail:
                        lines = ["有 %d 项未能删除（可能被占用或权限不足）：" % fail]
                        lines += ["- " + f for f in failed[:20]]
                        if len(failed) > 20:
                            lines.append("…共 %d 项" % len(failed))
                        messagebox.showwarning("完成", "\n".join(lines))
                    else:
                        messagebox.showinfo("完成", "残留已删除（回收站可恢复）。")
                    self._res_checked.clear()
                    self.app.set_status("残留删除完成")
                    self._refresh()
                    return
                elif kind == "error":
                    self._deleting = False
                    self.del_progress.configure(value=0)
                    self.app.set_status("删除出错")
                    messagebox.showerror("删除出错", msg[1])
                    return
        except queue.Empty:
            pass
        if self._deleting:
            self.after(120, self._del_poll)


# ---------------------------------------------------------------------------
# 标签页 4：空目录检测
# ---------------------------------------------------------------------------
class EmptyDirTab(ScanTab):
    def _build_controls(self, parent):
        ttk.Label(parent, text="扫描位置:").pack(side="left")
        self.root_var = tk.StringVar(value="C:\\")
        ent = ttk.Entry(parent, textvariable=self.root_var, width=24)
        ent.pack(side="left", padx=(2, 6))
        ttk.Button(parent, text="…", width=3, command=self._browse).pack(side="left")
        self.include_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(parent, text="包含系统目录(不推荐)", variable=self.include_var).pack(side="left")
        self.scan_btn = ttk.Button(parent, text="开始扫描", command=self._start_scan)
        self.scan_btn.pack(side="right", padx=2)
        self.cancel_btn = ttk.Button(parent, text="取消", command=self.cancel_event.set, state=tk.DISABLED)
        self.cancel_btn.pack(side="right", padx=2)

    def _browse(self):
        from tkinter import filedialog
        d = filedialog.askdirectory(title="选择要扫描的文件夹")
        if d:
            self.root_var.set(d)

    def _columns(self):
        return [
            ("path", "空目录路径", 720),
            ("nested", "含空子目录数", 140),
        ]

    def _scan_worker(self, q):
        root = self.root_var.get().strip() or "C:\\"
        items = scan_empty_dirs(root,
                                skip_system=not self.include_var.get(),
                                on_progress=lambda n: q.put(("progress", n)),
                                cancel_event=self.cancel_event)
        return items

    def populate(self, result):
        records = [{"paths": [p], "size": 0,
                    "cells": [p, "含 %d 个" % n]} for p, n in result]
        self._populate_records(records)
        self.info_var.set("共 %d 个空目录链（删除父目录会自动移除其下所有空子目录）" % len(records))


# ---------------------------------------------------------------------------
# 标签页 4：软件残留
# ---------------------------------------------------------------------------
class RemnantTab(ScanTab):
    def _columns(self):
        return [
            ("name", "软件名称", 240),
            ("path", "缺失的安装路径", 400),
            ("uninst", "卸载命令", 300),
        ]

    def _scan_worker(self, q):
        return scan_software_remnants()

    def populate(self, result):
        records = []
        for r in result:
            records.append({
                "regkey": r["regkey"],
                "size": 0,
                "miss": True,
                "cells": [r["name"], r["missing"], r["uninstall"]],
            })
        self._populate_records(records)
        self.info_var.set("发现 %d 个失效的软件残留（安装路径已不存在）。勾选后可清理对应注册表项，删除前会自动导出 .reg 备份。" % len(records))


# ---------------------------------------------------------------------------
# 主窗口
# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1150x700")
        self.minsize(960, 600)

        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass

        admin_bar = ttk.Frame(self)
        admin_bar.pack(fill="x", padx=8, pady=(6, 0))
        if is_admin():
            ttk.Label(admin_bar, text="✓ 当前以管理员身份运行", foreground="#1e7d32").pack(side="left")
        else:
            ttk.Label(admin_bar, text="未以管理员运行——系统缓存(Windows/更新缓存/回收站其他用户)可能无法扫描或删除。",
                      foreground="#b26a00").pack(side="left")
            ttk.Button(admin_bar, text="以管理员重新启动", command=self._relaunch_admin).pack(side="left", padx=8)

        self.status_var = tk.StringVar(value="就绪")
        self._status_label = ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w")
        self._status_label.pack(fill="x", side="bottom", padx=2, pady=2)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=4, pady=4)
        self.tabs = {}
        for key, cls, title in (
            ("uninstall", UninstallTab, "软件卸载"),
            ("temp", TempTab, "临时文件/缓存"),
            ("large", LargeTab, "大文件扫描"),
            ("dup", DupTab, "重复文件"),
            ("emptydir", EmptyDirTab, "空目录检测"),
            ("remnant", RemnantTab, "软件残留"),
        ):
            t = cls(nb, self)
            nb.add(t, text=title)
            self.tabs[key] = t

    def _relaunch_admin(self):
        exe = sys.executable
        args = [os.path.abspath(__file__)] if not getattr(sys, "frozen", False) else []
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, " ".join(args), None, 1)
        except Exception as e:
            messagebox.showerror("失败", "无法以管理员身份启动: %s" % e)

    def set_status(self, text):
        self.status_var.set(text)


def main():
    if "--selftest" in sys.argv:
        def close():
            app.destroy()
            print("GUI self-test OK")
        app = App()
        app.after(1500, close)
        app.mainloop()
        return
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

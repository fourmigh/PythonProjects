#!/usr/bin/env python3
"""支持多个端口的版本（Windows / Linux / macOS / WSL 通用）"""

import os
import re
import signal
import subprocess
import sys

IS_WINDOWS = sys.platform == "win32"


def run_command(args):
    """执行命令；命令不存在或无法执行时返回 None"""
    kwargs = {}
    if IS_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            **kwargs,
        )
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return None


def find_pids_windows(port):
    """通过 netstat 查找监听指定端口的进程"""
    result = run_command(["netstat", "-ano"])
    if result is None or result.returncode != 0:
        return []

    pids = set()
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[-2].upper() != "LISTENING":
            continue
        if parts[1].rsplit(":", 1)[-1] != str(port):
            continue
        try:
            pid = int(parts[-1])
        except ValueError:
            continue
        if pid > 0:
            pids.add(pid)
    return sorted(pids)


def find_pids_lsof(port):
    """通过 lsof 查找；返回 None 表示 lsof 不可用"""
    result = run_command(["lsof", "-ti", f":{port}"])
    if result is None:
        return None
    if result.returncode != 0:
        return []

    pids = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.isdigit() and int(line) > 0:
            pids.add(int(line))
    return sorted(pids)


def find_pids_ss(port):
    """通过 ss 查找；返回 None 表示 ss 不可用"""
    result = run_command(["ss", "-ltnpH", f"sport = :{port}"])
    if result is None or result.returncode != 0:
        return None

    pids = set()
    for match in re.finditer(r"pid=(\d+)", result.stdout):
        pid = int(match.group(1))
        if pid > 0:
            pids.add(pid)
    return sorted(pids)


def find_pids_proc(port):
    """通过 /proc 查找（lsof、ss 都不可用时的兜底）"""
    inodes = set()
    hex_port = f"{port:04X}"
    for path in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                next(handle, None)
                for line in handle:
                    parts = line.split()
                    if len(parts) < 10 or parts[3] != "0A":
                        continue
                    if parts[1].rsplit(":", 1)[-1].upper() != hex_port:
                        continue
                    inodes.add(parts[9])
        except OSError:
            continue

    if not inodes:
        return []

    targets = {f"socket:[{inode}]" for inode in inodes}
    pids = set()
    try:
        entries = os.listdir("/proc")
    except OSError:
        return []

    for entry in entries:
        if not entry.isdigit():
            continue
        fd_dir = f"/proc/{entry}/fd"
        try:
            fds = os.listdir(fd_dir)
        except OSError:
            continue
        for fd in fds:
            try:
                if os.readlink(f"{fd_dir}/{fd}") in targets:
                    pids.add(int(entry))
                    break
            except OSError:
                continue
    return sorted(pids)


def find_pids_unix(port):
    pids = find_pids_lsof(port)
    if pids:
        return pids
    if pids is None:
        pids = find_pids_ss(port)
        if pids:
            return pids
        if pids is None:
            return find_pids_proc(port)
    return pids


def find_pids(port):
    if IS_WINDOWS:
        return find_pids_windows(port)
    return find_pids_unix(port)


def kill_pid(pid):
    """结束进程，返回 (是否成功, 错误信息)"""
    if IS_WINDOWS:
        result = run_command(["taskkill", "/F", "/PID", str(pid)])
        if result is None:
            return False, "taskkill 不可用"
        if result.returncode == 0:
            return True, ""
        message = (result.stderr or result.stdout).strip()
        return False, message or f"taskkill 返回码 {result.returncode}"

    try:
        os.kill(pid, signal.SIGKILL)
        return True, ""
    except OSError as error:
        return False, str(error)


def find_and_kill_port(port):
    """查找并释放单个端口"""
    print(f"\n--- 检查端口 {port} ---")

    pids = find_pids(port)
    if not pids:
        print(f"端口 {port} 空闲")
        return True

    print(f"端口 {port} 被进程 {pids} 占用")
    all_ok = True
    for pid in pids:
        success, message = kill_pid(pid)
        if success:
            print(f"已结束进程 {pid}")
        else:
            all_ok = False
            print(f"结束进程 {pid} 失败: {message}")

    if all_ok:
        print(f"已释放端口 {port}")
    else:
        hint = "管理员" if IS_WINDOWS else "sudo"
        print(f"端口 {port} 未能完全释放，可能需要{hint}权限")
    return all_ok


if __name__ == "__main__":
    # 支持命令行参数传入多个端口
    if len(sys.argv) < 2:
        print("使用方法: python free_ports.py 端口1 端口2 ...")
        print("示例: python free_ports.py 3000 4200 8080")
        sys.exit(1)

    failed = False
    for port_str in sys.argv[1:]:
        try:
            port = int(port_str)
            if not find_and_kill_port(port):
                failed = True
        except ValueError:
            print(f"忽略无效端口: {port_str}")

    sys.exit(1 if failed else 0)

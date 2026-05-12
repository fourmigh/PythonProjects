#!/usr/bin/env python3
"""支持多个端口的版本"""

import subprocess
import sys

def find_and_kill_port(port):
    """查找并释放单个端口"""
    print(f"\n--- 检查端口 {port} ---")
    
    result = subprocess.run(["lsof", "-i", f":{port}"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"端口 {port} 空闲")
        return
    
    lines = result.stdout.strip().split("\n")
    if len(lines) < 2:
        print(f"端口 {port} 空闲")
        return
    
    pids = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 2:
            try:
                pid = int(parts[1])
                pids.append(pid)
            except ValueError:
                continue
    
    if pids:
        print(f"端口 {port} 被进程 {pids} 占用")
        for pid in pids:
            subprocess.run(["sudo", "kill", "-9", str(pid)])
        print(f"已释放端口 {port}")
    else:
        print(f"端口 {port} 空闲")

if __name__ == "__main__":
    # 支持命令行参数传入多个端口
    if len(sys.argv) < 2:
        print("使用方法: python3 free_ports.py 端口1 端口2 ...")
        print("示例: python3 free_ports.py 3000 4200 8080")
        sys.exit(1)
    
    for port_str in sys.argv[1:]:
        try:
            port = int(port_str)
            find_and_kill_port(port)
        except ValueError:
            print(f"忽略无效端口: {port_str}")
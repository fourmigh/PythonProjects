#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import os
import time
import json
import requests
import re
import unicodedata

# 导入模型列表
from model_list import VLM_MODELS

class OllamaManager:
    def __init__(self):
        self.ollama_cmd = "ollama"
        self.api_url = "http://localhost:11434"
    
    def run_cmd(self, cmd, capture_output=True, timeout=10):
        """执行命令并返回结果（带超时）"""
        try:
            if capture_output:
                process = subprocess.Popen(
                    cmd, 
                    shell=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True
                )
                
                try:
                    stdout, stderr = process.communicate(timeout=timeout)
                    return stdout.strip(), stderr.strip(), process.returncode
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                    return "", "命令执行超时", -1
            else:
                subprocess.Popen(cmd, shell=True)
                return "", "", 0
        except Exception as e:
            return "", str(e), -1
    
    def run_cmd_no_wait(self, cmd):
        """执行命令不等待结果"""
        try:
            subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except:
            return False
    
    def is_ollama_running(self):
        """检查 Ollama 服务是否运行"""
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def get_installed_models(self):
        """获取已安装的模型列表"""
        if not self.is_ollama_running():
            return {}
        
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                installed = {}
                for model in data.get('models', []):
                    name = model.get('name', '')
                    base_name = re.sub(r':.*$', '', name)
                    size_gb = model.get('size', 0) / (1024**3)
                    installed[base_name] = {
                        'full_name': name,
                        'size': f"{size_gb:.1f}GB"
                    }
                return installed
        except:
            pass
        return {}
    
    def get_running_models(self):
        """获取运行中的模型"""
        if not self.is_ollama_running():
            return []
        
        try:
            response = requests.get(f"{self.api_url}/api/ps", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = []
                for model in data.get('models', []):
                    name = model.get('name', '')
                    if name:
                        models.append(name)
                return models
        except:
            pass
        
        stdout, stderr, code = self.run_cmd(f"{self.ollama_cmd} ps", timeout=5)
        if code != 0 or not stdout:
            return []
        
        models = []
        lines = stdout.strip().split('\n')
        if len(lines) <= 1:
            return []
        
        for line in lines[1:]:
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    
    def start_service(self):
        """启动 Ollama 服务"""
        if self.is_ollama_running():
            print("[OK] Ollama 已经在运行中")
            return True

        print("[INFO] 正在启动 Ollama 服务...")
        if os.name == 'nt':
            self.run_cmd_no_wait(f"start /B {self.ollama_cmd} serve")
        else:
            self.run_cmd_no_wait(f"nohup {self.ollama_cmd} serve > /dev/null 2>&1 &")

        for i in range(10):
            time.sleep(1)
            if self.is_ollama_running():
                print("[OK] Ollama 服务已启动")
                return True

        print("[ERROR] 启动失败")
        return False
    
    def stop_service(self):
        """停止 Ollama 服务"""
        if not self.is_ollama_running():
            print("[INFO] Ollama 未运行")
            return True
        
        print("[INFO] 正在停止 Ollama...")
        try:
            import psutil
            for proc in psutil.process_iter(['name', 'pid']):
                if proc.info['name'] and 'ollama' in proc.info['name'].lower():
                    try:
                        proc.kill()
                    except:
                        pass
        except:
            if os.name == 'nt':
                os.system("taskkill /IM ollama.exe /F 2>nul")
            else:
                os.system("pkill -f ollama 2>/dev/null")
        
        time.sleep(2)
        
        if not self.is_ollama_running():
            print("[OK] Ollama 已停止")
            return True
        else:
            print("[ERROR] 停止失败")
            return False
    
    def pull_model(self, model_name):
        """下载模型"""
        if not self.is_ollama_running():
            print("[INFO] Ollama 服务未运行，正在启动...")
            self.start_service()
            time.sleep(2)
        
        print(f"\n[INFO] 正在下载模型: {model_name}")
        print("=" * 60)
        
        process = subprocess.Popen(f"{self.ollama_cmd} pull {model_name}", shell=True)
        process.wait()
        
        if process.returncode == 0:
            print("\n" + "=" * 60)
            print(f"[OK] 模型 {model_name} 下载完成")
            return True
        else:
            print(f"\n[ERROR] 下载失败，返回码: {process.returncode}")
            return False
    
    def run_model(self, model_name):
        """运行模型"""
        if not self.is_ollama_running():
            print("[INFO] Ollama 未运行，正在启动...")
            self.start_service()

        print(f"[INFO] 正在启动模型: {model_name}")
        if os.name == 'nt':
            subprocess.Popen(
                f'start "Ollama - {model_name}" cmd /k "echo 模型: {model_name} && echo. && {self.ollama_cmd} run {model_name}"',
                shell=True
            )
        else:
            term_cmd = None
            for term in ["x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal"]:
                if subprocess.call(f"which {term}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                    term_cmd = term
                    break
            if term_cmd:
                if term_cmd == "gnome-terminal":
                    subprocess.Popen(f'{term_cmd} -- bash -c "{self.ollama_cmd} run {model_name}; exec bash"', shell=True, stderr=subprocess.DEVNULL)
                else:
                    subprocess.Popen(f'{term_cmd} -e bash -c "{self.ollama_cmd} run {model_name}; exec bash"', shell=True, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(f'nohup {self.ollama_cmd} run {model_name} > /dev/null 2>&1 &', shell=True)
        print(f"[OK] 模型 {model_name} 已在新窗口启动")
        return True
    
    def delete_model(self, model_name):
        """删除模型"""
        stdout, stderr, code = self.run_cmd(f"{self.ollama_cmd} rm {model_name}", timeout=10)
        if code == 0:
            print(f"[OK] 模型 {model_name} 已删除")
            return True
        else:
            print(f"[ERROR] 删除失败: {stderr}")
            return False
    
    def stop_model(self, model_name):
        """停止运行中的模型"""
        if not self.is_ollama_running():
            print("[INFO] Ollama 服务未运行，无需停止")
            return True
        
        stdout, stderr, code = self.run_cmd(f"{self.ollama_cmd} stop {model_name}", timeout=5)
        return code == 0

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_menu():
    """打印菜单 - 根据服务状态动态显示"""
    manager = OllamaManager()
    service_running = manager.is_ollama_running()
    
    print("=" * 60)
    print("                  Ollama 管理器")
    print("=" * 60)
    print()
    
    # 显示状态
    if service_running:
        print("  Ollama 服务: [RUNNING]")
        running = manager.get_running_models()
        if running:
            print(f"  运行中模型: {', '.join(running)}")
        else:
            print("  运行中模型: (无)")
    else:
        print("  Ollama 服务: [STOPPED]")
        print("  运行中模型: (服务未启动)")
    
    print()
    print("=" * 60)
    
    if service_running:
        # 服务运行时显示完整菜单
        print("  1. 启动 Ollama 服务")
        print("  2. 停止 Ollama 服务")
        print("  3. 重启 Ollama 服务")
        print("  -" * 30)
        print("  4. 查看已安装模型")
        print("  5. 安装新模型")
        print("  6. 运行/加载模型")
        print("  7. 停止运行中的模型")
        print("  8. 删除模型")
    else:
        # 服务停止时只显示服务控制菜单
        print("  1. 启动 Ollama 服务")
        print("  -" * 30)
        print("  [提示] 服务未启动，请先选择 1 启动服务")
    
    print("  -" * 30)
    print("  0. 退出")
    print("=" * 60)

def print_installed_models(manager):
    """打印已安装的模型"""
    if not manager.is_ollama_running():
        print("\n[WARN] Ollama 服务未运行，无法查看已安装模型")
        print("[INFO] 请先选择 1 启动服务")
        return []
    
    installed = manager.get_installed_models()
    
    if not installed:
        print("\n[INFO] 没有已安装的模型")
        return []
    
    print("\n已安装的模型:")
    print("-" * 60)
    print(f"  {ljust_cjk('序号', 4)} {ljust_cjk('模型名称', 25)} {ljust_cjk('大小', 10)}")
    print("-" * 60)

    idx = 1
    model_list = []
    for name, info in installed.items():
        print(f"  {idx:<4} {ljust_cjk(name, 25)} {ljust_cjk(info.get('size', 'unknown'), 10)}")
        model_list.append(name)
        idx += 1

    return model_list

def display_width(s):
    """计算字符串的显示宽度（CJK=2，ASCII=1）"""
    return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in s)

def ljust_cjk(s, width):
    """按显示宽度左对齐"""
    return s + ' ' * max(0, width - display_width(s))

def parse_size_to_gb(size_str):
    """将大小字符串解析为 GB 数值"""
    if size_str == "未知":
        return float('inf')
    try:
        if size_str.endswith('GB'):
            return float(size_str.replace('GB', '').strip())
        elif size_str.endswith('MB'):
            return float(size_str.replace('MB', '').strip()) / 1024
    except:
        return float('inf')
    return float('inf')

def get_available_memory_gb():
    """获取可用内存（GB）"""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return mem.available / (1024**3)
    except:
        return 0

def print_available_models(manager):
    """打印可安装的模型（按大小排序，标注推荐）"""
    installed = manager.get_installed_models() if manager.is_ollama_running() else {}
    avail_gb = get_available_memory_gb()
    
    # 排序：按大小升序，未知放最后
    sorted_models = sorted(VLM_MODELS, key=lambda m: parse_size_to_gb(m['size']))
    
    print(f"\n可安装的 VLM 模型 (可用内存: {avail_gb:.1f}GB)")
    print("-" * 96)
    print(f"  {ljust_cjk('序号', 4)} {ljust_cjk('模型名称', 22)} {ljust_cjk('大小', 8)} {ljust_cjk('说明', 34)} {ljust_cjk('推荐', 10)}")
    print("-" * 96)

    idx = 1
    model_names = {}

    for model in sorted_models:
        name = model['name']
        size = model['size']
        desc = model['desc']
        is_installed = name in installed

        size_gb = parse_size_to_gb(size)
        if is_installed:
            recommend = "[已安装]"
        elif size == "未知":
            recommend = "[未知]"
        else:
            is_fit = size_gb < avail_gb * 0.85
            recommend = "[适合]" if is_fit else "[过大]"

        print(f"  {idx:<4} {ljust_cjk(name, 22)} {ljust_cjk(size, 8)} {ljust_cjk(desc, 34)} {ljust_cjk(recommend, 10)}")
        model_names[str(idx)] = name
        idx += 1

    print("-" * 96)
    print("  或直接输入模型名称 (如: llama3.2)")
    print("-" * 96)

    return model_names

def main():
    try:
        import psutil
    except ImportError:
        print("[WARN] 需要安装 psutil: pip install psutil")
        print("[INFO] 正在尝试安装...")
        os.system("pip install psutil requests")
        input("安装完成，按回车继续...")
    
    manager = OllamaManager()
    
    while True:
        clear_screen()
        print_menu()
        
        service_running = manager.is_ollama_running()
        
        # 服务停止时只显示选项 1 和 0
        if not service_running:
            choice = input("\n请选择 (0/1): ").strip()
            
            if choice == "0":
                print("再见！")
                break
            elif choice == "1":
                manager.start_service()
                input("\n按回车继续...")
            else:
                print("[ERROR] 无效选项，请选择 1 启动服务或 0 退出")
                time.sleep(1)
            continue
        
        # 服务运行时显示完整菜单
        choice = input("\n请选择 (0-8): ").strip()
        
        if choice == "0":
            print("再见！")
            break
        
        elif choice == "1":
            manager.start_service()
            input("\n按回车继续...")
        
        elif choice == "2":
            manager.stop_service()
            input("\n按回车继续...")
        
        elif choice == "3":
            manager.stop_service()
            time.sleep(2)
            manager.start_service()
            input("\n按回车继续...")
        
        elif choice == "4":
            clear_screen()
            print_installed_models(manager)
            input("\n按回车继续...")
        
        elif choice == "5":
            clear_screen()
            model_names = print_available_models(manager)
            
            model_input = input("\n请输入序号或模型名称: ").strip()
            
            if model_input in model_names:
                model_name = model_names[model_input]
            else:
                model_name = model_input
            
            if model_name:
                manager.pull_model(model_name)
            input("\n按回车继续...")
        
        elif choice == "6":
            clear_screen()
            installed_models = list(manager.get_installed_models().keys())
            
            if not installed_models:
                print("\n[INFO] 没有已安装的模型")
                print("[INFO] 请先安装模型 (选项5)")
                input("\n按回车继续...")
                continue
            
            print("\n已安装的模型:")
            for idx, name in enumerate(installed_models, 1):
                print(f"  {idx}. {name}")
            
            try:
                model_choice = input("\n请选择要运行的模型序号: ").strip()
                idx = int(model_choice) - 1
                if 0 <= idx < len(installed_models):
                    manager.run_model(installed_models[idx])
                else:
                    print("[ERROR] 无效选择")
            except ValueError:
                print("[ERROR] 请输入数字")
            
            input("\n按回车继续...")
        
        elif choice == "7":
            clear_screen()
            running = manager.get_running_models()
            
            if not running:
                print("\n[INFO] 没有运行中的模型")
                input("\n按回车继续...")
                continue
            
            print("\n运行中的模型:")
            for idx, model in enumerate(running, 1):
                print(f"  {idx}. {model}")
            
            model_choice = input("\n请选择要停止的模型序号 (或输入 'all' 停止全部): ").strip()
            
            if model_choice.lower() == 'all':
                for model in running:
                    manager.stop_model(model)
                print("[OK] 已停止所有模型")
            else:
                try:
                    idx = int(model_choice) - 1
                    if 0 <= idx < len(running):
                        manager.stop_model(running[idx])
                        print(f"[OK] 已停止模型: {running[idx]}")
                    else:
                        print("[ERROR] 无效选择")
                except ValueError:
                    print("[ERROR] 请输入数字")
            
            input("\n按回车继续...")
        
        elif choice == "8":
            clear_screen()
            installed_models = list(manager.get_installed_models().keys())
            
            if not installed_models:
                print("\n[INFO] 没有已安装的模型")
                input("\n按回车继续...")
                continue
            
            print("\n已安装的模型:")
            for idx, name in enumerate(installed_models, 1):
                print(f"  {idx}. {name}")
            
            confirm = input("\n确认要删除模型？(y/n): ").strip().lower()
            if confirm == 'y':
                try:
                    model_choice = input("请选择要删除的模型序号: ").strip()
                    idx = int(model_choice) - 1
                    if 0 <= idx < len(installed_models):
                        manager.delete_model(installed_models[idx])
                    else:
                        print("[ERROR] 无效选择")
                except ValueError:
                    print("[ERROR] 请输入数字")
            
            input("\n按回车继续...")
        
        else:
            print("[ERROR] 无效选项")
            time.sleep(1)

if __name__ == "__main__":
    main()
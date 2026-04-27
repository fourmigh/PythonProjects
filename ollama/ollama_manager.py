#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import os
import time
import threading
import psutil

# 尝试导入 rich 库（可选，如果没有就降级到简单输出）
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("提示: 安装 'rich' 库可获得更好的界面效果: pip install rich")
    print()

class OllamaManager:
    def __init__(self):
        self.ollama_cmd = "ollama"
        self.ollama_port = 11434
        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None
    
    def run_cmd(self, cmd, capture_output=True, timeout=300):
        """执行命令并返回结果"""
        try:
            if capture_output:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=timeout
                )
                return result.stdout.strip(), result.stderr.strip(), result.returncode
            else:
                subprocess.Popen(cmd, shell=True)
                return "", "", 0
        except subprocess.TimeoutExpired:
            return "", "命令超时", -1
        except Exception as e:
            return "", str(e), -1
    
    def is_ollama_running(self):
        """检查 Ollama 服务是否运行"""
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and 'ollama' in proc.info['name'].lower():
                return True
        return False
    
    def get_models(self):
        """获取已安装的模型列表"""
        stdout, stderr, code = self.run_cmd(f"{self.ollama_cmd} list")
        if code != 0:
            return []
        
        models = []
        lines = stdout.strip().split('\n')
        if len(lines) <= 1:
            return []
        
        for line in lines[1:]:  # 跳过表头
            parts = line.split()
            if parts:
                models.append({
                    'name': parts[0],
                    'id': parts[1] if len(parts) > 1 else '',
                    'size': parts[2] if len(parts) > 2 else '',
                    'modified': ' '.join(parts[3:]) if len(parts) > 3 else ''
                })
        return models
    
    def get_running_models(self):
        """获取运行中的模型"""
        stdout, stderr, code = self.run_cmd(f"{self.ollama_cmd} ps")
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
    
    def pull_model(self, model_name):
        """下载模型"""
        if RICH_AVAILABLE:
            self.console.print(f"\n[cyan]正在下载模型: {model_name}[/cyan]")
            self.console.print("[yellow]这可能需要几分钟到几十分钟，请耐心等待...[/yellow]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description=f"下载中...", total=None)
                stdout, stderr, code = self.run_cmd(f"{self.ollama_cmd} pull {model_name}", timeout=3600)
        else:
            print(f"\n正在下载模型: {model_name}")
            print("这可能需要几分钟到几十分钟，请耐心等待...")
            stdout, stderr, code = self.run_cmd(f"{self.ollama_cmd} pull {model_name}", timeout=3600)
        
        if code == 0:
            if RICH_AVAILABLE:
                self.console.print(f"[green]✓ 模型 {model_name} 下载完成[/green]")
            else:
                print(f"✓ 模型 {model_name} 下载完成")
            return True
        else:
            if RICH_AVAILABLE:
                self.console.print(f"[red]✗ 下载失败: {stderr}[/red]")
            else:
                print(f"✗ 下载失败: {stderr}")
            return False
    
    def delete_model(self, model_name):
        """删除模型"""
        stdout, stderr, code = self.run_cmd(f"{self.ollama_cmd} rm {model_name}")
        if code == 0:
            if RICH_AVAILABLE:
                self.console.print(f"[green]✓ 模型 {model_name} 已删除[/green]")
            else:
                print(f"✓ 模型 {model_name} 已删除")
            return True
        else:
            if RICH_AVAILABLE:
                self.console.print(f"[red]✗ 删除失败: {stderr}[/red]")
            else:
                print(f"✗ 删除失败: {stderr}")
            return False
    
    def stop_model(self, model_name):
        """停止运行中的模型"""
        stdout, stderr, code = self.run_cmd(f"{self.ollama_cmd} stop {model_name}")
        return code == 0
    
    def start_service(self):
        """启动 Ollama 服务"""
        if self.is_ollama_running():
            if RICH_AVAILABLE:
                self.console.print("[yellow]Ollama 已经在运行中[/yellow]")
            else:
                print("Ollama 已经在运行中")
            return True
        
        if RICH_AVAILABLE:
            self.console.print("[cyan]正在启动 Ollama 服务...[/cyan]")
        
        # 后台启动服务
        subprocess.Popen(f"start /B {self.ollama_cmd} serve", shell=True)
        
        # 等待服务启动
        for i in range(10):
            time.sleep(1)
            if self.is_ollama_running():
                if RICH_AVAILABLE:
                    self.console.print("[green]✓ Ollama 服务已启动[/green]")
                else:
                    print("✓ Ollama 服务已启动")
                return True
        
        if RICH_AVAILABLE:
            self.console.print("[red]✗ 启动失败[/red]")
        else:
            print("✗ 启动失败")
        return False
    
    def stop_service(self):
        """停止 Ollama 服务"""
        if not self.is_ollama_running():
            if RICH_AVAILABLE:
                self.console.print("[yellow]Ollama 未运行[/yellow]")
            else:
                print("Ollama 未运行")
            return True
        
        if RICH_AVAILABLE:
            self.console.print("[cyan]正在停止 Ollama...[/cyan]")
        
        # 杀死所有 ollama 进程
        for proc in psutil.process_iter(['name', 'pid']):
            if proc.info['name'] and 'ollama' in proc.info['name'].lower():
                proc.kill()
        
        time.sleep(2)
        
        if not self.is_ollama_running():
            if RICH_AVAILABLE:
                self.console.print("[green]✓ Ollama 已停止[/green]")
            else:
                print("✓ Ollama 已停止")
            return True
        else:
            if RICH_AVAILABLE:
                self.console.print("[red]✗ 停止失败[/red]")
            else:
                print("✗ 停止失败")
            return False
    
    def run_model(self, model_name):
        """运行模型（在新窗口）"""
        if not self.is_ollama_running():
            if RICH_AVAILABLE:
                self.console.print("[yellow]Ollama 未运行，正在启动...[/yellow]")
            self.start_service()
        
        if RICH_AVAILABLE:
            self.console.print(f"[cyan]正在启动模型: {model_name}[/cyan]")
        
        # 在新窗口中运行模型
        subprocess.Popen(f'start "Ollama - {model_name}" cmd /k "echo 模型: {model_name} && echo. && ollama run {model_name}"', shell=True)
        
        if RICH_AVAILABLE:
            self.console.print(f"[green]✓ 模型 {model_name} 已在新窗口启动[/green]")
        else:
            print(f"✓ 模型 {model_name} 已在新窗口启动")
        return True

def print_table_rich(manager):
    """使用 rich 打印表格"""
    console = Console()
    
    # 状态面板
    status_text = "🟢 运行中" if manager.is_ollama_running() else "🔴 未运行"
    status_panel = Panel(f"[bold]Ollama 服务状态: {status_text}[/bold]", title="系统状态")
    console.print(status_panel)
    console.print()
    
    # 运行中的模型表格
    running = manager.get_running_models()
    running_table = Table(title="运行中的模型")
    running_table.add_column("模型名称", style="cyan")
    if running:
        for model in running:
            running_table.add_row(model)
    else:
        running_table.add_row("(无)", style="dim")
    console.print(running_table)
    console.print()
    
    # 已安装模型表格
    models = manager.get_models()
    model_table = Table(title="已安装的模型")
    model_table.add_column("序号", style="yellow")
    model_table.add_column("模型名称", style="cyan")
    model_table.add_column("大小", style="green")
    model_table.add_column("最后修改", style="dim")
    
    if models:
        for idx, model in enumerate(models, 1):
            model_table.add_row(str(idx), model['name'], model['size'], model['modified'])
    else:
        model_table.add_row("", "(无)", "", "")
    console.print(model_table)

def print_table_simple(manager):
    """简单打印模式"""
    print("=" * 50)
    print(f"Ollama 服务状态: {'运行中 ✅' if manager.is_ollama_running() else '未运行 ❌'}")
    print("=" * 50)
    
    print("\n运行中的模型:")
    running = manager.get_running_models()
    if running:
        for model in running:
            print(f"  - {model}")
    else:
        print("  (无)")
    
    print("\n已安装的模型:")
    models = manager.get_models()
    if models:
        for idx, model in enumerate(models, 1):
            print(f"  {idx}. {model['name']} ({model['size']})")
    else:
        print("  (无)")

def show_menu():
    """显示主菜单"""
    if RICH_AVAILABLE:
        menu_text = """
[bold cyan]Ollama 管理器 - 主菜单[/bold cyan]

[bold yellow]服务控制[/bold yellow]
  1. 启动 Ollama 服务
  2. 停止 Ollama 服务
  3. 重启 Ollama 服务

[bold yellow]模型管理[/bold yellow]  (无需服务运行)
  4. 查看模型列表
  5. 安装新模型
  6. 运行/加载模型
  7. 停止运行中的模型
  8. 删除模型

[bold yellow]其他[/bold yellow]
  9. 完整状态查看
  0. 退出

[dim]提示: 模型安装/删除/列表功能不需要服务运行[/dim]
"""
        print(menu_text)
    else:
        print("=" * 50)
        print("Ollama 管理器 - 主菜单")
        print("=" * 50)
        print("\n服务控制:")
        print("  1. 启动 Ollama 服务")
        print("  2. 停止 Ollama 服务")
        print("  3. 重启 Ollama 服务")
        print("\n模型管理 (无需服务运行):")
        print("  4. 查看模型列表")
        print("  5. 安装新模型")
        print("  6. 运行/加载模型")
        print("  7. 停止运行中的模型")
        print("  8. 删除模型")
        print("\n其他:")
        print("  9. 完整状态查看")
        print("  0. 退出")
        print("\n提示: 模型安装/删除/列表功能不需要服务运行")

def main():
    manager = OllamaManager()
    
    # 推荐模型列表
    RECOMMENDED_MODELS = {
        "1": {"name": "llama3.2-vision", "desc": "Meta官方视觉模型 11B", "size": "7.9GB"},
        "2": {"name": "llava", "desc": "经典视觉语言模型 7B", "size": "4.5GB"},
        "3": {"name": "llava-llama3", "desc": "LLaVA升级版 8B", "size": "5.5GB"},
        "4": {"name": "phi3-vision", "desc": "微软轻量级视觉模型 4.2B", "size": "2.8GB"},
        "5": {"name": "moondream", "desc": "边缘设备友好 1.4B", "size": "829MB"},
        "6": {"name": "bakllava", "desc": "高清支持 7B", "size": "5.0GB"},
        "7": {"name": "gemma-2-vision", "desc": "Google视觉模型 9B", "size": "5.5GB"},
        "8": {"name": "qwen2.5-vl", "desc": "通义千问视觉版 7B", "size": "5.5GB"},
        "9": {"name": "llama3.2", "desc": "纯文本对话 3B/7B", "size": "2-4GB"},
        "10": {"name": "qwen2.5", "desc": "通义千问纯文本 7B/14B", "size": "4-8GB"},
    }
    
    while True:
        show_menu()
        
        if RICH_AVAILABLE:
            choice = Prompt.ask("\n请选择", choices=["0","1","2","3","4","5","6","7","8","9"])
        else:
            choice = input("\n请选择: ").strip()
        
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
            if RICH_AVAILABLE:
                print_table_rich(manager)
            else:
                print_table_simple(manager)
            input("\n按回车继续...")
        
        elif choice == "5":
            if RICH_AVAILABLE:
                console = Console()
                console.print("\n[bold]推荐模型清单:[/bold]")
                install_table = Table(title="可安装的模型")
                install_table.add_column("序号", style="yellow")
                install_table.add_column("模型名称", style="cyan")
                install_table.add_column("说明", style="green")
                install_table.add_column("大小", style="dim")
                
                for key, model in RECOMMENDED_MODELS.items():
                    install_table.add_row(key, model['name'], model['desc'], model['size'])
                
                console.print(install_table)
                console.print("\n[dim]也可以直接输入完整的模型名称（如: llama3.2）[/dim]")
                model_input = Prompt.ask("请输入序号或模型名称")
            else:
                print("\n推荐模型清单:")
                for key, model in RECOMMENDED_MODELS.items():
                    print(f"  {key}. {model['name']} - {model['desc']} ({model['size']})")
                print("\n提示: 也可以直接输入完整的模型名称（如: llama3.2）")
                model_input = input("请输入序号或模型名称: ").strip()
            
            # 判断是序号还是模型名
            if model_input in RECOMMENDED_MODELS:
                model_name = RECOMMENDED_MODELS[model_input]['name']
            else:
                model_name = model_input
            
            manager.pull_model(model_name)
            input("\n按回车继续...")
        
        elif choice == "6":
            models = manager.get_models()
            if not models:
                if RICH_AVAILABLE:
                    console = Console()
                    console.print("[yellow]没有已安装的模型，请先安装[/yellow]")
                    if Confirm.ask("是否现在安装？"):
                        # 跳转到安装流程
                        choice = "5"
                        continue
                else:
                    print("没有已安装的模型，请先安装")
                    input("\n按回车继续...")
                continue
            
            if RICH_AVAILABLE:
                console = Console()
                model_table = Table(title="已安装的模型")
                model_table.add_column("序号", style="yellow")
                model_table.add_column("模型名称", style="cyan")
                
                for idx, model in enumerate(models, 1):
                    model_table.add_row(str(idx), model['name'])
                console.print(model_table)
                
                model_choice = Prompt.ask("请选择要运行的模型序号", default="1")
            else:
                print("\n已安装的模型:")
                for idx, model in enumerate(models, 1):
                    print(f"  {idx}. {model['name']}")
                model_choice = input("请选择要运行的模型序号: ").strip()
            
            try:
                idx = int(model_choice) - 1
                if 0 <= idx < len(models):
                    manager.run_model(models[idx]['name'])
                else:
                    print("无效选择")
            except ValueError:
                print("请输入数字")
            
            input("\n按回车继续...")
        
        elif choice == "7":
            running = manager.get_running_models()
            if not running:
                if RICH_AVAILABLE:
                    console = Console()
                    console.print("[yellow]没有运行中的模型[/yellow]")
                else:
                    print("没有运行中的模型")
                input("\n按回车继续...")
                continue
            
            if RICH_AVAILABLE:
                console = Console()
                for idx, model in enumerate(running, 1):
                    console.print(f"{idx}. {model}")
                model_choice = Prompt.ask("请选择要停止的模型序号 (或输入 'all' 停止全部)")
            else:
                print("\n运行中的模型:")
                for idx, model in enumerate(running, 1):
                    print(f"  {idx}. {model}")
                model_choice = input("请选择要停止的模型序号 (或输入 'all' 停止全部): ").strip()
            
            if model_choice.lower() == 'all':
                for model in running:
                    manager.stop_model(model)
                if RICH_AVAILABLE:
                    console = Console()
                    console.print("[green]已停止所有模型[/green]")
                else:
                    print("已停止所有模型")
            else:
                try:
                    idx = int(model_choice) - 1
                    if 0 <= idx < len(running):
                        manager.stop_model(running[idx])
                        if RICH_AVAILABLE:
                            console = Console()
                            console.print(f"[green]已停止模型: {running[idx]}[/green]")
                        else:
                            print(f"已停止模型: {running[idx]}")
                except ValueError:
                    print("无效选择")
            
            input("\n按回车继续...")
        
        elif choice == "8":
            models = manager.get_models()
            if not models:
                if RICH_AVAILABLE:
                    console = Console()
                    console.print("[yellow]没有已安装的模型[/yellow]")
                else:
                    print("没有已安装的模型")
                input("\n按回车继续...")
                continue
            
            if RICH_AVAILABLE:
                console = Console()
                model_table = Table(title="已安装的模型")
                model_table.add_column("序号", style="yellow")
                model_table.add_column("模型名称", style="cyan")
                model_table.add_column("大小", style="green")
                
                for idx, model in enumerate(models, 1):
                    model_table.add_row(str(idx), model['name'], model['size'])
                console.print(model_table)
                
                if Confirm.ask("确认要删除模型吗？", default=False):
                    model_choice = Prompt.ask("请选择要删除的模型序号")
                    try:
                        idx = int(model_choice) - 1
                        if 0 <= idx < len(models):
                            manager.delete_model(models[idx]['name'])
                        else:
                            console.print("[red]无效选择[/red]")
                    except ValueError:
                        console.print("[red]请输入数字[/red]")
            else:
                print("\n已安装的模型:")
                for idx, model in enumerate(models, 1):
                    print(f"  {idx}. {model['name']} ({model['size']})")
                confirm = input("\n确认要删除模型吗？(y/n): ").strip().lower()
                if confirm == 'y':
                    model_choice = input("请选择要删除的模型序号: ").strip()
                    try:
                        idx = int(model_choice) - 1
                        if 0 <= idx < len(models):
                            manager.delete_model(models[idx]['name'])
                        else:
                            print("无效选择")
                    except ValueError:
                        print("请输入数字")
            
            input("\n按回车继续...")
        
        elif choice == "9":
            if RICH_AVAILABLE:
                print_table_rich(manager)
            else:
                print_table_simple(manager)
            input("\n按回车继续...")
        
        else:
            if RICH_AVAILABLE:
                console = Console()
                console.print("[red]无效选项[/red]")
            else:
                print("无效选项")
            input("\n按回车继续...")
        
        # 清屏
        os.system('cls' if os.name == 'nt' else 'clear')

if __name__ == "__main__":
    # 检查是否安装了 psutil
    try:
        import psutil
    except ImportError:
        print("需要安装 psutil 库: pip install psutil")
        sys.exit(1)
    
    # 检查 ollama 是否可用
    manager = OllamaManager()
    _, _, code = manager.run_cmd("ollama --version")
    if code != 0:
        print("错误: 找不到 ollama 命令，请确认已安装并添加到 PATH")
        sys.exit(1)
    
    main()
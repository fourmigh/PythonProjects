#!/usr/bin/env python3
"""
API 服务器管理模块
"""

import subprocess
from pathlib import Path
from typing import Optional


class APIServerManager:
    """API 服务器管理器"""
    
    def __init__(self, llama_path: Path, config_manager):
        """
        初始化服务器管理器
        :param llama_path: llama.cpp 可执行文件目录
        :param config_manager: 配置管理器实例
        """
        self.llama_path = Path(llama_path)
        self.config = config_manager
        self.current_process = None
    
    def _get_executable(self) -> Path:
        """获取服务器可执行文件"""
        exe = self.llama_path / "llama-server"
        
        import sys
        if sys.platform == "win32":
            exe = exe.with_suffix(".exe")
        
        return exe
    
    def _build_command(self, model_path: str, host: str = "127.0.0.1", 
                      port: int = 8080) -> list:
        """构建服务器命令"""
        exe = self._get_executable()
        
        if not exe.exists():
            print(f"[X] 找不到可执行文件: {exe}")
            print(f"   请确认 llama.cpp 是否安装在: {self.llama_path}")
            return []
        
        cmd = [str(exe), "-m", model_path, "--host", host, "--port", str(port)]
        
        # 添加性能参数
        params = self.config.get_default_params()
        cmd.extend([
            "-ngl", str(params.get('n_gpu_layers', 32)),
            "-c", str(params.get('context_size', 4096)),
            "-t", str(params.get('threads', 8)),
        ])
        
        return cmd
    
    def start_server(self, model_path: str, host: str = None, port: int = None,
                     start_proxy: bool = False):
        """启动 API 服务器"""
        if host is None:
            host = self.config.get("server", {}).get("host", "127.0.0.1")
        if port is None:
            port = self.config.get("server", {}).get("port", 8080)
        
        print(f"\n[SERVER] 启动 API 服务器")
        print(f"   地址: http://{host}:{port}")
        print(f"   模型: {Path(model_path).name}")
        print(f"   API 端点: http://{host}:{port}/v1/chat/completions")
        print(f"   兼容 OpenAI API\n")
        
        cmd = self._build_command(model_path, host, port)
        if not cmd:
            return
        
        try:
            server_proc = subprocess.Popen(cmd)
            print("[OK] 服务器运行中...")

            if start_proxy:
                proxy_port = 11434
                print(f"\n[PROXY] 启动 Ollama 兼容代理 (端口 {proxy_port})...")
                try:
                    from server.ollama_proxy import create_app
                    app = create_app(f"http://{host}:{port}")
                    from werkzeug.serving import run_simple
                    run_simple("0.0.0.0", proxy_port, app)
                except KeyboardInterrupt:
                    print("\n[STOP] 正在停止...")
                finally:
                    server_proc.terminate()
                    server_proc.wait()
                    print("[OK] 服务器和代理已停止")
            else:
                server_proc.wait()
                
        except KeyboardInterrupt:
            print("\n[STOP] 正在停止服务器...")
            server_proc.terminate()
            server_proc.wait()
            print("[OK] 服务器已停止")
    
    def start_server_interactive(self, model_path: str):
        """交互式启动服务器"""
        server_config = self.config.get("server", {})
        
        host = input(f"服务器地址 [{server_config.get('host', '127.0.0.1')}]: ").strip()
        if not host:
            host = server_config.get('host', '127.0.0.1')
        
        port_input = input(f"端口 [{server_config.get('port', 8080)}]: ").strip()
        if port_input:
            try:
                port = int(port_input)
            except ValueError:
                print("[X] 端口必须是数字")
                return
        else:
            port = server_config.get('port', 8080)
        
        proxy_choice = input("同时启动 Ollama 兼容代理 (端口 11434)? (y/N): ").strip().lower()
        start_proxy = proxy_choice == 'y'
        
        self.start_server(model_path, host, port, start_proxy)
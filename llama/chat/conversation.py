#!/usr/bin/env python3
"""
对话功能模块
提供交互式对话和单次查询功能
"""

import subprocess
from pathlib import Path
from typing import List, Optional


class ConversationManager:
    """对话管理器"""
    
    def __init__(self, llama_path: Path, config_manager):
        """
        初始化对话管理器
        :param llama_path: llama.cpp 可执行文件目录
        :param config_manager: 配置管理器实例
        """
        self.llama_path = Path(llama_path)
        self.config = config_manager
        self.current_process = None
    
    def _get_executable(self, interactive: bool = False, server: bool = False) -> Path:
        """获取可执行文件路径"""
        if server:
            exe = self.llama_path / "llama-server"
        else:
            exe = self.llama_path / "llama-cli"
        
        # Windows 添加 .exe 后缀
        import sys
        if sys.platform == "win32":
            exe = exe.with_suffix(".exe")
        
        return exe
    
    def _build_command(self, model_path: str, prompt: str = None, 
                      interactive: bool = False, **kwargs) -> List[str]:
        """构建 llama.cpp 命令"""
        exe = self._get_executable(interactive=interactive)
        
        if not exe.exists():
            print(f"[X] 找不到可执行文件: {exe}")
            print(f"   请确认 llama.cpp 是否安装在: {self.llama_path}")
            return []
        
        cmd = [str(exe), "-m", model_path]
        
        if interactive:
            cmd.append("-cnv")
        
        # 添加参数
        params = self.config.get_default_params()
        cmd.extend([
            "-ngl", str(kwargs.get('n_gpu_layers', params.get('n_gpu_layers', 32))),
            "-c", str(kwargs.get('context_size', params.get('context_size', 4096))),
            "-t", str(kwargs.get('threads', params.get('threads', 8))),
            "--temp", str(kwargs.get('temperature', params.get('temperature', 0.7))),
            "--repeat-penalty", str(kwargs.get('repeat_penalty', params.get('repeat_penalty', 1.1))),
            "-b", str(kwargs.get('batch_size', params.get('batch_size', 512)))
        ])
        
        if prompt and not interactive:
            cmd.extend(["-p", prompt])
        
        return cmd
    
    def interactive_chat(self, model_path: str):
        """启动交互式对话"""
        print("\n[CHAT] 启动交互式对话模式")
        print("   - 直接输入问题进行对话")
        print("   - 输入 '/exit' 或按 Ctrl+C 退出\n")
        
        cmd = self._build_command(model_path, interactive=True)
        
        if not cmd:
            return
        
        try:
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            print("\n\n[BYE] 再见!")
    
    def single_query(self, model_path: str, prompt: str):
        """单次查询"""
        cmd = self._build_command(model_path, prompt=prompt)
        
        if not cmd:
            return
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("\n[AI] 模型回答:")
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"[X] 运行出错: {e}")
            if e.stderr:
                print(f"错误信息: {e.stderr}")
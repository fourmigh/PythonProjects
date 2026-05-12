#!/usr/bin/env python3
"""
LLaMA.cpp 管理工具 - 主入口
"""

import os
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import ConfigManager
from models.local_manager import LocalModelManager
from models.downloader import ModelDownloader
from chat.conversation import ConversationManager
from server.api_server import APIServerManager
from llama_cpp_manager import LLaMACppManager


class LLaMAManager:
    """LLaMA.cpp 管理器主类"""
    
    def __init__(self, llama_path: str = None, models_path: str = None):
        """
        初始化管理器
        :param llama_path: llama.cpp 可执行文件所在目录
        :param models_path: 模型文件存放目录
        """
        self.llama_path = Path(llama_path) if llama_path else Path.cwd()
        self.models_path = Path(models_path) if models_path else self.llama_path / "models"
        
        # 初始化各模块
        self.config = ConfigManager(self.llama_path / "llama_config.json")
        
        # 更新配置中的路径
        self.config.set("llama_path", str(self.llama_path))
        self.config.set("models_path", str(self.models_path))
        
        # 初始化各个管理器
        self.local_models = LocalModelManager(self.models_path, self.config)
        self.downloader = ModelDownloader(self.models_path)
        self.chat = ConversationManager(self.llama_path, self.config)
        self.server = APIServerManager(self.llama_path, self.config)
        self.llama_manager = LLaMACppManager(self.llama_path)
    
    def show_menu(self):
        """显示主菜单"""
        while True:
            print("\n" + "="*50)
            print("[MANAGER] LLaMA.cpp 管理器")
            print("="*50)
            print("1. [CHAT] 交互式对话")
            print("2. [?] 单次提问")
            print("3. [SERVER] 启动 API 服务器 (可选 Ollama 代理)")
            print("4. [FILES] 查看本地模型")
            print("5. [STAR] 设置默认模型")
            print("6. [SETTINGS] 编辑默认参数")
            print("7. [DOWNLOAD] 搜索并下载模型")
            print("8. [DELETE] 删除模型")
            print("9. [LLAMA] 管理 llama.cpp")
            print("10. [EXIT] 退出")
            print("="*50)
            
            choice = input("请选择操作: ").strip()
            
            if choice == '1':
                model = self.local_models.get_selected_model()
                if model:
                    self.chat.interactive_chat(model)
                    
            elif choice == '2':
                model = self.local_models.get_selected_model()
                if model:
                    prompt = input("\n请输入问题: ").strip()
                    if prompt:
                        self.chat.single_query(model, prompt)
                        
            elif choice == '3':
                model = self.local_models.get_selected_model()
                if model:
                    self.server.start_server_interactive(model)
                    
            elif choice == '4':
                self.local_models.show_models()
                
            elif choice == '5':
                self.local_models.set_default_model_interactive()
                
            elif choice == '6':
                self.edit_params()
                
            elif choice == '7':
                if self.downloader.is_available():
                    self.downloader.search_and_download_interactive()
                else:
                    print("[X] 下载功能不可用，请先安装: pip install huggingface-hub")
                    
            elif choice == '8':
                self.local_models.delete_model_interactive()
                
            elif choice == '9':
                self.llama_manager.interactive_menu()
                
            elif choice == '10':
                print("[BYE] 再见!")
                break
                
            else:
                print("[X] 无效的选择")
    
    def edit_params(self):
        """编辑默认参数"""
        params = self.config.get_default_params()
        
        print("\n[SETTINGS] 当前参数设置:")
        for key, value in params.items():
            print(f"   {key}: {value}")
        
        print("\n请输入新值 (留空保持不变):")
        for key in list(params.keys()):
            current = params[key]
            new_value = input(f"  {key} [{current}]: ").strip()
            if new_value:
                try:
                    if '.' in new_value:
                        params[key] = float(new_value)
                    else:
                        params[key] = int(new_value)
                except ValueError:
                    print(f"[WARN] 无效的值，保持原值: {current}")
        
        self.config.set_default_params(params)
        print("[OK] 参数已保存")


def main():
    parser = argparse.ArgumentParser(description="LLaMA.cpp 管理工具")
    parser.add_argument("--llama-path", default=os.getcwd(), 
                       help="llama.cpp 所在目录 (默认: 当前目录)")
    parser.add_argument("--models-path", help="模型文件目录 (默认: llama-path/models)")
    
    args = parser.parse_args()
    
    manager = LLaMAManager(args.llama_path, args.models_path)
    manager.show_menu()


if __name__ == "__main__":
    import argparse
    main()
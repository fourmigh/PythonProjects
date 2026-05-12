#!/usr/bin/env python3
"""
本地模型管理模块
提供模型的增删改查功能
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
import shutil


class LocalModelManager:
    """本地模型管理器"""
    
    def __init__(self, models_path: Path, config_manager):
        """
        初始化本地模型管理器
        :param models_path: 模型文件存放目录
        :param config_manager: 配置管理器实例
        """
        self.models_path = Path(models_path)
        self.config = config_manager
        self.models_path.mkdir(parents=True, exist_ok=True)
    
    def list_models(self) -> List[Dict]:
        """
        列出本地所有模型
        :return: 模型信息字典列表
        """
        models = []
        
        # 支持的扩展名
        extensions = ['*.gguf', '*.bin']
        
        for ext in extensions:
            # 查找当前目录
            for file_path in self.models_path.glob(ext):
                models.append(self._get_model_info(file_path))
            
            # 查找子目录
            for file_path in self.models_path.rglob(ext):
                if file_path.parent != self.models_path:  # 避免重复
                    models.append(self._get_model_info(file_path))
        
        # 按修改时间排序（最新的在前）
        models.sort(key=lambda x: x["modified"], reverse=True)
        return models
    
    def _get_model_info(self, file_path: Path) -> Dict:
        """获取模型文件信息"""
        stat = file_path.stat()
        return {
            "path": str(file_path),
            "name": file_path.name,
            "size_gb": stat.st_size / (1024**3),
            "size_mb": stat.st_size / (1024**2),
            "modified": stat.st_mtime,
            "is_default": file_path == Path(self.config.get_default_model() or "")
        }
    
    def show_models(self) -> List[Dict]:
        """显示本地模型列表，返回模型列表"""
        models = self.list_models()
        
        if not models:
            print("[FILES] 本地未找到任何模型文件")
            print(f"   请将 .gguf 模型文件放入: {self.models_path}")
            print("   或使用下载功能获取模型")
            return []
        
        print(f"\n[FILES] 本地模型 (共 {len(models)} 个):")
        print("-" * 70)
        for i, model in enumerate(models, 1):
            default_mark = " [默认]" if model["is_default"] else ""
            print(f"  {i}. {model['name']}{default_mark}")
            print(f"      大小: {model['size_gb']:.2f} GB | 路径: {model['path']}")
        print("-" * 70)
        
        return models
    
    def get_model_by_index(self, index: int) -> Optional[Dict]:
        """通过索引获取模型信息"""
        models = self.list_models()
        if 1 <= index <= len(models):
            return models[index - 1]
        return None
    
    def get_model_by_name(self, name: str) -> Optional[Dict]:
        """通过名称（支持部分匹配）获取模型信息"""
        models = self.list_models()
        for model in models:
            if name.lower() in model["name"].lower():
                return model
        return None
    
    def delete_model(self, model_info: Dict) -> bool:
        """删除模型文件"""
        model_path = Path(model_info["path"])
        model_name = model_info["name"]
        
        print(f"\n[WARN] 即将删除模型: {model_name}")
        print(f"   路径: {model_path}")
        print(f"   大小: {model_info['size_gb']:.2f} GB")
        
        confirm = input("\n确认删除? 此操作不可恢复! (y/N): ").strip().lower()
        
        if confirm != 'y':
            print("[OK] 取消删除")
            return False
        
        try:
            # 如果是默认模型，清除默认设置
            if model_info["is_default"]:
                self.config.clear_default_model()
                print("[INFO] 已清除默认模型设置")
            
            # 删除文件
            model_path.unlink()
            print(f"[OK] 已删除模型: {model_name}")
            return True
            
        except Exception as e:
            print(f"[X] 删除失败: {e}")
            return False
    
    def delete_model_interactive(self) -> bool:
        """交互式删除模型"""
        models = self.show_models()
        if not models:
            return False
        
        try:
            choice = int(input("\n请选择要删除的模型编号 (0 返回): "))
            if choice == 0:
                return False
            if 1 <= choice <= len(models):
                return self.delete_model(models[choice - 1])
            else:
                print("[X] 无效的选择")
                return False
        except ValueError:
            print("[X] 请输入有效的数字")
            return False
    
    def set_default_model_interactive(self) -> bool:
        """交互式设置默认模型"""
        models = self.show_models()
        if not models:
            return False
        
        try:
            choice = int(input("\n请选择要设为默认的模型编号 (0 取消): "))
            if choice == 0:
                return False
            if 1 <= choice <= len(models):
                model_path = models[choice - 1]["path"]
                self.config.set_default_model(model_path)
                print(f"[OK] 默认模型已设置为: {models[choice - 1]['name']}")
                return True
            else:
                print("[X] 无效的选择")
                return False
        except ValueError:
            print("[X] 请输入有效的数字")
            return False
    
    def get_selected_model(self) -> Optional[str]:
        """获取用户选择的模型（优先使用默认模型）"""
        # 尝试使用默认模型
        default_model = self.config.get_default_model()
        if default_model:
            print(f"[INFO] 使用默认模型: {Path(default_model).name}")
            confirm = input("是否使用此模型? (Y/n): ").strip().lower()
            if confirm != 'n':
                return default_model
        
        # 交互式选择
        models = self.show_models()
        if not models:
            return None
        
        try:
            choice = int(input("\n请选择模型编号 (0 取消): "))
            if choice == 0:
                return None
            if 1 <= choice <= len(models):
                selected = models[choice - 1]["path"]
                # 询问是否设为默认
                set_default = input("是否将此模型设为默认? (y/N): ").strip().lower()
                if set_default == 'y':
                    self.config.set_default_model(selected)
                return selected
            else:
                print("[X] 无效的选择")
                return None
        except ValueError:
            print("[X] 请输入有效的数字")
            return None
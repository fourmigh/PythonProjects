#!/usr/bin/env python3
"""
配置管理模块
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Path):
        """
        初始化配置管理器
        :param config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        default_config = {
            "default_model": None,
            "llama_path": None,
            "models_path": None,
            "default_params": {
                "n_gpu_layers": 32,
                "context_size": 4096,
                "threads": 8,
                "temperature": 0.7,
                "repeat_penalty": 1.1,
                "batch_size": 512
            },
            "recent_models": [],
            "server": {
                "host": "127.0.0.1",
                "port": 8080
            }
        }
        
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            # 合并默认值（确保新增字段存在）
            for key, value in default_config.items():
                if key not in self.config:
                    self.config[key] = value
        else:
            self.config = default_config
            self.save_config()
    
    def save_config(self):
        """保存配置文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def get(self, key: str, default=None):
        """获取配置项"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置配置项"""
        self.config[key] = value
        self.save_config()
    
    def get_default_params(self) -> Dict[str, Any]:
        """获取默认参数"""
        return self.config.get("default_params", {})
    
    def set_default_params(self, params: Dict[str, Any]):
        """设置默认参数"""
        self.config["default_params"] = params
        self.save_config()
    
    def get_default_model(self) -> Optional[str]:
        """获取默认模型路径"""
        model_path = self.config.get("default_model")
        if model_path and Path(model_path).exists():
            return model_path
        return None
    
    def set_default_model(self, model_path: str):
        """设置默认模型"""
        self.config["default_model"] = model_path
        self.save_config()
    
    def clear_default_model(self):
        """清除默认模型"""
        self.config["default_model"] = None
        self.save_config()
    
    def add_recent_model(self, model_path: str, max_recent: int = 5):
        """添加模型到最近使用列表"""
        recent = self.config.get("recent_models", [])
        
        # 移除已存在的
        if model_path in recent:
            recent.remove(model_path)
        
        # 添加到开头
        recent.insert(0, model_path)
        
        # 保持最大数量
        self.config["recent_models"] = recent[:max_recent]
        self.save_config()
    
    def get_recent_models(self) -> list:
        """获取最近使用的模型列表"""
        return self.config.get("recent_models", [])
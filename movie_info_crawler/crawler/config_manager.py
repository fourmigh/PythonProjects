"""配置管理模块 - 管理多个配置文件"""

import json
import os
from typing import List, Any
from pathlib import Path


class ConfigManager:
    """配置文件管理器 - 统一管理所有配置"""
    
    def __init__(self, config_dir: str = '.'):
        self.config_dir = Path(config_dir)
        
        # 配置文件路径
        self.movies_file = self.config_dir / 'config.json'
        self.settings_file = self.config_dir / 'settings.json'

        # 配置数据
        self.movies_config: dict = {}
        self.settings_config: dict = {}
        
        # 加载所有配置
        self._load_all_configs()
    
    def _load_all_configs(self) -> None:
        """加载所有配置文件"""
        self._load_movies_config()
        self._load_settings_config()
    
    def _load_movies_config(self) -> None:
        """加载电影列表配置"""
        default = {"movies": ["疯狂的石头", "爱情神话", "人生大事"]}
        
        if self.movies_file.exists():
            with open(self.movies_file, 'r', encoding='utf-8') as f:
                self.movies_config = json.load(f)
            print(f"✓ 已加载电影配置: {self.movies_file}")
        else:
            self.movies_config = default
            self._save_movies_config()
            print(f"✓ 已创建电影配置文件: {self.movies_file}")
            print("  请根据需要修改电影列表后重新运行程序")
    
    def _load_settings_config(self) -> None:
        """加载系统设置"""
        default = {
            "settings": {
                "request_interval": 1,
                "max_search_results": 5,
                "timeout": 10,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        }
        
        if self.settings_file.exists():
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                self.settings_config = json.load(f)
            print(f"✓ 已加载系统设置: {self.settings_file}")
        else:
            self.settings_config = default
            self._save_settings_config()
            print(f"✓ 已创建设置文件: {self.settings_file}")
    
    def _save_movies_config(self) -> None:
        """保存电影配置"""
        with open(self.movies_file, 'w', encoding='utf-8') as f:
            json.dump(self.movies_config, f, ensure_ascii=False, indent=2)
    
    def _save_settings_config(self) -> None:
        """保存系统设置"""
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings_config, f, ensure_ascii=False, indent=2)
    
    @property
    def movies(self) -> List[str]:
        """获取电影列表"""
        return self.movies_config.get('movies', [])
    
    @movies.setter
    def movies(self, value: List[str]) -> None:
        """设置电影列表"""
        self.movies_config['movies'] = value
        self._save_movies_config()
    
    @property
    def request_interval(self) -> int:
        """获取请求间隔（秒）"""
        return self.settings_config.get('settings', {}).get('request_interval', 1)
    
    @property
    def max_search_results(self) -> int:
        """获取最大搜索结果数"""
        return self.settings_config.get('settings', {}).get('max_search_results', 5)
    
    @property
    def timeout(self) -> int:
        """获取请求超时时间"""
        return self.settings_config.get('settings', {}).get('timeout', 10)
    
    @property
    def user_agent(self) -> str:
        """获取User-Agent"""
        return self.settings_config.get('settings', {}).get('user_agent', 
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
"""数据模型定义 - 使用枚举类统一管理所有字段"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class MovieField(Enum):
    """电影字段枚举 - 单一数据源"""
    
    # 基础信息
    TITLE = ("片名", "title")
    YEAR = ("年份", "year")
    AKA = ("又名", "aka")
    
    # 人员信息
    DIRECTOR = ("导演", "director")
    SCREENWRITER = ("编剧", "screenwriter")
    ACTORS = ("主演", "actors")
    
    # 分类信息
    GENRE = ("类型", "genre")
    REGION = ("地区", "region")
    LANGUAGE = ("语言", "language")
    
    # 时间信息
    RELEASE_DATE = ("上映日期", "release_date")
    RUNTIME = ("片长", "runtime")
    
    # 评分信息
    RATING = ("豆瓣评分", "rating")
    RATING_COUNT = ("评分人数", "rating_count")
    
    # 链接信息
    DOUBAN_LINK = ("豆瓣链接", "douban_link")
    IMDB_LINK = ("IMDb链接", "imdb_link")
    
    # 财务信息
    BOX_OFFICE = ("票房", "box_office")

    # 简介
    SUMMARY = ("简介", "summary")
    
    def __init__(self, label: str, key: str):
        self.label = label
        self.key = key
    
    @classmethod
    def get_by_label(cls, label: str) -> 'MovieField':
        """根据中文标签获取枚举项"""
        for field in cls:
            if field.label == label:
                return field
        raise ValueError(f"未找到标签为 '{label}' 的字段")
    
    @classmethod
    def get_by_key(cls, key: str) -> 'MovieField':
        """根据key获取枚举项"""
        for field in cls:
            if field.key == key:
                return field
        raise ValueError(f"未找到key为 '{key}' 的字段")
    
    @classmethod
    def get_all_labels(cls) -> List[str]:
        """获取所有中文标签"""
        return [field.label for field in cls]
    
    @classmethod
    def get_all_keys(cls) -> List[str]:
        """获取所有key"""
        return [field.key for field in cls]
    
    @classmethod
    def get_label_to_key_map(cls) -> Dict[str, str]:
        """获取标签到key的映射"""
        return {field.label: field.key for field in cls}
    
    @classmethod
    def get_key_to_label_map(cls) -> Dict[str, str]:
        """获取key到标签的映射"""
        return {field.key: field.label for field in cls}


# 预定义的字段组合（使用枚举项列表）
FIELD_SETS = {
    "COMPACT": [
        MovieField.TITLE,
        MovieField.DIRECTOR,
        MovieField.YEAR,
        MovieField.RATING,
    ],
    "DEFAULT": [
        MovieField.TITLE,
        MovieField.YEAR,
        MovieField.DIRECTOR,
        MovieField.ACTORS,
        MovieField.GENRE,
        MovieField.REGION,
        MovieField.LANGUAGE,
        MovieField.RELEASE_DATE,
        MovieField.RUNTIME,
        MovieField.RATING,
        MovieField.RATING_COUNT,
    ],
    "FULL": list(MovieField),  # 所有字段
}

# 便捷访问
COMPACT_FIELDS = FIELD_SETS["COMPACT"]
DEFAULT_FIELDS = FIELD_SETS["DEFAULT"]
FULL_FIELDS = FIELD_SETS["FULL"]


@dataclass
class MovieInfo:
    """电影详细信息 - 基于枚举的动态存储"""
    
    _data: Dict[MovieField, str] = field(default_factory=dict)
    
    def __post_init__(self):
        # 初始化所有字段为空字符串
        for field in MovieField:
            if field not in self._data:
                self._data[field] = ''
    
    def __getattr__(self, name: str) -> str:
        """支持点号访问属性（使用枚举的key或label）"""
        if name.startswith('_'):
            return super().__getattribute__(name)
        
        # 尝试通过key查找
        try:
            field = MovieField.get_by_key(name)
            return self._data.get(field, '')
        except ValueError:
            pass
        
        # 尝试通过label查找
        try:
            field = MovieField.get_by_label(name)
            return self._data.get(field, '')
        except ValueError:
            pass
        
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name: str, value: Any) -> None:
        """支持点号设置属性"""
        if name.startswith('_'):
            super().__setattr__(name, value)
            return
        
        # 尝试通过key查找
        try:
            field = MovieField.get_by_key(name)
            self._data[field] = str(value) if value else ''
            return
        except ValueError:
            pass
        
        # 尝试通过label查找
        try:
            field = MovieField.get_by_label(name)
            self._data[field] = str(value) if value else ''
            return
        except ValueError:
            pass
        
        super().__setattr__(name, value)
    
    def get(self, field: MovieField) -> str:
        """通过枚举获取字段值"""
        return self._data.get(field, '')
    
    def get_by_label(self, label: str) -> str:
        """通过中文标签获取字段值"""
        field = MovieField.get_by_label(label)
        return self._data.get(field, '')
    
    def get_by_key(self, key: str) -> str:
        """通过key获取字段值"""
        field = MovieField.get_by_key(key)
        return self._data.get(field, '')
    
    def set(self, field: MovieField, value: str) -> None:
        """通过枚举设置字段值"""
        self._data[field] = value
    
    def set_by_label(self, label: str, value: str) -> None:
        """通过中文标签设置字段值"""
        field = MovieField.get_by_label(label)
        self._data[field] = value
    
    def to_dict(self, use_label: bool = True) -> Dict[str, str]:
        """转换为字典
        
        Args:
            use_label: True时使用中文标签作为key，False时使用英文key
        """
        if use_label:
            return {field.label: value for field, value in self._data.items() if value}
        else:
            return {field.key: value for field, value in self._data.items() if value}
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'MovieInfo':
        """从字典创建实例"""
        instance = cls()
        for key, value in data.items():
            # 尝试通过标签查找
            try:
                field = MovieField.get_by_label(key)
                instance.set(field, value)
            except ValueError:
                # 尝试通过key查找
                try:
                    field = MovieField.get_by_key(key)
                    instance.set(field, value)
                except ValueError:
                    pass
        return instance
    
    @classmethod
    def get_available_fields(cls) -> List[MovieField]:
        """获取所有可用字段枚举"""
        return list(MovieField)
    
    @classmethod
    def get_available_labels(cls) -> List[str]:
        """获取所有可用中文标签"""
        return MovieField.get_all_labels()


@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    url: str
    year: str = ''


@dataclass
class MovieResult:
    """电影处理结果"""
    search_name: str           # 用户搜索的电影名称
    found: bool = False        # 是否找到
    info: Optional[MovieInfo] = None  # 电影信息
    error: Optional[str] = None       # 错误信息


@dataclass
class UserChoice:
    """用户选择结果"""
    type: str  # 'select', 'manual', 'skip'
    index: Optional[int] = None
    url: Optional[str] = None
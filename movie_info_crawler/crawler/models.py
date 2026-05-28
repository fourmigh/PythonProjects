"""数据模型定义 - 使用枚举类统一管理所有字段"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class Source:
    """数据来源常量"""
    DOUBAN = "豆瓣"
    MAOYAN = "猫眼"
    ALL = (DOUBAN, MAOYAN)


class MovieField(Enum):
    """电影字段枚举"""

    TITLE = ("片名", "title")
    YEAR = ("年份", "year")
    AKA = ("又名", "aka")
    DIRECTOR = ("导演", "director")
    SCREENWRITER = ("编剧", "screenwriter")
    ACTORS = ("主演", "actors")
    GENRE = ("类型", "genre")
    REGION = ("地区", "region")
    LANGUAGE = ("语言", "language")
    RELEASE_DATE = ("上映日期", "release_date")
    RUNTIME = ("片长", "runtime")
    RATING = ("评分", "rating")
    RATING_COUNT = ("评分人数", "rating_count")
    DOUBAN_LINK = ("豆瓣链接", "douban_link")
    IMDB_LINK = ("IMDb链接", "imdb_link")
    BOX_OFFICE = ("票房", "box_office")
    WANT_TO_SEE = ("想看人数", "want_to_see")
    SUMMARY = ("简介", "summary")

    def __init__(self, label: str, key: str):
        self.label = label
        self.key = key

    @classmethod
    def get_by_label(cls, label: str) -> 'MovieField':
        for field in cls:
            if field.label == label:
                return field
        raise ValueError(f"未找到标签为 '{label}' 的字段")

    @classmethod
    def get_by_key(cls, key: str) -> 'MovieField':
        for field in cls:
            if field.key == key:
                return field
        raise ValueError(f"未找到key为 '{key}' 的字段")

    @classmethod
    def get_all_labels(cls) -> List[str]:
        return [field.label for field in cls]

    @classmethod
    def get_all_keys(cls) -> List[str]:
        return [field.key for field in cls]

    @classmethod
    def get_label_to_key_map(cls) -> Dict[str, str]:
        return {field.label: field.key for field in cls}

    @classmethod
    def get_key_to_label_map(cls) -> Dict[str, str]:
        return {field.key: field.label for field in cls}


FIELD_SETS = {
    "COMPACT": [
        MovieField.TITLE, MovieField.DIRECTOR, MovieField.YEAR, MovieField.RATING,
    ],
    "DEFAULT": [
        MovieField.TITLE, MovieField.YEAR, MovieField.DIRECTOR, MovieField.ACTORS,
        MovieField.GENRE, MovieField.REGION, MovieField.LANGUAGE,
        MovieField.RELEASE_DATE, MovieField.RUNTIME,
        MovieField.RATING, MovieField.RATING_COUNT,
    ],
    "FULL": list(MovieField),
}

COMPACT_FIELDS = FIELD_SETS["COMPACT"]
DEFAULT_FIELDS = FIELD_SETS["DEFAULT"]
FULL_FIELDS = FIELD_SETS["FULL"]


@dataclass
class MovieInfo:
    """电影详细信息 - 多来源存储"""

    _data: Dict[MovieField, Dict[str, str]] = field(default_factory=dict)

    def set(self, field: MovieField, value: str, source: str = Source.DOUBAN) -> None:
        if value:
            self._data.setdefault(field, {})[source] = value

    def get(self, field: MovieField, source: str = None) -> str:
        sources = self._data.get(field, {})
        if source:
            return sources.get(source, '')
        for s in Source.ALL:
            if s in sources:
                return sources[s]
        return ''

    def get_all(self, field: MovieField) -> Dict[str, str]:
        return dict(self._data.get(field, {}))

    def merge(self, other: 'MovieInfo') -> None:
        for field, sources in other._data.items():
            for src, value in sources.items():
                self.set(field, value, src)

    def __getattr__(self, name: str) -> str:
        if name.startswith('_'):
            return super().__getattribute__(name)
        try:
            field = MovieField.get_by_key(name)
            return self.get(field)
        except ValueError:
            pass
        try:
            field = MovieField.get_by_label(name)
            return self.get(field)
        except ValueError:
            pass
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith('_'):
            super().__setattr__(name, value)
            return
        try:
            field = MovieField.get_by_key(name)
            self.set(field, str(value) if value else '')
            return
        except ValueError:
            pass
        try:
            field = MovieField.get_by_label(name)
            self.set(field, str(value) if value else '')
            return
        except ValueError:
            pass
        super().__setattr__(name, value)

    def get_by_label(self, label: str) -> str:
        field = MovieField.get_by_label(label)
        return self.get(field)

    def get_by_key(self, key: str) -> str:
        field = MovieField.get_by_key(key)
        return self.get(field)

    def set_by_label(self, label: str, value: str) -> None:
        field = MovieField.get_by_label(label)
        self.set(field, value)

    def to_dict(self, use_label: bool = True) -> Dict[str, str]:
        if use_label:
            return {field.label: self.get(field) for field in MovieField if self.get(field)}
        else:
            return {field.key: self.get(field) for field in MovieField if self.get(field)}

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'MovieInfo':
        instance = cls()
        for key, value in data.items():
            try:
                field = MovieField.get_by_label(key)
                instance.set(field, value)
            except ValueError:
                try:
                    field = MovieField.get_by_key(key)
                    instance.set(field, value)
                except ValueError:
                    pass
        return instance

    @classmethod
    def get_available_fields(cls) -> List[MovieField]:
        return list(MovieField)

    @classmethod
    def get_available_labels(cls) -> List[str]:
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
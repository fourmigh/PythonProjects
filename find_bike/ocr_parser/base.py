# ocr_parser/base.py
# ============================================================
# OCR解析器基类
# ============================================================

from abc import ABC, abstractmethod
from typing import Tuple, Set, List


class BaseOCRParser(ABC):
    """OCR解析器基类"""
    
    @abstractmethod
    def parse(self, answer: str) -> Tuple[bool, str]:
        """
        解析OCR模型返回结果
        
        Args:
            answer: 模型的原始回答文本
            
        Returns:
            Tuple[bool, str]: (是否允许, 原始回答)
            - True: 允许（无牌照）
            - False: 不允许（有牌照）
        """
        pass
    
    @abstractmethod
    def add_negative_keyword(self, keyword: str):
        """添加黑名单关键词"""
        pass
    
    @abstractmethod
    def add_valid_plate_code(self, code: str):
        """添加有效的三位纯数字车牌"""
        pass
    
    @abstractmethod
    def get_statistics(self, results: List[Tuple[str, bool, bool]]) -> dict:
        """统计解析结果"""
        pass
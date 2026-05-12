# ocr_parser/__init__.py
# ============================================================
# OCR解析模块 - 统一导出入口
# ============================================================

from typing import Tuple
from .base import BaseOCRParser
from .glm_ocr_parser import GLMOCRParser


_default_parser = None


def get_parser() -> BaseOCRParser:
    """获取默认的OCR解析器实例"""
    global _default_parser
    if _default_parser is None:
        _default_parser = GLMOCRParser()
    return _default_parser


def parse_ocr_result(answer: str) -> Tuple[bool, str]:
    """
    解析OCR模型结果（快捷函数）
    
    Args:
        answer: 模型的原始回答文本
        
    Returns:
        Tuple[bool, str]: (是否允许, 原始回答)
        - True: 允许（无牌照）
        - False: 不允许（有牌照）
    """
    parser = get_parser()
    return parser.parse(answer)


def set_parser(parser: BaseOCRParser):
    """设置自定义解析器"""
    global _default_parser
    _default_parser = parser


__all__ = [
    'BaseOCRParser',
    'GLMOCRParser',
    'parse_ocr_result',
    'get_parser',
    'set_parser'
]
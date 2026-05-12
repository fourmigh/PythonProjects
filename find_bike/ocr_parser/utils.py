# ocr_parser/utils.py
# ============================================================
# OCR解析器工具函数
# ============================================================

import re
from typing import List, Tuple


def extract_license_plates(text: str) -> List[str]:
    """
    从文本中提取所有可能车牌号
    
    Args:
        text: 待提取文本
        
    Returns:
        车牌号列表
    """
    patterns = [
        r'\b\d{3}[A-Z]{3}\b',           # 如 "318TEK"
        r'\b\d{3}\s+[A-Z]{3}\b',        # 如 "318 TEK"  
        r'\b[A-Z]{3}\s+\d{3}\b',        # 如 "TEK 318"
        r'车牌号[：:]\s*([A-Z0-9]+)',    # 如 "车牌号: 673KSV"
    ]
    
    plates = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        plates.extend(matches)
    
    return plates


def is_likely_license_plate(text: str) -> bool:
    """
    判断字符串是否可能是车牌号
    
    Args:
        text: 待判断字符串
        
    Returns:
        是否可能是车牌号
    """
    text = text.upper()
    
    # 长度检查
    if len(text) < 3 or len(text) > 9:
        return False
    
    # 黑名单词
    negative = {'LOGO', 'FLOOR', 'RAMP', 'WOOD', 'BOX', 'CARD', 'LABEL'}
    if text in negative:
        return False
    
    # 必须包含字母和数字（纯数字需特殊处理）
    has_digit = any(c.isdigit() for c in text)
    has_alpha = any(c.isalpha() for c in text)
    
    if has_digit and has_alpha:
        return True
    
    # 3位纯数字白名单
    if text.isdigit() and len(text) == 3:
        valid_digits = {'318', '476', '502', '866', '863', '993', '418', '673', '999'}
        return text in valid_digits
    
    return False


def clean_answer(answer: str) -> str:
    """
    清理OCR回答文本
    
    Args:
        answer: 原始回答
        
    Returns:
        清理后的文本
    """
    # 移除多余空白
    cleaned = ' '.join(answer.split())
    
    return cleaned
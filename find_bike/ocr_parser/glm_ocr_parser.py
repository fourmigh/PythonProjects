# ocr_parser/glm_ocr_parser.py
# ============================================================
# GLM-OCR 模型结果解析器
# 专门用于解析智谱 glm-ocr 模型的返回结果
# ============================================================

import re
from typing import Tuple, Set, List

from .base import BaseOCRParser
from .config import (
    NEGATIVE_KEYWORDS,
    VALID_SHORT_DIGITS,
    LICENSE_PATTERNS,
    NON_BICYCLE_KEYWORDS,
    ELECTRIC_BIKE_KEYWORDS,
    BICYCLE_KEYWORDS,
    NEGATIVE_PHRASES,
    POSITIVE_PHRASES
)


class GLMOCRParser(BaseOCRParser):
    """GLM-OCR 模型结果解析器"""
    
    def __init__(self):
        # 从配置文件加载
        self.negative_keywords: Set[str] = NEGATIVE_KEYWORDS.copy()
        self.valid_short_digits: Set[str] = VALID_SHORT_DIGITS.copy()
        self.license_patterns: List[str] = LICENSE_PATTERNS.copy()
        self.non_bicycle_keywords: Set[str] = NON_BICYCLE_KEYWORDS.copy()
        self.electric_bike_keywords: Set[str] = ELECTRIC_BIKE_KEYWORDS.copy()
        self.bicycle_keywords: Set[str] = BICYCLE_KEYWORDS.copy()
        self.negative_phrases: List[str] = NEGATIVE_PHRASES.copy()
        self.positive_phrases: List[str] = POSITIVE_PHRASES.copy()
    
    def parse(self, answer: str) -> Tuple[bool, str]:
        """
        解析 OCR 模型返回结果
        
        Args:
            answer: 模型的原始回答文本
            
        Returns:
            Tuple[bool, str]: (是否允许, 原始回答)
            - True: 允许（有自行车且无牌照）
            - False: 不允许（无自行车或有牌照）
        """
        answer_upper = answer.upper()
        answer_lower = answer.lower()
        
        # 1. 检查是否为机动车（汽车/摩托车）
        if self._is_motor_vehicle(answer_lower):
            print(f"  [OCR解析] 检测到机动车（汽车/摩托车）-> 返回 False (不允许)")
            return False, answer
        
        # 2. 检查是否为电动车（业务规则：电动车不符合要求）
        if self._is_electric_bike(answer_lower):
            print(f"  [OCR解析] 检测到电动车 -> 返回 False (不允许)")
            return False, answer
        
        # 3. 检查是否有自行车关键词
        if not self._has_bicycle(answer_lower):
            print(f"  [OCR解析] 未检测到自行车 -> 返回 False (不允许)")
            return False, answer
        
        # 4. 检查是否有"有牌照"等明确关键词
        if self._has_clear_positive(answer):
            found_plates = self._extract_valid_plates(answer_upper)
            if found_plates:
                print(f"  [OCR解析] 明确有牌照且检测到车牌: {', '.join(found_plates)} -> 返回 False (不允许)")
                return False, answer
            else:
                print(f"  [OCR解析] 明确有牌照 -> 返回 False (不允许)")
                return False, answer
        
        # 5. 提取并验证车牌
        found_plates = self._extract_valid_plates(answer_upper)
        
        if found_plates:
            print(f"  [OCR解析] 检测到有效车牌: {', '.join(found_plates)} -> 返回 False (不允许)")
            return False, answer
        
        # 6. 检查是否有明确的否定词
        if self._has_clear_negative(answer_lower):
            print(f"  [OCR解析] 明确无牌照 -> 返回 True (允许)")
            return True, answer
        
        # 7. 默认：无车牌
        print(f"  [OCR解析] 未检测到有效车牌 -> 返回 True (允许)")
        return True, answer
    
    def _is_motor_vehicle(self, answer_lower: str) -> bool:
        """检查是否为机动车（汽车、摩托车等）"""
        for keyword in self.non_bicycle_keywords:
            if keyword in answer_lower:
                return True
        return False
    
    def _is_electric_bike(self, answer_lower: str) -> bool:
        """检查是否为电动车"""
        for keyword in self.electric_bike_keywords:
            if keyword in answer_lower:
                return True
        return False
    
    def _has_bicycle(self, answer_lower: str) -> bool:
        """检查是否有自行车关键词"""
        for keyword in self.bicycle_keywords:
            if keyword in answer_lower:
                return True
        return False
    
    def _has_clear_negative(self, answer_lower: str) -> bool:
        """检查是否有明确的否定词"""
        for phrase in self.negative_phrases:
            if phrase in answer_lower:
                return True
        return False
    
    def _has_clear_positive(self, answer: str) -> bool:
        """检查是否有明确的肯定词"""
        for phrase in self.positive_phrases:
            if phrase in answer:
                return True
        return False
    
    def _extract_valid_plates(self, text_upper: str) -> Set[str]:
        """从文本中提取并验证有效的车牌"""
        found_plates = set()
        
        for pattern in self.license_patterns:
            matches = re.findall(pattern, text_upper)
            for match in matches:
                if isinstance(match, tuple):
                    plate_candidate = ''.join(match)
                    plate_with_space = f"{match[0]} {match[1]}"
                else:
                    plate_candidate = match
                    plate_with_space = match
                
                if self._is_valid_plate(plate_candidate):
                    found_plates.add(plate_candidate)
                    found_plates.add(plate_with_space)
        
        return found_plates
    
    def _is_valid_plate(self, candidate: str) -> bool:
        """验证候选字符串是否为有效车牌"""
        if len(candidate) < 3 or len(candidate) > 9:
            return False
        
        if candidate in self.negative_keywords:
            return False
        
        # 纯数字情况
        if candidate.isdigit():
            if len(candidate) == 3 and candidate in self.valid_short_digits:
                return True
            if len(candidate) == 4 and int(candidate) > 1900:
                return False
            return False
        
        # 纯字母情况
        if candidate.isalpha():
            if 3 <= len(candidate) <= 6 and candidate not in self.negative_keywords:
                return True
            return False
        
        # 字母+数字混合
        has_digit = any(c.isdigit() for c in candidate)
        has_alpha = any(c.isalpha() for c in candidate)
        if has_digit and has_alpha:
            return True
        
        return False
    
    # ============================================================
    # 动态添加方法（运行时修改配置）
    # ============================================================
    
    def add_negative_keyword(self, keyword: str):
        """添加黑名单关键词"""
        self.negative_keywords.add(keyword.upper())
    
    def add_valid_plate_code(self, code: str):
        """添加有效的三位纯数字车牌"""
        self.valid_short_digits.add(code)
    
    def add_non_bicycle_keyword(self, keyword: str):
        """添加非机动车关键词"""
        self.non_bicycle_keywords.add(keyword.lower())
    
    def add_electric_bike_keyword(self, keyword: str):
        """添加电动车关键词"""
        self.electric_bike_keywords.add(keyword.lower())
    
    def add_bicycle_keyword(self, keyword: str):
        """添加自行车关键词"""
        self.bicycle_keywords.add(keyword.lower())
    
    def add_negative_phrase(self, phrase: str):
        """添加无牌照短语"""
        self.negative_phrases.append(phrase.lower())
    
    def add_positive_phrase(self, phrase: str):
        """添加有牌照短语"""
        self.positive_phrases.append(phrase)
    
    def get_statistics(self, results: List[Tuple[str, bool, bool]]) -> dict:
        """统计解析结果"""
        total = len(results)
        correct = sum(1 for _, parsed, expected in results if parsed == expected)
        
        false_positive = []
        false_negative = []
        
        for name, parsed, expected in results:
            if parsed != expected:
                if expected is True:
                    false_negative.append(name)
                else:
                    false_positive.append(name)
        
        return {
            'total': total,
            'correct': correct,
            'accuracy': correct / total * 100 if total > 0 else 0,
            'false_positive': false_positive,
            'false_negative': false_negative,
            'false_positive_count': len(false_positive),
            'false_negative_count': len(false_negative)
        }


# 测试代码
if __name__ == "__main__":
    parser = GLMOCRParser()
    
    test_cases = [
        ("318 TEK", False),
        ("一辆蓝色的共享单车停在路边", True),
        ("车牌号是673KSV", False),
        ("2026.04.17 13:48", True),
        ("图片中是一辆黄色的小车，车身黄色", True),  # 小车应识别为自行车
        ("一辆电动车停在路边", False),  # 电动车 -> 不允许
        ("一辆摩托车驶过", False),  # 摩托车 -> 不允许
    ]
    
    print("=" * 60)
    print("GLM-OCR 解析器测试")
    print("=" * 60)
    
    for text, expected in test_cases:
        result, _ = parser.parse(text)
        status = "✓" if result == expected else "✗"
        expected_str = "不允许" if not expected else "允许"
        result_str = "不允许" if not result else "允许"
        print(f"{status} 期望: {expected_str}, 结果: {result_str}")
        print(f"   文本: {text[:80]}")
# utils.py
from typing import List


def calculate_bitmap(slots: List[int]) -> int:
    """计算时段位图"""
    if not slots:
        return 0
    start = slots[0]
    end = slots[-1]
    return ((1 << (end - start + 1)) - 1) << start


def has_overlap(slots1: List[int], slots2: List[int]) -> bool:
    """检查两个时段是否有重叠"""
    return not (slots1[-1] < slots2[0] or slots2[-1] < slots1[0])
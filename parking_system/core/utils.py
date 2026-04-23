# utils.py
from typing import List, Set, Tuple
from collections import defaultdict


def get_conflict_range(user_slots: List[int], occupant_slots: List[int]) -> str:
    """获取用户与占用者之间的时段冲突范围"""
    user_start = user_slots[0]
    user_end = user_slots[-1]
    occ_start = occupant_slots[0]
    occ_end = occupant_slots[-1]
    
    conflict_start = max(user_start, occ_start)
    conflict_end = min(user_end, occ_end)
    
    if conflict_start <= conflict_end:
        if conflict_start == conflict_end:
            return f" [冲突时段:{conflict_start}]"
        else:
            return f" [冲突时段:{conflict_start}-{conflict_end}]"
    return ""


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


def format_slots(slots: List[int], num_slots: int, get_time_range_func=None) -> str:
    """格式化时段显示"""
    if len(slots) == 1:
        if get_time_range_func:
            return f"时段 {slots[0]} ({get_time_range_func(slots[0]-1)})"
        return f"时段 {slots[0]}"
    else:
        if get_time_range_func:
            return f"时段 {slots[0]}-{slots[-1]} ({get_time_range_func(slots[0]-1)} 到 {get_time_range_func(slots[-1]-1)})"
        return f"时段 {slots[0]}-{slots[-1]}"
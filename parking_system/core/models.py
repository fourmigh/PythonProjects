# models.py
from typing import List, Optional
from dataclasses import dataclass, field
from enum import Enum


class UserStatus(Enum):
    BOOKED = "booked"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    OVERTIME = "overtime"


@dataclass
class User:
    """用户信息数据类"""
    id: int
    slots: List[int]
    spot_assigned: Optional[int] = None
    checked_in: bool = False
    checked_out: bool = False
    checkin_time: Optional[int] = None
    checkout_time: Optional[int] = None
    overtime: bool = False
    overtime_start: Optional[int] = None
    actual_end_slot: Optional[int] = None  # 实际结束时段（超时时使用）


@dataclass
class TimeSlotStatus:
    """时段状态数据类"""
    slot_index: int
    booked_count: int
    actual_count: int
    capacity: int
    is_past: bool = False
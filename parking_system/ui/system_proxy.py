"""停车场系统代理（单例模式）"""

import sys
import os
from typing import List, Tuple, Dict, Optional
from collections import defaultdict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.parking_system import ParkingSystem
from core.models import User, TimeSlotStatus


class ParkingSystemProxy:
    """停车场系统代理（单例模式）"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._system = None
        self.total_spots = None
        self.num_slots = None
        self.minutes_per_slot = None
        self._initialized = True
        
        # 回调函数列表（用于通知UI刷新）
        self._refresh_callbacks = []
    
    def init_system(self, total_spots: int, num_slots: int):
        """初始化系统"""
        self.total_spots = total_spots
        self.num_slots = num_slots
        self.minutes_per_slot = 24 * 60 // num_slots
        self._system = ParkingSystem(total_spots, num_slots)
    
    def register_refresh_callback(self, callback):
        """注册刷新回调函数"""
        if callback not in self._refresh_callbacks:
            self._refresh_callbacks.append(callback)
    
    def unregister_refresh_callback(self, callback):
        """注销刷新回调函数"""
        if callback in self._refresh_callbacks:
            self._refresh_callbacks.remove(callback)
    
    def _notify_refresh(self):
        """通知所有注册的回调刷新UI"""
        for callback in self._refresh_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"刷新回调执行失败: {e}")
    
    # ========== 代理方法 ==========
    
    @property
    def system(self):
        """获取底层系统实例"""
        return self._system
    
    @property
    def users(self) -> Dict[int, User]:
        """获取所有用户"""
        return self._system.users if self._system else {}
    
    @property
    def spot_schedule(self) -> defaultdict:
        """获取车位时间表"""
        return self._system.spot_schedule if self._system else defaultdict(dict)
    
    @property
    def time_point(self) -> int:
        """获取当前时间点"""
        return self._system.time_point if self._system else 0
    
    @property
    def next_user_id(self) -> int:
        """获取下一个用户ID"""
        return self._system.next_user_id if self._system else 1
    
    @property
    def total_time_points(self) -> int:
        """获取总时间点数量"""
        return self.num_slots * 2 if self.num_slots else 0
    
    def get_slot_status(self, slot: int) -> TimeSlotStatus:
        """获取时段状态"""
        if self._system:
            return self._system.get_slot_status(slot)
        return TimeSlotStatus(slot_index=slot, booked_count=0, actual_count=0, capacity=0)
    
    def get_all_users(self) -> List[User]:
        """获取所有用户"""
        return self._system.get_all_users() if self._system else []
    
    def book(self, user_id: int, slots: List[int]) -> Tuple[bool, str]:
        """预订车位"""
        if not self._system:
            return False, "系统未初始化"
        result = self._system.book(user_id, slots)
        self._notify_refresh()
        return result
    
    def arrive_smart(self, user_id: int, time_slot: int) -> Tuple[bool, str]:
        """用户到达（智能分配）"""
        if not self._system:
            return False, "系统未初始化"
        result = self._system.arrive_smart(user_id, time_slot)
        self._notify_refresh()
        return result
    
    def depart(self, user_id: int, time_slot: int, overtime: bool = False) -> Tuple[bool, str]:
        """用户离开"""
        if not self._system:
            return False, "系统未初始化"
        result = self._system.depart(user_id, time_slot, overtime)
        self._notify_refresh()
        return result
    
    def advance_time(self, new_time_point: int) -> None:
        """前进时间"""
        if self._system:
            self._system.advance_time(new_time_point)
            self._notify_refresh()
    
    def reset(self) -> None:
        """重置系统"""
        if self._system:
            self._system.reset()
            self._notify_refresh()
    
    def get_current_slot(self) -> int:
        """获取当前时间对应的时段编号（基于真实时间）"""
        from datetime import datetime
        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute
        slot = current_minutes // self.minutes_per_slot + 1 if self.minutes_per_slot else 1
        if slot < 1:
            slot = 1
        if slot > self.num_slots:
            slot = self.num_slots + 1
        return slot
    
    def get_time_range(self, slot_index: int) -> str:
        """获取时间段的起止时间字符串"""
        if self.minutes_per_slot is None:
            return ""
        start_minutes = slot_index * self.minutes_per_slot
        end_minutes = (slot_index + 1) * self.minutes_per_slot
        start_hour = start_minutes // 60
        start_min = start_minutes % 60
        end_hour = end_minutes // 60
        end_min = end_minutes % 60
        return f"{start_hour:02d}:{start_min:02d}-{end_hour:02d}:{end_min:02d}"
    
    def get_time_point_description(self) -> str:
        """获取当前时间点的描述"""
        if self.time_point >= self.total_time_points:
            return "所有时段已结束"
        
        slot_index = self.time_point // 2
        is_start = (self.time_point % 2 == 0)
        
        if is_start:
            return f"时段 {slot_index + 1} 开始前 ({self.get_time_range(slot_index)})"
        else:
            return f"时段 {slot_index + 1} 结束后 ({self.get_time_range(slot_index)})"


# 全局单例实例
system_proxy = ParkingSystemProxy()
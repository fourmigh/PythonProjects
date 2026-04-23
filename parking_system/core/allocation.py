# allocation.py
from typing import List, Tuple, Set, Dict, Optional
from collections import defaultdict
import time

from .config import AllocationWeights
from .models import User
from .utils import calculate_bitmap, has_overlap


class AllocationManager:
    """车位分配管理器"""
    
    def __init__(self, total_spots: int, num_slots: int, 
                 spot_schedule: defaultdict, spot_bitmap: dict,
                 users: Dict[int, User], time_point: int):
        self.total_spots = total_spots
        self.num_slots = num_slots
        self.spot_schedule = spot_schedule
        self.spot_bitmap = spot_bitmap
        self.users = users
        self.time_point = time_point
    
    def _update_spot_bitmap(self, spot: int):
        """更新车位的占用位图"""
        bitmap = 0
        for slot, _ in self.spot_schedule[spot].items():
            bitmap |= (1 << (slot + 1))
        self.spot_bitmap[spot] = bitmap
    
    def _get_spot_bitmap(self, spot: int) -> int:
        """获取车位位图，带缓存"""
        if spot not in self.spot_bitmap:
            self._update_spot_bitmap(spot)
        return self.spot_bitmap.get(spot, 0)
    
    def _get_future_users(self, current_time_slot: int) -> List[User]:
        """获取所有未到达的未来用户"""
        future_users = []
        for user in self.users.values():
            if not user.checked_in and not user.checked_out:
                if user.slots[0] > current_time_slot + 1:
                    future_users.append(user)
        future_users.sort(key=lambda u: u.slots[0])
        return future_users
    
    def _get_conflicting_future_users(self, current_user: User, current_time_slot: int) -> List[User]:
        """获取与当前用户有时段重叠的未来用户"""
        current_start = current_user.slots[0]
        current_end = current_user.slots[-1]
        
        conflicting_users = []
        for user in self.users.values():
            if not user.checked_in and not user.checked_out:
                if user.slots[0] > current_time_slot + 1:
                    if has_overlap([current_start, current_end], user.slots):
                        conflicting_users.append(user)
        
        conflicting_users.sort(key=lambda u: u.slots[0])
        return conflicting_users
    
    def _can_fulfill_future_users(self, occupied_spots: Set[int], 
                                   allocated_spot: int, 
                                   current_user: User,
                                   current_time_slot: int) -> bool:
        """检查分配后未来用户是否都能找到位置"""
        if AllocationWeights.FAST_CHECK_MODE:
            remaining_free = self.total_spots - len(occupied_spots) - 1
            if remaining_free >= 5:
                return True
        
        if AllocationWeights.CHECK_ONLY_CONFLICTING_FUTURE_USERS:
            future_users = self._get_conflicting_future_users(current_user, current_time_slot)
        else:
            future_users = self._get_future_users(current_time_slot)
        
        if not future_users:
            return True
        
        if len(future_users) > AllocationWeights.MAX_FUTURE_USERS_CHECK:
            future_users = future_users[:AllocationWeights.MAX_FUTURE_USERS_CHECK]
        
        temp_bitmaps = self.spot_bitmap.copy()
        current_bitmap = calculate_bitmap(current_user.slots)
        temp_bitmaps[allocated_spot] = temp_bitmaps.get(allocated_spot, 0) | current_bitmap
        
        temp_occupied_spots = set(occupied_spots)
        temp_occupied_spots.add(allocated_spot)
        
        for future_user in future_users:
            future_bitmap = calculate_bitmap(future_user.slots)
            found_spot = None
            
            for spot in range(1, self.total_spots + 1):
                if spot in temp_occupied_spots:
                    continue
                if (temp_bitmaps.get(spot, 0) & future_bitmap) != 0:
                    continue
                found_spot = spot
                break
            
            if found_spot is None:
                return False
            
            temp_bitmaps[found_spot] = temp_bitmaps.get(found_spot, 0) | future_bitmap
            temp_occupied_spots.add(found_spot)
        
        return True
    
    def _calculate_spot_score(self, spot: int, user: User, time_slot: int) -> int:
        """计算车位的分配得分"""
        current_start = user.slots[0]
        current_end = user.slots[-1]
        current_duration = len(user.slots)
        user_bitmap = calculate_bitmap(user.slots)
        spot_bitmap = self._get_spot_bitmap(spot)
        
        # 车位连续性
        left_free = True
        if spot > 1:
            left_bitmap = self._get_spot_bitmap(spot - 1)
            if (left_bitmap & user_bitmap) != 0:
                left_free = False
        
        right_free = True
        if spot < self.total_spots:
            right_bitmap = self._get_spot_bitmap(spot + 1)
            if (right_bitmap & user_bitmap) != 0:
                right_free = False
        
        is_corner = (spot == 1 or spot == self.total_spots)
        
        score = 0
        if left_free and right_free:
            score += AllocationWeights.CONTINUOUS_BOTH_SIDES
        elif left_free or right_free:
            score += AllocationWeights.CONTINUOUS_ONE_SIDE
        
        # 到达紧迫性
        urgency = current_start - time_slot - 1
        if urgency == 0:
            score += AllocationWeights.URGENCY_IMMEDIATE
        elif urgency == 1:
            score += AllocationWeights.URGENCY_NEXT
        elif urgency == 2:
            score += AllocationWeights.URGENCY_2ND_NEXT
        
        # 时长匹配
        if current_duration >= self.num_slots * 0.7:
            future_free = 0
            for slot in range(current_end + 1, 
                             min(current_end + AllocationWeights.MAX_CHECK_SLOTS, 
                                 self.num_slots + 1)):
                if ((spot_bitmap >> slot) & 1) == 0:
                    future_free += 1
                else:
                    break
            score += (AllocationWeights.LONG_TERM_FUTURE_FREE_BASE + 
                     future_free * AllocationWeights.LONG_TERM_FUTURE_FREE_PER_SLOT)
        elif current_duration <= 2 and is_corner:
            score += AllocationWeights.SHORT_TERM_CORNER_BONUS
        
        # 当前空闲
        if (spot_bitmap & user_bitmap) == 0:
            score += AllocationWeights.CURRENT_FREE_BONUS
        
        # 超时风险
        if AllocationWeights.CONSIDER_OVERTIME:
            extended_end = current_end + AllocationWeights.OVERTIME_EXTEND_SLOTS
            if extended_end <= self.num_slots:
                extended_bit = 1 << extended_end
                if (spot_bitmap & extended_bit) != 0:
                    score -= AllocationWeights.OVERTIME_RISK_PENALTY
        
        return score
    
    def allocate_smart(self, user: User, time_slot: int, 
                       occupied_spots: Set[int], free_spots: List[int]) -> Tuple[Optional[int], str]:
        """智能分配算法"""
        # 获取未来订单的位图列表
        current_start = user.slots[0]
        current_end = user.slots[-1]
        future_bitmaps = self._get_future_bitmaps_optimized(
            current_start, current_end, time_slot
        )
        
        best_score = -float('inf')
        best_spot = None
        
        # 候选车位列表（优先考虑空闲车位）
        candidate_spots = free_spots
        
        for spot in candidate_spots:
            spot_bitmap = self._get_spot_bitmap(spot)
            
            # 快速冲突检查
            conflict = False
            for fb in future_bitmaps:
                if (spot_bitmap & fb) != 0:
                    conflict = True
                    break
            
            if conflict:
                continue
            
            # 检查未来用户是否能被满足
            if not self._can_fulfill_future_users(occupied_spots, spot, user, time_slot):
                continue
            
            score = self._calculate_spot_score(spot, user, time_slot)
            
            if score > best_score:
                best_score = score
                best_spot = spot
            elif score == best_score and best_spot is not None and spot < best_spot:
                best_spot = spot
        
        # 修复降级逻辑：如果没找到，尝试不检查未来用户冲突的分配
        if best_spot is None:
            # 降级：只检查冲突，不检查未来用户是否都能满足
            for spot in candidate_spots:
                spot_bitmap = self._get_spot_bitmap(spot)
                
                # 只检查快速冲突
                conflict = False
                for fb in future_bitmaps:
                    if (spot_bitmap & fb) != 0:
                        conflict = True
                        break
                
                if conflict:
                    continue
                
                # 不检查 _can_fulfill_future_users
                score = self._calculate_spot_score(spot, user, time_slot)
                
                if score > best_score:
                    best_score = score
                    best_spot = spot
        
        # 最终降级：只要空闲就分配
        if best_spot is None and free_spots:
            best_spot = free_spots[0]
            return best_spot, ""
        
        if best_spot is None:
            return None, "没有合适的车位"
        
        return best_spot, ""
    
    def _get_future_bitmaps_optimized(self, current_start: int, current_end: int, 
                                       current_time: int) -> List[int]:
        """获取未来订单位图"""
        future_bitmaps = []
        check_end = current_end + AllocationWeights.OVERTIME_EXTEND_SLOTS if AllocationWeights.CONSIDER_OVERTIME else current_end
        
        for user in self.users.values():
            if not user.checked_in and not user.checked_out:
                if user.slots[0] > current_time + 1:
                    if user.slots[0] > check_end:
                        continue
                    
                    overlap_start = max(current_start, user.slots[0])
                    overlap_end = min(check_end, user.slots[-1])
                    
                    if overlap_start <= overlap_end:
                        bitmap = ((1 << (overlap_end - overlap_start + 1)) - 1) << overlap_start
                        future_bitmaps.append(bitmap)
                        
                        if len(future_bitmaps) >= AllocationWeights.MAX_FUTURE_ORDERS:
                            break
        
        return future_bitmaps
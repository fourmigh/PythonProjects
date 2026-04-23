# parking_system.py
from typing import List, Tuple, Dict, Optional, Set
from collections import defaultdict
import time

from .config import AllocationWeights
from .models import User, TimeSlotStatus
from .allocation import AllocationManager
from .utils import get_conflict_range, calculate_bitmap, format_slots


class ParkingSystem:
    """停车系统主类"""
    
    # 性能统计
    _perf_stats = defaultdict(lambda: {'count': 0, 'total_time': 0})
    
    @classmethod
    def reset_perf_stats(cls):
        cls._perf_stats.clear()
    
    @classmethod
    def print_perf_stats(cls):
        print("\n" + "="*80)
        print("性能分析报告")
        print("="*80)
        print(f"{'函数名':<45} {'调用次数':<12} {'总耗时(秒)':<15} {'平均耗时(毫秒)':<15}")
        print("-"*80)
        
        sorted_stats = sorted(cls._perf_stats.items(), key=lambda x: x[1]['total_time'], reverse=True)
        for func_name, stats in sorted_stats:
            avg_ms = stats['total_time'] / stats['count'] * 1000
            print(f"{func_name:<45} {stats['count']:<12} {stats['total_time']:<15.3f} {avg_ms:<15.3f}")
        print("="*80)
    
    def _profile(func):
        def wrapper(self, *args, **kwargs):
            start = time.time()
            result = func(self, *args, **kwargs)
            elapsed = time.time() - start
            ParkingSystem._perf_stats[func.__name__]['count'] += 1
            ParkingSystem._perf_stats[func.__name__]['total_time'] += elapsed
            return result
        return wrapper
    
    def __init__(self, total_spots: int, num_slots: int):
        self.total_spots = total_spots
        self.num_slots = num_slots
        self.slot_duration = 24 * 60 // num_slots
        self.occupied = [0] * num_slots
        self.users: Dict[int, User] = {}
        self.next_user_id = 1
        self.spot_schedule = defaultdict(dict)
        self.spot_bitmap = {}
        self.time_point = 0
        self.allocation_manager = None
    
    def _init_allocation_manager(self):
        """初始化分配管理器"""
        if self.allocation_manager is None:
            self.allocation_manager = AllocationManager(
                self.total_spots, self.num_slots,
                self.spot_schedule, self.spot_bitmap,
                self.users, self.time_point
            )
    
    def _update_spot_bitmap(self, spot: int):
        bitmap = 0
        for slot, _ in self.spot_schedule[spot].items():
            bitmap |= (1 << (slot + 1))
        self.spot_bitmap[spot] = bitmap
    
    def _check_slots_availability(self, slots: List[int]) -> Tuple[bool, str, Optional[List[int]]]:
        past_slots = self.time_point // 2
        for slot in slots:
            if slot <= past_slots:
                return False, f"时段{slot}已过去", None
        
        for slot in slots:
            idx = slot - 1
            if self.occupied[idx] >= self.total_spots:
                return False, f"时段{slot}已满", None
        
        common_free = set(range(1, self.total_spots + 1))
        for slot in slots:
            occupied = set()
            for spot in range(1, self.total_spots + 1):
                if slot-1 in self.spot_schedule[spot]:
                    occupied.add(spot)
            common_free -= occupied
        
        if common_free:
            return True, "可用", sorted(common_free)
        
        conflict_count = {}
        for spot in range(1, self.total_spots + 1):
            conflict_count[spot] = 0
            for slot in slots:
                if slot-1 in self.spot_schedule[spot]:
                    conflict_count[spot] += 1
        
        min_conflict = min(conflict_count.values())
        best_spots = [spot for spot, count in conflict_count.items() if count == min_conflict]
        
        return False, f"没有连续的空闲车位满足时段{slots[0]}-{slots[-1]}的需求", best_spots[:5]
    
    @_profile
    def book(self, user_id: int, slots: List[int]) -> Tuple[bool, str]:
        for i in range(len(slots)-1):
            if slots[i+1] != slots[i] + 1:
                return False, "时段必须连续"
        
        past_slots = self.time_point // 2
        for slot in slots:
            if slot <= past_slots:
                return False, f"时段{slot}已过去"
        
        available, msg, recommended_spots = self._check_slots_availability(slots)
        if not available:
            if recommended_spots:
                msg += f" (推荐车位: {recommended_spots})"
            return False, msg
        
        for slot in slots:
            self.occupied[slot-1] += 1
        
        user = User(id=user_id, slots=slots)
        self.users[user_id] = user
        self.next_user_id = max(self.next_user_id, user_id + 1)
        
        return True, "预订成功"
    
    @_profile
    def check_availability(self, slots: List[int]) -> Tuple[bool, str]:
        for slot in slots:
            idx = slot - 1
            if self.occupied[idx] >= self.total_spots:
                return False, f"时段{slot}已满"
        return True, "可用"
    
    @_profile
    def get_available_slots(self) -> List[List[int]]:
        available = []
        past_slots = self.time_point // 2
        
        for i in range(1, self.num_slots + 1):
            if i <= past_slots:
                continue
            if self.occupied[i-1] < self.total_spots:
                available.append([i])
        
        for length in range(2, self.num_slots + 1):
            for start in range(1, self.num_slots - length + 2):
                slots = list(range(start, start + length))
                if any(s <= past_slots for s in slots):
                    continue
                if all(self.occupied[s-1] < self.total_spots for s in slots):
                    available.append(slots)
        
        return available
    
    @_profile
    def arrive(self, user_id: int, time_slot: int) -> Tuple[bool, str]:
        """用户到达 - 简单分配算法"""
        if user_id not in self.users:
            return False, "用户不存在"
        
        user = self.users[user_id]
        if user.checked_in:
            return False, "用户已到达"
        
        if user.checked_out:
            return False, "用户已离开"
        
        expected_slot = user.slots[0]
        if time_slot + 1 != expected_slot:
            return False, f"用户应在时段{expected_slot}到达"
        
        occupied_spots = set()
        for u in self.users.values():
            if u.checked_in and not u.checked_out and u.spot_assigned:
                occupied_spots.add(u.spot_assigned)
        
        free_spots = [s for s in range(1, self.total_spots + 1) 
                     if s not in occupied_spots]
        
        if not free_spots:
            # 详细分析无空闲车位的原因
            overtime_users = [u for u in self.users.values() if u.checked_in and not u.checked_out and u.overtime and u.spot_assigned]
            normal_users = [u for u in self.users.values() if u.checked_in and not u.checked_out and not u.overtime and u.spot_assigned]
            reason = self._analyze_no_free_spots(user, occupied_spots, overtime_users, normal_users, time_slot)
            return False, reason
        
        # 选择一个不影响未来用户的空闲车位
        self._init_allocation_manager()
        best_spot = None
        for spot in free_spots:
            if self.allocation_manager._can_fulfill_future_users(occupied_spots, spot, user, time_slot):
                best_spot = spot
                break
        
        if best_spot is None:
            return False, "没有合适的车位（分配后会导致未来用户无位置）"
        
        user.spot_assigned = best_spot
        user.checked_in = True
        user.checkin_time = time_slot
        
        for slot in user.slots:
            self.spot_schedule[best_spot][slot-1] = user.id
        
        self._update_spot_bitmap(best_spot)
        
        # ========== 新增：到达成功后减少 occupied 计数 ==========
        for slot in user.slots:
            if self.occupied[slot-1] > 0:
                self.occupied[slot-1] -= 1
        # ====================================================
        
        return True, f"分配车位{best_spot}"
    
    @_profile
    def arrive_smart(self, user_id: int, time_slot: int) -> Tuple[bool, str]:
        """用户到达 - 智能分配算法"""
        if user_id not in self.users:
            return False, "用户不存在"
        
        user = self.users[user_id]
        if user.checked_in:
            return False, "用户已到达"
        if user.checked_out:
            return False, "用户已离开"
        
        expected_slot = user.slots[0]
        if time_slot + 1 != expected_slot:
            return False, f"用户应在时段{expected_slot}到达"
        
        occupied_spots = set()
        overtime_users = []
        normal_users = []
        
        for u in self.users.values():
            if u.checked_in and not u.checked_out and u.spot_assigned:
                occupied_spots.add(u.spot_assigned)
                if u.overtime:
                    overtime_users.append(u)
                else:
                    normal_users.append(u)
        
        free_spots = [s for s in range(1, self.total_spots + 1) 
                     if s not in occupied_spots]
        
        if not free_spots:
            reason = self._analyze_no_free_spots(user, occupied_spots, overtime_users, normal_users, time_slot)
            return False, reason
        
        # 初始化分配管理器
        self._init_allocation_manager()
        
        # 修复：空闲车位少时也需要智能分配，不能直接取第一个
        # 但可以限制候选车位数量以提升性能
        candidate_spots = free_spots
        if len(free_spots) > AllocationWeights.MAX_CANDIDATE_SPOTS:
            # 如果空闲车位太多，可以只考虑前MAX_CANDIDATE_SPOTS个
            candidate_spots = free_spots[:AllocationWeights.MAX_CANDIDATE_SPOTS]
        
        best_spot, err_msg = self.allocation_manager.allocate_smart(
            user, time_slot, occupied_spots, candidate_spots
        )
        
        if best_spot is None:
            # 降级：尝试所有空闲车位
            best_spot, err_msg = self.allocation_manager.allocate_smart(
                user, time_slot, occupied_spots, free_spots
            )
            if best_spot is None:
                return False, err_msg
        
        user.spot_assigned = best_spot
        user.checked_in = True
        user.checkin_time = time_slot
        
        for slot in user.slots:
            self.spot_schedule[best_spot][slot-1] = user.id
        
        self._update_spot_bitmap(best_spot)
        
        # ========== 新增：到达成功后减少 occupied 计数 ==========
        # 预订时增加了计数，现在实际占用了车位，需要减去预订计数
        # 注意：不能简单减1，因为可能多个用户到达同一时段
        # 但这里每个用户到达时，其预订的每个时段都要减1
        for slot in user.slots:
            if self.occupied[slot-1] > 0:
                self.occupied[slot-1] -= 1
        # ====================================================
        
        return True, f"分配车位{best_spot}"
    
    def _analyze_no_free_spots(self, user, occupied_spots, overtime_users, normal_users, time_slot):
        """分析无空闲车位的原因"""
        total_spots = self.total_spots
        occupied_count = len(occupied_spots)
        overtime_count = len(overtime_users)
        normal_count = len(normal_users)
        
        current_slot_num = time_slot + 1
        current_slot_overtime_occupants = []
        
        # 收集所有超时用户（包括已经超时但还未离开的）
        all_overtime_users = []
        for u in self.users.values():
            if u.checked_in and not u.checked_out and u.spot_assigned:
                if u.overtime:
                    all_overtime_users.append(u)
                # 检查是否预订结束时间已过但未标记超时
                elif u.slots[-1] < current_slot_num:
                    all_overtime_users.append(u)
        
        # 当前时段超时用户
        for u in all_overtime_users:
            # 获取用户实际占用的结束时段
            if u.overtime and hasattr(u, 'actual_end_slot') and u.actual_end_slot is not None:
                actual_end = u.actual_end_slot
            else:
                actual_end = u.slots[-1]
            
            if current_slot_num <= actual_end and current_slot_num >= u.slots[0]:
                current_slot_overtime_occupants.append(u)
        
        user_slots = user.slots
        slot_status = []
        full_slots = []
        for slot in user_slots:
            if slot <= self.time_point // 2:
                slot_status.append(f"时段{slot}(已过去)")
            else:
                booked = self.occupied[slot-1]
                available = self.total_spots - booked
                slot_status.append(f"时段{slot}(预订{booked}/{self.total_spots}, 空余{available})")
                if booked >= self.total_spots:
                    full_slots.append(slot)
        
        # 分析每个车位被谁占用（包括实际占用范围）
        spot_occupancy = {}
        for spot in range(1, self.total_spots + 1):
            occupants = []
            for u in self.users.values():
                if u.checked_in and not u.checked_out and u.spot_assigned == spot:
                    # 获取用户实际占用的结束时段
                    if u.overtime and hasattr(u, 'actual_end_slot') and u.actual_end_slot is not None:
                        actual_end = u.actual_end_slot
                        is_overtime = True
                    else:
                        actual_end = u.slots[-1]
                        is_overtime = u.overtime
                    
                    occupants.append({
                        'id': u.id,
                        'slots': u.slots,
                        'actual_end': actual_end,
                        'is_overtime': is_overtime
                    })
            if occupants:
                spot_occupancy[spot] = occupants
        
        # 分析已满时段被哪些用户占用
        full_slot_analysis = []
        for slot in full_slots:
            slot_occupants = []
            for u in self.users.values():
                if u.checked_in and not u.checked_out and u.spot_assigned:
                    # 获取用户实际占用的结束时段
                    if u.overtime and hasattr(u, 'actual_end_slot') and u.actual_end_slot is not None:
                        actual_end = u.actual_end_slot
                    else:
                        actual_end = u.slots[-1]
                    
                    if slot >= u.slots[0] and slot <= actual_end:
                        slot_occupants.append(u)
            
            if slot_occupants:
                full_slot_analysis.append(f"\n  时段{slot}被以下用户占用:")
                for u in slot_occupants[:10]:
                    # 获取实际占用范围
                    if u.overtime and hasattr(u, 'actual_end_slot') and u.actual_end_slot is not None:
                        occ_end = u.actual_end_slot
                        occ_range = f"{u.slots[0]}-{occ_end}"
                        is_overtime = "超时" if (u.overtime or occ_end > u.slots[-1]) else "正常"
                    else:
                        occ_range = f"{u.slots[0]}-{u.slots[-1]}"
                        is_overtime = "正常"
                    
                    full_slot_analysis.append(f"    用户{u.id}: 车位{u.spot_assigned}, 状态:{is_overtime}, 占用时段{occ_range}")
                if len(slot_occupants) > 10:
                    full_slot_analysis.append(f"    ... 还有{len(slot_occupants)-10}个用户")
            else:
                full_slot_analysis.append(f"\n  时段{slot}已满，但无法确定占用用户")
        
        # 推荐车位
        recommended_spots = self._recommend_spots_for_user(user, time_slot)
        
        reason_parts = []
        reason_parts.append("=" * 70)
        reason_parts.append(f"[失败案例分析] 用户{user.id} 到达失败")
        reason_parts.append("=" * 70)
        reason_parts.append(f"无空闲车位 (总车位:{total_spots}, 已占用:{occupied_count})")
        
        # 显示每个车位的占用情况（使用实际占用范围）
        reason_parts.append(f"\n[车位占用详情]")
        for spot in range(1, self.total_spots + 1):
            if spot in spot_occupancy:
                for occ in spot_occupancy[spot]:
                    status = "超时" if occ['is_overtime'] else "正常"
                    reason_parts.append(f"  车位{spot}: 被用户{occ['id']}({status})占用, 占用时段{occ['slots'][0]}-{occ['actual_end']}")
            else:
                reason_parts.append(f"  车位{spot}: 空闲")
        
        if all_overtime_users:
            reason_parts.append(f"\n[超时用户] 共{len(all_overtime_users)}人:")
            for u in all_overtime_users[:10]:
                if hasattr(u, 'actual_end_slot') and u.actual_end_slot is not None:
                    actual_end = u.actual_end_slot
                else:
                    actual_end = u.slots[-1]
                overtime_duration = current_slot_num - u.slots[-1]
                reason_parts.append(f"  用户{u.id}: 车位{u.spot_assigned}, 超时{overtime_duration}段, 占用时段{u.slots[0]}-{actual_end}")
            if len(all_overtime_users) > 10:
                reason_parts.append(f"  ... 还有{len(all_overtime_users)-10}个超时用户")
        else:
            reason_parts.append(f"\n[超时用户] 无")
        
        if normal_users:
            reason_parts.append(f"\n[正常用户] 共{normal_count}人，占用了{normal_count}个车位")
            for u in normal_users[:10]:
                reason_parts.append(f"  用户{u.id}: 车位{u.spot_assigned}, 占用时段{u.slots[0]}-{u.slots[-1]}")
        
        if current_slot_overtime_occupants:
            reason_parts.append(f"\n[当前时段{current_slot_num}超时用户占用] 共{len(current_slot_overtime_occupants)}人:")
            for u in current_slot_overtime_occupants[:5]:
                if hasattr(u, 'actual_end_slot') and u.actual_end_slot is not None:
                    actual_end = u.actual_end_slot
                else:
                    actual_end = u.slots[-1]
                overtime_duration = current_slot_num - u.slots[-1]
                reason_parts.append(f"  用户{u.id}: 车位{u.spot_assigned}, 超时{overtime_duration}段, 占用时段{u.slots[0]}-{actual_end}")
            if len(current_slot_overtime_occupants) > 5:
                reason_parts.append(f"  ... 还有{len(current_slot_overtime_occupants)-5}个超时用户")
        else:
            reason_parts.append(f"\n[当前时段{current_slot_num}超时用户占用] 无")
        
        reason_parts.append(f"\n[用户{user.id}预订时段] {user.slots}")
        reason_parts.append(f"  各时段预订情况:")
        for status in slot_status:
            reason_parts.append(f"    {status}")
        
        if full_slot_analysis:
            reason_parts.append(f"\n[已满时段分析]")
            for analysis in full_slot_analysis:
                reason_parts.append(analysis)
        
        if recommended_spots:
            for line in recommended_spots:
                reason_parts.append(line)
        else:
            reason_parts.append(f"\n[车位分析] 当前无任何车位能满足用户{user.id}的时段需求")
            reason_parts.append(f"  用户需要连续占用时段: {user.slots}")
            
            crowded_slots = []
            for slot in user_slots:
                if slot <= self.time_point // 2:
                    continue
                booked = self.occupied[slot-1]
                if booked >= self.total_spots:
                    crowded_slots.append(f"时段{slot}(已满)")
                elif booked >= self.total_spots * 0.8:
                    crowded_slots.append(f"时段{slot}(接近满员:{booked}/{self.total_spots})")
            
            if crowded_slots:
                reason_parts.append(f"  拥挤时段: {', '.join(crowded_slots)}")
        
        reason_parts.append("=" * 70)
        
        return "\n" + "\n".join(reason_parts)
    
    def _recommend_spots_for_user(self, user, time_slot):
        """为用户推荐可能的车位"""
        all_spots = range(1, self.total_spots + 1)
        
        current_start = user.slots[0]
        current_end = user.slots[-1]
        current_duration = len(user.slots)
        user_bitmap = calculate_bitmap(user.slots)
        
        # 获取未来订单的位图列表
        check_end = current_end + AllocationWeights.OVERTIME_EXTEND_SLOTS if AllocationWeights.CONSIDER_OVERTIME else current_end
        future_bitmaps = []
        for u in self.users.values():
            if not u.checked_in and not u.checked_out:
                if u.slots[0] > time_slot + 1:
                    if u.slots[0] > check_end:
                        continue
                    overlap_start = max(current_start, u.slots[0])
                    overlap_end = min(check_end, u.slots[-1])
                    if overlap_start <= overlap_end:
                        bitmap = ((1 << (overlap_end - overlap_start + 1)) - 1) << overlap_start
                        future_bitmaps.append(bitmap)
                        if len(future_bitmaps) >= AllocationWeights.MAX_FUTURE_ORDERS:
                            break
        
        stats = {
            'idle_no_conflict': 0,
            'idle_has_future_conflict': 0,
            'occupied_no_conflict': 0,
            'occupied_conflict': 0,
        }
        
        overtime_spot_details = []
        
        for spot in all_spots:
            # 构建车位位图
            spot_bitmap = 0
            for slot, _ in self.spot_schedule[spot].items():
                spot_bitmap |= (1 << (slot + 1))
            
            future_conflict = False
            conflicting_slots = []
            for fb in future_bitmaps:
                conflict_bit = spot_bitmap & fb
                if conflict_bit != 0:
                    future_conflict = True
                    for slot in range(current_start, current_end + 1):
                        if (conflict_bit >> slot) & 1:
                            conflicting_slots.append(slot)
                    break
            
            # 获取当前占用该车位的用户
            current_occupants = []
            for u in self.users.values():
                if u.checked_in and not u.checked_out and u.spot_assigned == spot:
                    if u not in current_occupants:
                        current_occupants.append(u)
            
            # 检查用户的所有时段是否都空闲（考虑超时用户的实际占用范围）
            all_slots_free = True
            for slot in range(current_start, current_end + 1):
                # 检查 spot_schedule
                if slot-1 in self.spot_schedule[spot]:
                    all_slots_free = False
                    break
                
                # 检查该车位上的用户是否超时占用了当前时段
                for occ in current_occupants:
                    # 获取占用者的实际占用结束时段
                    if occ.overtime and hasattr(occ, 'actual_end_slot') and occ.actual_end_slot is not None:
                        occ_end = occ.actual_end_slot
                    else:
                        occ_end = occ.slots[-1]
                    
                    if slot >= occ.slots[0] and slot <= occ_end:
                        all_slots_free = False
                        break
                if not all_slots_free:
                    break
            
            # 检查是否有冲突（时段重叠），考虑超时用户的实际占用范围
            has_conflict = False
            conflict_with_users = []
            for occ in current_occupants:
                # 获取占用者的实际占用结束时段
                if occ.overtime and hasattr(occ, 'actual_end_slot') and occ.actual_end_slot is not None:
                    occ_start = occ.slots[0]
                    occ_end = occ.actual_end_slot
                else:
                    occ_start = occ.slots[0]
                    occ_end = occ.slots[-1]
                
                # 检查是否有重叠
                if current_end >= occ_start and current_start <= occ_end:
                    has_conflict = True
                    conflict_with_users.append(occ)
            
            is_occupied = len(current_occupants) > 0
            # 判断是否有超时用户占用
            has_overtime = any(occ.overtime for occ in current_occupants)
            
            # 统计
            if all_slots_free:
                if not future_conflict:
                    stats['idle_no_conflict'] += 1
                else:
                    stats['idle_has_future_conflict'] += 1
            elif not has_conflict:
                stats['occupied_no_conflict'] += 1
            else:
                stats['occupied_conflict'] += 1
            
            # 记录超时用户占用详情
            if has_overtime and has_conflict:
                status = []
                occupant_info_list = []
                for occ in conflict_with_users:
                    # 获取占用者的实际占用范围
                    if occ.overtime and hasattr(occ, 'actual_end_slot') and occ.actual_end_slot is not None:
                        occ_status = "超时"
                        occ_range = f"{occ.slots[0]}-{occ.actual_end_slot}"
                    else:
                        occ_status = "正常"
                        occ_range = f"{occ.slots[0]}-{occ.slots[-1]}"
                    
                    # 计算冲突时段
                    conflict_start = max(current_start, occ.slots[0])
                    conflict_end = min(current_end, occ.slots[-1])
                    if conflict_start <= conflict_end:
                        if conflict_start == conflict_end:
                            conflict_str = f" [冲突时段:{conflict_start}]"
                        else:
                            conflict_str = f" [冲突时段:{conflict_start}-{conflict_end}]"
                    else:
                        conflict_str = ""
                    
                    occupant_info_list.append(f"用户{occ.id}({occ_status})占用时段{occ_range}{conflict_str}")
                occupant_info = ", ".join(occupant_info_list)
                status.append(f"被{occupant_info}占用")
                
                if future_conflict and conflicting_slots:
                    unique_conflicts = sorted(set(conflicting_slots))
                    status.append(f"未来时段{unique_conflicts}与其他预订冲突")
                
                status.append("[提示:超时用户离开后可分配]")
                overtime_spot_details.append(f"车位{spot:3d} - {', '.join(status)}")
        
        result_lines = []
        result_lines.append(f"\n[车位统计]")
        result_lines.append(f"  总计:{self.total_spots}个车位")
        result_lines.append(f"  理想车位(用户所有时段都空闲): {stats['idle_no_conflict']}个")
        result_lines.append(f"  空闲但有未来冲突: {stats['idle_has_future_conflict']}个")
        result_lines.append(f"  被占用但与用户时段不冲突: {stats['occupied_no_conflict']}个 (可用!)")
        result_lines.append(f"  被占用且与用户时段冲突: {stats['occupied_conflict']}个")
        
        result_lines.append(f"\n[失败原因分析]")
        if stats['idle_no_conflict'] == 0 and stats['occupied_no_conflict'] == 0:
            if stats['occupied_conflict'] > 0:
                result_lines.append(f"  所有车位都被占用且与用户时段冲突，无法分配")
                if overtime_spot_details:
                    result_lines.append(f"  其中 {len(overtime_spot_details)} 个车位被超时用户占用")
                full_slots = []
                for slot in user.slots:
                    if slot <= self.time_point // 2:
                        continue
                    if self.occupied[slot-1] >= self.total_spots:
                        full_slots.append(slot)
                if full_slots:
                    result_lines.append(f"  关键原因: 时段{full_slots}已满，导致无法分配")
            elif stats['idle_has_future_conflict'] > 0:
                result_lines.append(f"  有空闲车位但未来时段已被预订，是预订冲突导致")
            else:
                result_lines.append(f"  没有可用的车位")
        elif stats['occupied_no_conflict'] > 0:
            result_lines.append(f"  有{stats['occupied_no_conflict']}个车位被占用但与用户时段不冲突，理论上可用")
            result_lines.append(f"  但分配失败，可能是算法没有正确识别这些可用车位")
        else:
            result_lines.append(f"  有{stats['idle_no_conflict']}个理想车位可用")
            full_slots = []
            for slot in user.slots:
                if slot <= self.time_point // 2:
                    continue
                if self.occupied[slot-1] >= self.total_spots:
                    full_slots.append(slot)
            if full_slots:
                result_lines.append(f"  关键原因: 时段{full_slots}已满，虽然有空闲车位但无法满足连续时段需求")
            else:
                result_lines.append(f"  但分配失败，可能原因是算法未能正确匹配可用车位")
        
        if overtime_spot_details:
            result_lines.append(f"\n[超时用户占用详情] (共{len(overtime_spot_details)}个)")
            for detail in overtime_spot_details[:20]:
                result_lines.append(f"  {detail}")
            if len(overtime_spot_details) > 20:
                result_lines.append(f"  ... 还有{len(overtime_spot_details)-20}个超时用户占用的车位")
        else:
            result_lines.append(f"\n[超时用户占用详情] 无超时用户占用车位")
        
        return result_lines

    @_profile
    def depart(self, user_id: int, time_slot: int, overtime: bool = False) -> Tuple[bool, str]:
        """用户离开"""
        if user_id not in self.users:
            return False, "用户不存在"
        
        user = self.users[user_id]
        if not user.checked_in:
            return False, "用户未到达"
        
        if user.checked_out:
            return False, "用户已离开"
        
        if user.overtime:
            user.checked_out = True
            user.checkout_time = time_slot
            
            if user.spot_assigned:
                spot = user.spot_assigned
                for slot in user.slots:
                    if slot-1 in self.spot_schedule[spot]:
                        del self.spot_schedule[spot][slot-1]
                if hasattr(user, 'actual_end_slot') and user.actual_end_slot is not None:
                    for slot in range(user.slots[-1] + 1, user.actual_end_slot + 1):
                        if slot-1 in self.spot_schedule[spot]:
                            del self.spot_schedule[spot][slot-1]
                self._update_spot_bitmap(spot)
            
            return True, "离开成功"
        
        expected_slot = user.slots[-1]
        if not overtime and time_slot + 1 != expected_slot:
            return False, f"用户应在时段{expected_slot}离开"
        
        if overtime:
            user.overtime = True
            if not hasattr(user, 'overtime_start') or user.overtime_start is None:
                user.overtime_start = time_slot
            
            if not hasattr(user, 'actual_end_slot') or user.actual_end_slot is None:
                user.actual_end_slot = user.slots[-1]
                
            user.actual_end_slot += 1
            
            if user.spot_assigned:
                spot = user.spot_assigned
                for slot in range(user.slots[-1] + 1, user.actual_end_slot + 1):
                    self.spot_schedule[spot][slot-1] = user.id
                self._update_spot_bitmap(spot)
            
            return True, "继续停车"
        
        user.checked_out = True
        user.checkout_time = time_slot
        
        if user.spot_assigned:
            spot = user.spot_assigned
            for slot in user.slots:
                if slot-1 in self.spot_schedule[spot]:
                    del self.spot_schedule[spot][slot-1]
            self._update_spot_bitmap(spot)
        
        return True, "离开成功"
    
    @_profile
    def advance_time(self, time_slot: int) -> None:
        self.time_point = time_slot
    
    @_profile
    def get_slot_status(self, time_slot: int) -> TimeSlotStatus:
        idx = time_slot - 1
        actual = 0
        
        for user in self.users.values():
            if user.checked_in and not user.checked_out:
                # 检查是否在预订时段内
                if time_slot in user.slots:
                    actual += 1
                # 检查是否在超时时段内
                elif user.overtime and hasattr(user, 'actual_end_slot') and user.actual_end_slot is not None:
                    if time_slot > user.slots[-1] and time_slot <= user.actual_end_slot:
                        actual += 1
            elif user.checked_in and user.checked_out:
                # 已离开的用户
                if user.checkin_time + 1 <= time_slot <= user.checkout_time + 1:
                    actual += 1
        
        is_past = time_slot <= self.time_point // 2
        
        return TimeSlotStatus(
            slot_index=time_slot,
            booked_count=self.occupied[idx],
            actual_count=actual,
            capacity=self.total_spots,
            is_past=is_past
        )
    
    @_profile
    def get_all_users(self) -> List[User]:
        return list(self.users.values())
    
    def reset(self) -> None:
        self.__init__(self.total_spots, self.num_slots)
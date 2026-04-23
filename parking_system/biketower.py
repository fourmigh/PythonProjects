# biketower.py
import time
from datetime import datetime, timedelta
from core.parking_system import ParkingSystem
from core.models import User, TimeSlotStatus


class ParkingReservationSystemUI:
    """停车预订系统UI类"""
    
    def __init__(self, total_spots, num_slots):
        self.total_spots = total_spots
        self.num_slots = num_slots
        self.system = ParkingSystem(total_spots, num_slots)
        self.mode = "booking"
        
    def get_time_range(self, slot_index):
        slot_duration = 24 * 60 // self.num_slots
        start_minutes = slot_index * slot_duration
        end_minutes = (slot_index + 1) * slot_duration
        start_hour = start_minutes // 60
        start_min = start_minutes % 60
        end_hour = end_minutes // 60
        end_min = end_minutes % 60
        return f"{start_hour:02d}:{start_min:02d}-{end_hour:02d}:{end_min:02d}"
    
    def get_time_point_description(self):
        if self.system.time_point % 2 == 0:
            slot_index = self.system.time_point // 2
            if slot_index < self.num_slots:
                return f"时段 {slot_index + 1} 开始前 ({self.get_time_range(slot_index)})"
            else:
                return f"所有时段结束"
        else:
            slot_index = self.system.time_point // 2
            if slot_index < self.num_slots:
                return f"时段 {slot_index + 1} 结束后 ({self.get_time_range(slot_index)})"
            else:
                return f"所有时段结束"
    
    def display_availability(self):
        print("\n" + "="*60)
        print(f"当前模式: {'预订模式' if self.mode == 'booking' else '分配/取车模式'}")
        if self.mode == "assignment":
            print(f"当前时间点: {self.get_time_point_description()}")
        print("="*60)
        print("当前各时段空余车位情况：")
        print("-"*60)
        
        if self.mode == "booking":
            past_slots = self.system.time_point // 2
            
            for i in range(self.num_slots):
                slot_status = self.system.get_slot_status(i + 1)
                available = slot_status.capacity - slot_status.booked_count
                if i < past_slots:
                    print(f"时段 {i+1:2d} ({self.get_time_range(i)}): {available:2d} 个空位 (已过去，不可预订)")
                else:
                    print(f"时段 {i+1:2d} ({self.get_time_range(i)}): {available:2d} 个空位 (已预订 {slot_status.booked_count})")
        else:
            current_slot = self.system.time_point // 2
            for i in range(self.num_slots):
                slot_status = self.system.get_slot_status(i + 1)
                available = slot_status.capacity - slot_status.actual_count
                if i < current_slot:
                    print(f"时段 {i+1:2d} ({self.get_time_range(i)}): {available:2d} 个空位 (历史占用 {slot_status.actual_count})")
                elif i == current_slot:
                    if self.system.time_point % 2 == 0:
                        print(f"时段 {i+1:2d} ({self.get_time_range(i)}): {available:2d} 个空位 (时段开始前 {slot_status.actual_count}) *")
                    else:
                        print(f"时段 {i+1:2d} ({self.get_time_range(i)}): {available:2d} 个空位 (时段结束后 {slot_status.actual_count}) *")
                else:
                    print(f"时段 {i+1:2d} ({self.get_time_range(i)}): {available:2d} 个空位 (未来预订 {slot_status.booked_count})")
        print("="*60)
    
    def parse_time_slots(self, input_str):
        input_str = input_str.strip()
        slots = []
        
        if '-' in input_str and ',' not in input_str:
            try:
                start, end = map(int, input_str.split('-'))
                if start < 1 or end > self.num_slots or start > end:
                    return None
                slots = list(range(start, end + 1))
            except:
                return None
        elif ',' in input_str:
            try:
                parts = input_str.split(',')
                slots = [int(p.strip()) for p in parts if p.strip()]
                for slot in slots:
                    if slot < 1 or slot > self.num_slots:
                        return None
                slots = sorted(set(slots))
                if len(slots) > 1:
                    for i in range(len(slots)-1):
                        if slots[i+1] != slots[i] + 1:
                            print("提示：预订的时段必须连续！")
                            return None
            except:
                return None
        else:
            try:
                slot = int(input_str)
                if slot < 1 or slot > self.num_slots:
                    return None
                slots = [slot]
            except:
                return None
                
        return slots
    
    def format_slots(self, slots):
        if len(slots) == 1:
            return f"时段 {slots[0]} ({self.get_time_range(slots[0]-1)})"
        else:
            return f"时段 {slots[0]}-{slots[-1]} ({self.get_time_range(slots[0]-1)} 到 {self.get_time_range(slots[-1]-1)})"
    
    def get_available_options(self):
        return self.system.get_available_slots()
    
    def display_available_options(self):
        if self.mode != "booking":
            return
            
        options = self.get_available_options()
        
        if not options:
            print("\n当前没有任何可预订的时段！所有时段都已满或已过去。")
            return
            
        print("\n" + "="*60)
        print("当前可预订的时段选项：")
        print("-"*60)
        
        by_length = {}
        for opt in options:
            length = len(opt)
            if length not in by_length:
                by_length[length] = []
            by_length[length].append(opt)
        
        for length in sorted(by_length.keys()):
            if length == 1:
                print(f"\n单独时段：")
            else:
                print(f"\n{length}个连续时段：")
            for opt in by_length[length]:
                if len(opt) == 1:
                    print(f"  时段 {opt[0]} ({self.get_time_range(opt[0]-1)})")
                else:
                    print(f"  时段 {opt[0]}-{opt[-1]} ({self.get_time_range(opt[0]-1)} 到 {self.get_time_range(opt[-1]-1)})")
        print("="*60)
    
    def process_time_start(self, time_slot):
        print("-"*60)
        print(f"[时段开始] 时段 {time_slot + 1} ({self.get_time_range(time_slot)}) 开始")
        print("-"*60)
        
        arriving_users = []
        for user in self.system.get_all_users():
            if not user.checked_in and not user.checked_out:
                if time_slot + 1 == user.slots[0]:
                    arriving_users.append(user)
        
        if arriving_users:
            print(f"\n[到达] 需要到达的用户（共 {len(arriving_users)} 人）：")
            for user in arriving_users:
                print(f"  用户 {user.id} - 预订时段: {self.format_slots(user.slots)}")
            
            for user in arriving_users:
                success, msg = self.system.arrive_smart(user.id, time_slot)
                if success:
                    print(f"\n  [成功] 用户 {user.id} 到达，{msg}")
                else:
                    print(f"\n  [失败] 用户 {user.id} 无法分配车位: {msg}")
        
        self.show_current_occupancy(time_slot)
    
    def process_time_end(self, time_slot):
        print("-"*60)
        print(f"[时段结束] 时段 {time_slot + 1} ({self.get_time_range(time_slot)}) 结束")
        print("-"*60)
        
        leaving_users = []
        for user in self.system.get_all_users():
            if user.checked_in and not user.checked_out:
                if time_slot + 1 == user.slots[-1] or user.overtime:
                    leaving_users.append(user)
        
        if leaving_users:
            print(f"\n[离开] 需要处理的离开用户：")
            for user in leaving_users:
                spot_display = str(user.spot_assigned) if user.spot_assigned is not None else "未分配"
                if user.overtime:
                    overtime_start = user.overtime_start if hasattr(user, 'overtime_start') and user.overtime_start is not None else "?"
                    print(f"  用户 {user.id} (车位 {spot_display}) - 超时用户 (从时段{overtime_start}开始超时)，需决定是否继续")
                else:
                    print(f"  用户 {user.id} (车位 {spot_display}) - 预订结束时间到")
            
            for user in leaving_users:
                if user.spot_assigned is None:
                    print(f"\n[警告] 用户 {user.id} 还未分配车位，无法处理")
                    continue
                    
                if user.overtime:
                    print(f"\n用户 {user.id} 当前处于超时状态，是否继续停车？")
                else:
                    print(f"\n用户 {user.id} 预订时间已到，是否超时继续停车？")
                
                choice = input("  (y=继续停车/n=离开，默认n): ").strip().lower()
                overtime_choice = (choice == 'y')
                success, msg = self.system.depart(user.id, time_slot, overtime_choice)
                if success:
                    if overtime_choice:
                        print(f"  [继续] 用户 {user.id} 选择继续停车，继续占用车位 {user.spot_assigned}")
                    else:
                        print(f"  [离开] 用户 {user.id} 离开，释放车位 {user.spot_assigned}")
                else:
                    print(f"  [失败] {msg}")
        
        self.show_current_occupancy(time_slot)
    
    def show_current_occupancy(self, time_slot):
        print(f"\n[车位占用] 当前车位占用情况：")
        occupied_spots = []
        for user in self.system.get_all_users():
            if user.checked_in and not user.checked_out and user.spot_assigned is not None:
                if user.overtime:
                    if hasattr(user, 'overtime_start') and user.overtime_start is not None:
                        overtime_duration = time_slot - user.overtime_start
                    else:
                        overtime_duration = 0
                    status = f"超时({overtime_duration}段)"
                else:
                    status = "正常"
                occupied_spots.append(f"车位{user.spot_assigned}: 用户{user.id}({status})")
        
        if occupied_spots:
            for spot_info in occupied_spots:
                print(f"  {spot_info}")
        else:
            print("  无占用")
        
        if time_slot + 1 < self.num_slots:
            print(f"\n[未来预订] 时段 {time_slot + 2} 到 {self.num_slots} 的预订情况：")
            for i in range(time_slot + 1, self.num_slots):
                slot_status = self.system.get_slot_status(i + 1)
                available = slot_status.capacity - slot_status.booked_count
                print(f"  时段 {i+1} ({self.get_time_range(i)}): {available} 个空位")
    
    def advance_time(self):
        total_points = self.num_slots * 2
        
        if self.system.time_point < total_points:
            slot_index = self.system.time_point // 2
            is_start = (self.system.time_point % 2 == 0)
            
            if is_start:
                print(f"\n{'='*60}")
                print(f"前进到时段 {slot_index + 1} 开始")
                print(f"{'='*60}")
                self.process_time_start(slot_index)
            else:
                print(f"\n{'='*60}")
                print(f"前进到时段 {slot_index + 1} 结束")
                print(f"{'='*60}")
                self.process_time_end(slot_index)
            
            self.system.advance_time(self.system.time_point + 1)
            
            if self.system.time_point < total_points:
                next_slot_index = self.system.time_point // 2
                next_is_start = (self.system.time_point % 2 == 0)
                if next_is_start:
                    print(f"\n[下一步] 下一个时间点：时段 {next_slot_index + 1} 开始")
                else:
                    print(f"\n[下一步] 下一个时间点：时段 {next_slot_index + 1} 结束")
                print("   输入 'n' 继续前进")
            else:
                print(f"\n[完成] 已处理完所有时间点")
                self.handle_end_of_day()
        else:
            print("\n已经处理完所有时间点")
            self.handle_end_of_day()
    
    def initialize_assignment(self):
        print("\n" + "="*60)
        print("初始化分配模式...")
        print("="*60)
        
        pending_users = [u for u in self.system.get_all_users() 
                        if not u.checked_in and not u.checked_out]
        
        if pending_users:
            print(f"\n[待处理] 发现 {len(pending_users)} 个待处理的用户：")
            for user in pending_users:
                print(f"  用户 {user.id} - 预订时段: {self.format_slots(user.slots)}")
            print("\n提示：使用 'n' 命令逐步前进时间来处理这些用户")
        else:
            print("\n暂无待处理的用户")
        
        current_slot = self.system.time_point // 2
        if current_slot < self.num_slots:
            print(f"\n初始化完成！当前时间点：时段 {current_slot + 1} 开始前")
        else:
            print(f"\n初始化完成！所有时段已结束")
        print("使用 'n' 命令前进一个时间点（开始或结束）")
        print("="*60)
    
    def switch_to_booking(self):
        self.mode = "booking"
        past_slots = self.system.time_point // 2
        
        if past_slots > 0:
            print(f"\n[提示] 当前时间已经到达时段 {past_slots + 1} 开始前")
            print(f"       时段 1-{past_slots} 已经过去，无法预订")
        
        if past_slots < self.num_slots:
            print(f"       可预订时段: {past_slots + 1} 到 {self.num_slots}")
        else:
            print(f"       所有时段都已过去，无法继续预订")
    
    def show_progress(self):
        if self.mode == "assignment":
            total_points = self.num_slots * 2
            print(f"\n[进度] 当前进度：")
            print(f"   已处理时间点: {self.system.time_point}/{total_points}")
            
            if self.system.time_point < total_points:
                slot_index = self.system.time_point // 2
                is_start = (self.system.time_point % 2 == 0)
                if is_start:
                    print(f"   下一个时间点: 时段 {slot_index + 1} 开始")
                else:
                    print(f"   下一个时间点: 时段 {slot_index + 1} 结束")
            
            pending_users = [u for u in self.system.get_all_users() 
                           if not u.checked_in and not u.checked_out 
                           and u.slots[0] > self.system.time_point // 2 + 1]
            
            if pending_users:
                print(f"   等待处理的用户: {len(pending_users)} 人")
                for user in pending_users[:3]:
                    print(f"     - 用户 {user.id}: {self.format_slots(user.slots)}")
                if len(pending_users) > 3:
                    print(f"     ... 还有 {len(pending_users) - 3} 个用户")
    
    def handle_end_of_day(self):
        print("\n" + "="*60)
        print("所有时间段结束，处理剩余用户...")
        print("="*60)
        
        remaining_users = [u for u in self.system.get_all_users() 
                          if u.checked_in and not u.checked_out]
        
        if remaining_users:
            print(f"\n[剩余] 还有 {len(remaining_users)} 个用户在场内：")
            for user in remaining_users:
                spot_display = str(user.spot_assigned) if user.spot_assigned is not None else "未分配"
                if user.overtime:
                    overtime_start = user.overtime_start if hasattr(user, 'overtime_start') and user.overtime_start is not None else "?"
                    overtime_duration = self.system.time_point // 2 - (user.overtime_start if hasattr(user, 'overtime_start') and user.overtime_start is not None else self.system.time_point // 2)
                    print(f"  用户 {user.id} (车位 {spot_display}) - 已超时 {overtime_duration} 个时间段 (从时段{overtime_start}开始)")
                else:
                    print(f"  用户 {user.id} (车位 {spot_display}) - 正常停车")
            
            print("\n如何处理剩余用户？")
            print("  1 - 全部强制离开")
            print("  2 - 逐个询问")
            print("  3 - 保持原状（不处理）")
            
            choice = input("请选择 (1/2/3，默认1): ").strip()
            
            if choice == '2':
                for user in remaining_users:
                    if user.spot_assigned is None:
                        print(f"\n[警告] 用户 {user.id} 还未分配车位，无法处理")
                        continue
                    print(f"\n用户 {user.id} (车位 {user.spot_assigned})")
                    choice2 = input("  是否离开？(y=离开/n=留下，默认y): ").strip().lower()
                    if choice2 != 'n':
                        success, msg = self.system.depart(user.id, self.system.time_point // 2, False)
                        if success:
                            print(f"  [离开] 用户 {user.id} 离开，释放车位 {user.spot_assigned}")
                        else:
                            print(f"  [失败] {msg}")
            elif choice == '1':
                for user in remaining_users:
                    if user.spot_assigned is None:
                        print(f"\n[警告] 用户 {user.id} 还未分配车位，跳过")
                        continue
                    success, msg = self.system.depart(user.id, self.system.time_point // 2, False)
                    if success:
                        print(f"\n[强制离开] 用户 {user.id} 强制离开，释放车位 {user.spot_assigned}")
                    else:
                        print(f"\n[失败] 用户 {user.id} 强制离开失败: {msg}")
            else:
                print("保持原状，不处理剩余用户")
        
        print("\n" + "="*60)
        print("最终统计：")
        print("-"*60)
        
        all_users = self.system.get_all_users()
        total_users = len(all_users)
        completed_users = sum(1 for u in all_users if u.checked_out)
        overtime_users = sum(1 for u in all_users if u.overtime)
        
        print(f"总用户数: {total_users}")
        print(f"已完成用户: {completed_users}")
        print(f"超时用户: {overtime_users}")
        print("="*60)
        
        print("\n系统运行结束。")
        print("输入 'r' 重置系统，输入 'q' 退出，其他键继续但不再处理时间")
        end_choice = input(">>> ").strip().lower()
        if end_choice == 'r':
            self.system.reset()
            print("系统已重置")
        elif end_choice == 'q':
            exit(0)
    
    def display_all_users(self):
        users = self.system.get_all_users()
        if not users:
            print("\n暂无用户")
            return
        
        print("\n" + "="*80)
        print("所有用户信息：")
        print("-"*80)
        for user in users:
            status = []
            if user.checked_in:
                status.append("已到达")
            if user.checked_out:
                status.append("已离开")
            if user.overtime:
                status.append("超时")
            status_str = ", ".join(status) if status else "未到达"
            
            spot_display = str(user.spot_assigned) if user.spot_assigned is not None else "未分配"
            
            print(f"用户 {user.id:2d}: {self.format_slots(user.slots):30s} "
                  f"车位 {spot_display:3s} "
                  f"状态: {status_str}")
        print("="*80)
    
    def display_spot_schedule(self):
        print("\n车位分配时间表：")
        print("-"*100)
        
        header = "车位号 |"
        for i in range(self.num_slots):
            header += f" 时段{i+1:2d} |"
        print(header)
        print("-"*100)
        
        for spot in range(1, self.total_spots + 1):
            row = f"  {spot:2d}   |"
            for slot in range(self.num_slots):
                row += f"  空   |"
            print(row)
        print("="*100)


def main():
    print("="*60)
    print("自行车停车库预订系统（含车位分配）")
    print("="*60)
    
    while True:
        try:
            total_spots = int(input("请输入总车位数: "))
            if total_spots <= 0:
                print("车位数必须大于0，请重新输入")
                continue
            break
        except ValueError:
            print("请输入有效的数字")
    
    while True:
        try:
            num_slots = int(input("请输入时间段个数: "))
            if num_slots <= 0:
                print("时间段个数必须大于0，请重新输入")
                continue
            break
        except ValueError:
            print("请输入有效的数字")
    
    ui = ParkingReservationSystemUI(total_spots, num_slots)
    
    slot_duration = 24 * 60 // num_slots
    slot_hours = slot_duration / 60
    print(f"\n系统初始化完成：{total_spots}个车位，{num_slots}个时间段")
    print(f"每个时间段时长：{slot_hours:.1f}小时 ({slot_duration}分钟)")
    print(f"时间范围：{ui.get_time_range(0)} 到 {ui.get_time_range(num_slots-1)}")
    print("\n时间段编号：1, 2, 3, ...")
    
    system_running = True
    while system_running:
        if ui.mode == "booking":
            ui.display_availability()
            ui.display_available_options()
            print("\n[预订模式] 可用命令:")
            print("  [数字/范围/逗号] - 预订时段")
            print("  m - 切换到分配模式")
            print("  u - 显示所有用户")
            print("  s - 显示车位时间表")
            print("  q - 退出系统")
            print("="*60)
        else:
            ui.display_availability()
            ui.show_progress()
            print("\n[分配模式] 可用命令:")
            print("  n - 前进一个时间点（开始或结束）")
            print("  m - 切换到预订模式")
            print("  u - 显示所有用户")
            print("  s - 显示车位时间表")
            print("  q - 退出系统")
            print("="*60)
        
        user_input = input(">>> ").strip().lower()
        
        if user_input == 'q':
            print("退出系统")
            system_running = False
            break
        elif user_input == 'm':
            if ui.mode == "booking":
                ui.mode = "assignment"
                print(f"\n已切换到分配模式")
                ui.initialize_assignment()
                ui.show_progress()
            else:
                ui.switch_to_booking()
        elif user_input == 'u':
            ui.display_all_users()
        elif user_input == 's':
            ui.display_spot_schedule()
        elif ui.mode == "booking":
            slots = ui.parse_time_slots(user_input)
            if slots is None:
                print("输入格式错误，请重新输入")
                continue
            next_id = ui.system.next_user_id
            success, msg = ui.system.book(next_id, slots)
            if success:
                print(f"\n[成功] 预订成功！用户 {next_id} 预订时段：{ui.format_slots(slots)}")
            else:
                print(f"\n[失败] {msg}")
        elif ui.mode == "assignment":
            if user_input == 'n':
                ui.advance_time()
            elif user_input == '':
                continue
            else:
                print(f"未知命令 '{user_input}'，分配模式下可用命令: n, m, u, s, q")
        else:
            print("未知命令")


if __name__ == "__main__":
    main()
# test_parking_system.py
import random
import time
from typing import List, Tuple, Dict
from core.parking_system import ParkingSystem


class ParkingSystemAdvancedTester:
    def __init__(self, total_spots: int, num_slots: int):
        self.total_spots = total_spots
        self.num_slots = num_slots
        
    def calculate_combinatorial_explosion(self, max_users: int) -> int:
        """计算组合爆炸规模"""
        slot_options = self.num_slots
        for length in range(2, self.num_slots + 1):
            slot_options += (self.num_slots - length + 1)
        
        total = 0
        for num_users in range(1, max_users + 1):
            total += slot_options ** num_users
        return total

    def generate_non_overlapping_bookings(self, num_bookings: int, all_options: List[List[int]] = None) -> List[List[int]]:
        """
        生成不重叠的预订序列（间隔至少1个时段）
        
        Args:
            num_bookings: 要生成的预订数量
            all_options: 时段选项列表（如果为None，则自动生成）
        
        Returns:
            不重叠的预订列表（可能少于num_bookings，如果没有足够选项）
        """
        if all_options is None:
            all_options = self.generate_slot_options()
        
        bookings = []
        last_end = 0
        
        for _ in range(num_bookings):
            # 筛选可用的选项：起始时段必须 > last_end + 1（间隔至少1个时段）
            available_options = []
            for option in all_options:
                option_start = option[0]
                if option_start > last_end + 1 and option_start <= self.num_slots:
                    available_options.append(option)
            
            if not available_options:
                break
            
            selected = random.choice(available_options)
            bookings.append(selected.copy())
            last_end = selected[-1]
        
        return bookings
    
    def random_test(self, num_tests: int = 10000, max_users: int = 10, 
                    overtime_decision: str = "never") -> None:
        """随机测试"""
        import random
        
        print(f"\n{'='*80}")
        print(f"随机测试：{self.total_spots}车位，{self.num_slots}时段")
        print(f"测试次数: {num_tests:,}")
        print(f"最大用户数: {max_users}")
        print(f"超时模式: {overtime_decision}")
        print(f"{'='*80}")
        
        all_slot_options = self.generate_slot_options()
        
        results = {
            'success': 0, 'fail': 0, 'booked': 0, 'arrived': 0, 'failed_arrivals': 0,
            'arrival_times': [], 'arrival_count': 0
        }
        
        fail_cases = []
        start_time = time.time()
        
        for test_id in range(num_tests):
            num_users = random.randint(1, max_users)
            
            # 使用公共方法生成不重叠的预订
            bookings = self.generate_non_overlapping_bookings(num_users, all_slot_options)
            
            # 如果没有生成任何预订，跳过
            if len(bookings) == 0:
                continue
            
            # 转换为动态预订格式（预订时间设为 0，表示开始时立即预订）
            bookings_with_time = [(0, slots) for slots in bookings]
            
            success, reason, stats = self.simulate_time_progression(
                bookings_with_time, overtime_decision, collect_timing=True, results_ref=results
            )
            
            if success:
                results['success'] += 1
            else:
                results['fail'] += 1
                if len(fail_cases) < 20:
                    fail_cases.append((test_id, bookings, reason, stats))
            
            results['booked'] += stats['booked_users']
            results['arrived'] += stats['arrived_users']
            results['failed_arrivals'] += stats['failed_arrivals']
            
            if (test_id + 1) % 1000 == 0:
                elapsed = time.time() - start_time
                print(f"进度: {test_id+1}/{num_tests} ({100*(test_id+1)/num_tests:.1f}%) - 耗时: {elapsed:.1f}s")
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*80}")
        print(f"随机测试完成!")
        print(f"耗时: {elapsed:.1f}秒")
        print(f"{'='*80}")
        
        self._print_single_result(results, fail_cases, num_tests)
        self._print_timing_stats(results)
    
    def stress_test(self, num_users: int = 50, num_tests: int = 100,
                   overtime_decision: str = "never") -> None:
        """压力测试"""
        import random
        
        print(f"\n{'='*80}")
        print(f"压力测试：{self.total_spots}车位，{self.num_slots}时段")
        print(f"每测试用户数: {num_users}")
        print(f"测试次数: {num_tests}")
        print(f"超时模式: {overtime_decision}")
        print(f"{'='*80}")
        
        all_slot_options = self.generate_slot_options()
        
        results = {
            'success': 0, 'fail': 0, 'booked': 0, 'arrived': 0, 'failed_arrivals': 0,
            'arrival_times': [], 'arrival_count': 0
        }
        
        start_time = time.time()
        
        for test_id in range(num_tests):
            # 使用公共方法生成不重叠的预订
            bookings = self.generate_non_overlapping_bookings(num_users, all_slot_options)
            
            # 如果没有生成任何预订，跳过
            if len(bookings) == 0:
                continue
            
            # 转换为动态预订格式（预订时间设为 0，表示开始时立即预订）
            bookings_with_time = [(0, slots) for slots in bookings]
            
            success, reason, stats = self.simulate_time_progression(
                bookings_with_time, overtime_decision, collect_timing=True, results_ref=results
            )
            
            if success:
                results['success'] += 1
            else:
                results['fail'] += 1
            
            results['booked'] += stats['booked_users']
            results['arrived'] += stats['arrived_users']
            results['failed_arrivals'] += stats['failed_arrivals']
            
            if (test_id + 1) % 10 == 0:
                elapsed = time.time() - start_time
                print(f"进度: {test_id+1}/{num_tests} ({100*(test_id+1)/num_tests:.1f}%) - 耗时: {elapsed:.1f}s")
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*80}")
        print(f"压力测试完成!")
        print(f"耗时: {elapsed:.1f}秒")
        print(f"{'='*80}")
        
        self._print_single_result(results, None, num_tests, is_stress=True)
        self._print_timing_stats(results)
    
    def edge_case_test(self, overtime_decision: str = "never") -> None:
        """边界测试"""
        print(f"\n{'='*80}")
        print(f"边界测试：{self.total_spots}车位，{self.num_slots}时段")
        print(f"超时模式: {overtime_decision}")
        print(f"{'='*80}")
        
        all_slot_options = self.generate_slot_options()
        test_scenarios = []
        
        # 1. 最大容量测试（使用公共方法生成不重叠）
        max_capacity = min(self.total_spots * self.num_slots, 100)
        bookings = self.generate_non_overlapping_bookings(max_capacity, all_slot_options)
        test_scenarios.append(("最大容量测试", bookings))
        
        # 2. 全时段长预订（单个预订，无重叠问题）
        bookings = [[1, self.num_slots]]
        test_scenarios.append(("全天预订", bookings))
        
        # 3. 时段边界测试（手动指定不重叠的边界场景）
        bookings = []
        last_end = 0
        for slot in [1, 3, 5, 7]:
            if slot <= self.num_slots:
                bookings.append([slot])
                last_end = slot
        test_scenarios.append(("时段边界测试", bookings))
        
        # 4. 密集重叠测试（保留原样，用于测试重叠处理能力）
        overlapping_bookings = []
        for i in range(1, self.num_slots):
            overlapping_bookings.append([i, i+1])
        test_scenarios.append(("密集重叠测试（故意重叠）", overlapping_bookings))
        
        # 5. 容量极限测试（可能重叠，保留原样测试边界）
        limit_bookings = []
        for _ in range(self.total_spots * 2):
            slot = random.randint(1, self.num_slots)
            limit_bookings.append([slot])
        test_scenarios.append(("容量极限测试（可能重叠）", limit_bookings))
        
        # 6. 长时段与短时段混合测试（使用公共方法生成基础，再添加长时段）
        mixed_bookings = []
        # 先生成一个长时段
        long_booking = self.generate_non_overlapping_bookings(1, all_slot_options)
        if long_booking:
            mixed_bookings.extend(long_booking)
            last_end = long_booking[0][-1]
            # 再生成一些短时段
            for slot in range(last_end + 2, self.num_slots + 1):
                mixed_bookings.append([slot])
        test_scenarios.append(("长短混合测试", mixed_bookings))
        
        # 7. 完全填充测试（使用公共方法生成）
        full_bookings = self.generate_non_overlapping_bookings(
            self.total_spots * self.num_slots, all_slot_options
        )
        test_scenarios.append(("完全填充测试", full_bookings))
        
        for scenario_name, bookings in test_scenarios:
            if not bookings:
                print(f"\n[跳过] {scenario_name}: 无法生成有效的预订")
                continue
            
            self._test_single_scenario(scenario_name, bookings, overtime_decision)
    
    def generate_slot_options(self) -> List[List[int]]:
        """生成所有可能的时段选择"""
        options = []
        for i in range(1, self.num_slots + 1):
            options.append([i])
        for length in range(2, self.num_slots + 1):
            for start in range(1, self.num_slots - length + 2):
                options.append(list(range(start, start + length)))
        return options
    
    def simulate_time_progression(self, bookings_with_time: List[Tuple[int, List[int]]], 
                                  overtime_decision: str = "never",
                                  collect_timing: bool = False,
                                  results_ref: dict = None) -> Tuple[bool, str, dict]:
        """模拟时间推进 - 支持动态预订
        
        Args:
            bookings_with_time: 带预订时间的列表，格式 [(book_time, slots), ...]
                               book_time: 预订发生的时间点（时段）
                               slots: 预订的时段列表（必须全部 > book_time）
        """
        import random
        
        system = ParkingSystem(self.total_spots, self.num_slots)
        stats = {
            'total_booking_attempts': len(bookings_with_time),
            'booked_users': 0,
            'arrived_users': 0,
            'departed_users': 0,
            'overtime_users': 0,
            'failed_arrivals': 0,
            'failed_bookings': 0,
            'slot_occupancy': []
        }
        
        # 按预订时间排序
        sorted_bookings = sorted(bookings_with_time, key=lambda x: x[0])
        booking_index = 0
        next_user_id = 1
        
        # 时间推进
        for time_slot in range(self.num_slots):
            # 1. 处理新预订（预订时间 == 当前时间）
            while booking_index < len(sorted_bookings):
                book_time, slots = sorted_bookings[booking_index]
                if book_time > time_slot:
                    break
                
                user_id = next_user_id
                next_user_id += 1
                
                success, msg = system.book(user_id, slots)
                if success:
                    stats['booked_users'] += 1
                else:
                    stats['failed_bookings'] += 1
                booking_index += 1
            
            # 2. 到达处理
            for user in system.get_all_users():
                if not user.checked_in and not user.checked_out:
                    if time_slot + 1 == user.slots[0]:
                        if collect_timing and results_ref is not None:
                            start_ns = time.perf_counter_ns()
                            success, msg = system.arrive(user.id, time_slot)
                            end_ns = time.perf_counter_ns()
                            elapsed_us = (end_ns - start_ns) / 1000.0
                            results_ref['arrival_times'].append(elapsed_us)
                            results_ref['arrival_count'] += 1
                        else:
                            success, msg = system.arrive(user.id, time_slot)
                        
                        if success:
                            stats['arrived_users'] += 1
                        else:
                            stats['failed_arrivals'] += 1
                            return False, f"用户{user.id}到达失败 {msg}", stats
            
            # 3. 离开处理
            for user in system.get_all_users():
                if user.checked_in and not user.checked_out:
                    if time_slot + 1 == user.slots[-1]:
                        overtime = False
                        if overtime_decision == "always":
                            overtime = True
                        elif overtime_decision == "random":
                            overtime = random.choice([True, False])
                        
                        success, msg = system.depart(user.id, time_slot, overtime)
                        if success:
                            stats['departed_users'] += 1
                            if overtime:
                                stats['overtime_users'] += 1
        
        return True, "成功", stats
    
    def _print_timing_stats(self, results: dict):
        """打印耗时统计"""
        print("\n" + "="*80)
        print("到达分配耗时统计")
        print("="*80)
        
        if results['arrival_count'] > 0:
            times = results['arrival_times']
            count = results['arrival_count']
            
            avg_us = sum(times) / count
            min_us = min(times)
            max_us = max(times)
            
            # 计算中位数
            sorted_times = sorted(times)
            median_us = sorted_times[len(sorted_times)//2]
            
            # 计算百分位数
            p95_us = sorted_times[int(len(sorted_times) * 0.95)] if len(sorted_times) > 0 else 0
            p99_us = sorted_times[int(len(sorted_times) * 0.99)] if len(sorted_times) > 0 else 0
            
            print(f"  总调用次数: {count:,}")
            print(f"  平均耗时: {avg_us:.3f} μs ({avg_us/1000:.3f} ms)")
            print(f"  最小耗时: {min_us:.3f} μs")
            print(f"  最大耗时: {max_us:.3f} μs")
            print(f"  中位数耗时: {median_us:.3f} μs")
            print(f"  95分位耗时: {p95_us:.3f} μs")
            print(f"  99分位耗时: {p99_us:.3f} μs")
            
            # 每秒可处理次数估算
            ops_per_sec = 1_000_000 / avg_us if avg_us > 0 else 0
            print(f"  估算吞吐量: {ops_per_sec:.0f} 次/秒")
        else:
            print(f"  无到达调用数据")
        
        print("="*80)
    
    def _print_single_result(self, result: Dict, fail_cases: List, 
                             total_tests: int, is_stress: bool = False):
        """打印测试结果"""
        print(f"\n测试结果:")
        print(f"  成功用例: {result['success']}/{total_tests} ({100*result['success']/total_tests:.2f}%)")
        print(f"  失败用例: {result['fail']}/{total_tests} ({100*result['fail']/total_tests:.2f}%)")
        
        if result['booked'] > 0:
            arrival_rate = result['arrived'] / result['booked'] * 100
            print(f"  预订成功: {result['booked']}")
            print(f"  到达成功: {result['arrived']} (到达率: {arrival_rate:.2f}%)")
            if result['failed_arrivals'] > 0:
                print(f"  到达失败: {result['failed_arrivals']}")
        
        if fail_cases and not is_stress:
            print(f"\n失败案例 (显示前5个):")
            for test_id, bookings, reason, stats in fail_cases[:5]:
                print(f"  测试{test_id}: {bookings[:3]}...")
                print(f"    原因: {reason}")
    
    def _test_single_scenario(self, scenario_name: str, bookings: List[List[int]], 
                              overtime_decision: str):
        """测试单个场景"""
        print(f"\n{'='*80}")
        print(f"测试场景: {scenario_name}")
        print(f"用户数: {len(bookings)}")
        print(f"{'='*80}")
        
        temp_results = {'arrival_times': [], 'arrival_count': 0}
        start_total = time.perf_counter_ns()
        
        # 转换为动态预订格式
        bookings_with_time = [(0, slots) for slots in bookings]
        
        success, reason, stats = self.simulate_time_progression(
            bookings_with_time, overtime_decision, collect_timing=True, results_ref=temp_results
        )
        end_total = time.perf_counter_ns()
        total_time_us = (end_total - start_total) / 1000.0
        
        if success:
            arrival_rate = stats['arrived_users'] / stats['booked_users'] * 100 if stats['booked_users'] > 0 else 0
            print(f"[成功]")
            print(f"  预订成功: {stats['booked_users']}/{stats['total_booking_attempts']}")
            print(f"  到达成功: {stats['arrived_users']}/{stats['booked_users']} (到达率: {arrival_rate:.1f}%)")
            print(f"  离开用户: {stats['departed_users']}")
            if stats['overtime_users'] > 0:
                print(f"  超时用户: {stats['overtime_users']}")
            
            if temp_results['arrival_times']:
                avg_time = sum(temp_results['arrival_times']) / len(temp_results['arrival_times'])
                print(f"\n  到达调用次数: {len(temp_results['arrival_times'])}")
                print(f"  平均到达耗时: {avg_time:.3f} μs ({avg_time/1000:.3f} ms)")
                print(f"  总模拟耗时: {total_time_us:.3f} μs ({total_time_us/1000:.3f} ms)")
        else:
            print(f"[失败] {reason}")
        
        print(f"{'='*80}")


def main():
    print("="*80)
    print("自行车停车库系统 - 高级测试程序")
    print("="*80)
    
    while True:
        try:
            total_spots = int(input("请输入总车位数: "))
            if total_spots <= 0:
                print("车位数必须大于0")
                continue
            break
        except ValueError:
            print("请输入有效的数字")
    
    while True:
        try:
            num_slots = int(input("请输入时间段个数: "))
            if num_slots <= 0:
                print("时间段个数必须大于0")
                continue
            break
        except ValueError:
            print("请输入有效的数字")
    
    tester = ParkingSystemAdvancedTester(total_spots, num_slots)
    
    print(f"\n理论最大用户数: {total_spots * num_slots}")
    print(f"如果使用穷举法测试5个用户，组合数将达到: {tester.calculate_combinatorial_explosion(5):,}")
    print("组合爆炸，无法穷举！")
    
    print("\n请选择测试类型:")
    print("  1 - 随机测试（推荐）")
    print("  2 - 压力测试")
    print("  3 - 边界测试")
    print("  4 - 全部测试")
    
    test_type = input("请输入选择 (1/2/3/4): ").strip()
    
    print("\n请选择超时处理模式:")
    print("  1 - 永不超时")
    print("  2 - 总是超时")
    print("  3 - 随机超时")
    
    overtime_choice = input("请输入选择 (1/2/3): ").strip()
    if overtime_choice == '1':
        overtime_mode = "never"
    elif overtime_choice == '2':
        overtime_mode = "always"
    else:
        overtime_mode = "random"
    
    if test_type == '1':
        num_tests = input("请输入测试次数 (默认10000): ").strip()
        num_tests = int(num_tests) if num_tests else 10000
        max_users = input("请输入最大用户数 (默认10): ").strip()
        max_users = int(max_users) if max_users else 10
        tester.random_test(num_tests, max_users, overtime_mode)
    elif test_type == '2':
        num_users = input("请输入每测试用户数 (默认50): ").strip()
        num_users = int(num_users) if num_users else 50
        num_tests = input("请输入测试次数 (默认100): ").strip()
        num_tests = int(num_tests) if num_tests else 100
        tester.stress_test(num_users, num_tests, overtime_mode)
    elif test_type == '3':
        tester.edge_case_test(overtime_mode)
    else:
        print("\n运行全部测试...")
        tester.random_test(5000, 8, overtime_mode)
        tester.stress_test(30, 50, overtime_mode)
        tester.edge_case_test(overtime_mode)


if __name__ == "__main__":
    main()
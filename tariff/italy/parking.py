from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Set
from collections import Counter

# ============ 费率常量（统一在此修改） ============
class ParkingRates:
    # 1档：短时票
    RATE_1_NAME = "1档(短时)"
    RATE_1_PRICE = 2.00
    RATE_1_DURATION = 60     # 分钟
    
    # 2档：中时票
    RATE_2_NAME = "2档(中时)"
    RATE_2_PRICE = 6.00
    RATE_2_DURATION = 360    # 分钟 (6小时)
    
    # 3档：日间票
    RATE_3_NAME = "日间票"
    RATE_3_PRICE = 12.00
    RATE_3_START_HOUR = 6
    RATE_3_START_MINUTE = 0
    RATE_3_EXPIRE_HOUR = 20
    RATE_3_EXPIRE_MINUTE = 0
    
    # 4档：夜间票
    RATE_4_NAME = "夜间票"
    RATE_4_PRICE = 20.00
    RATE_4_START_HOUR = 20
    RATE_4_START_MINUTE = 0
    RATE_4_EXPIRE_HOUR = 5
    RATE_4_EXPIRE_MINUTE = 59
    
    # 5档：24小时票
    RATE_5_NAME = "24小时票"
    RATE_5_PRICE = 24.00
    RATE_5_DURATION_HOURS = 24


class ParkingTicket:
    def __init__(self, name: str, price: float, expire_time: datetime):
        self.name = name
        self.price = price
        self.expire_time = expire_time
    
    def covers(self, end_time: datetime) -> bool:
        return self.expire_time >= end_time
    
    def __eq__(self, other):
        if not isinstance(other, ParkingTicket):
            return False
        return (self.name == other.name and 
                self.price == other.price and 
                self.expire_time == other.expire_time)
    
    def __hash__(self):
        return hash((self.name, self.price, self.expire_time))


class ParkingCalculator:
    def __init__(self, start_time: datetime, end_time: datetime):
        self.start = start_time
        self.end = end_time
        self.duration_minutes = int((end_time - start_time).total_seconds() / 60)
        self.duration_hours = self.duration_minutes / 60
        
        self.rate5_duration_minutes = ParkingRates.RATE_5_DURATION_HOURS * 60
        self.rate5_name = ParkingRates.RATE_5_NAME
        
        # 获取固定时长票的时长列表（1档、2档、24小时票）
        self.fixed_durations = [
            ParkingRates.RATE_1_DURATION,
            ParkingRates.RATE_2_DURATION,
            self.rate5_duration_minutes
        ]
    
    # ---------- 票种创建方法 ----------
    def _create_rate_1(self, purchase_time: datetime) -> ParkingTicket:
        expire = purchase_time + timedelta(minutes=ParkingRates.RATE_1_DURATION)
        return ParkingTicket(ParkingRates.RATE_1_NAME, ParkingRates.RATE_1_PRICE, expire)
    
    def _create_rate_2(self, purchase_time: datetime) -> ParkingTicket:
        expire = purchase_time + timedelta(minutes=ParkingRates.RATE_2_DURATION)
        return ParkingTicket(ParkingRates.RATE_2_NAME, ParkingRates.RATE_2_PRICE, expire)
    
    def _create_rate_3(self, purchase_time: datetime) -> Optional[ParkingTicket]:
        start_cutoff = purchase_time.replace(
            hour=ParkingRates.RATE_3_START_HOUR,
            minute=ParkingRates.RATE_3_START_MINUTE,
            second=0,
            microsecond=0
        )
        expire_cutoff = purchase_time.replace(
            hour=ParkingRates.RATE_3_EXPIRE_HOUR,
            minute=ParkingRates.RATE_3_EXPIRE_MINUTE,
            second=0,
            microsecond=0
        )
        if purchase_time < start_cutoff or purchase_time >= expire_cutoff:
            return None
        return ParkingTicket(ParkingRates.RATE_3_NAME, ParkingRates.RATE_3_PRICE, expire_cutoff)
    
    def _create_rate_4(self, purchase_time: datetime) -> Optional[ParkingTicket]:
        # 夜间票售卖时段：RATE_4_START(20:00) 跨日到 RATE_4_EXPIRE(次日05:59)
        # 20:00~23:59 购买 → 次日 05:59 到期
        # 00:00~05:58 购买 → 当天 05:59 到期
        # 05:59~20:00 之间不可买夜间票
        start_cutoff_today = purchase_time.replace(
            hour=ParkingRates.RATE_4_START_HOUR,
            minute=ParkingRates.RATE_4_START_MINUTE,
            second=0,
            microsecond=0
        )
        expire_cutoff_today = purchase_time.replace(
            hour=ParkingRates.RATE_4_EXPIRE_HOUR,
            minute=ParkingRates.RATE_4_EXPIRE_MINUTE,
            second=0,
            microsecond=0
        )
        if purchase_time >= start_cutoff_today:
            # 20:00~23:59
            expire = expire_cutoff_today + timedelta(days=1)
        elif purchase_time < expire_cutoff_today:
            # 00:00~05:58
            expire = expire_cutoff_today
        else:
            # 05:59~20:00 之间
            return None
        return ParkingTicket(ParkingRates.RATE_4_NAME, ParkingRates.RATE_4_PRICE, expire)
    
    def _create_rate_5(self, purchase_time: datetime) -> ParkingTicket:
        expire = purchase_time + timedelta(hours=ParkingRates.RATE_5_DURATION_HOURS)
        return ParkingTicket(ParkingRates.RATE_5_NAME, ParkingRates.RATE_5_PRICE, expire)
    
    def _get_available_tickets(self, current_time: datetime, include_time_window_tickets: bool = True) -> List[ParkingTicket]:
        """获取当前时间可购买的所有票
        
        include_time_window_tickets: 是否包含日间票、夜间票等按时窗生效的票种。
        1档/2档/24小时票等固定时长票始终包含。
        """
        tickets = []
        t1 = self._create_rate_1(current_time)
        if t1:
            tickets.append(t1)
        t2 = self._create_rate_2(current_time)
        if t2:
            tickets.append(t2)
        
        if include_time_window_tickets:
            t3 = self._create_rate_3(current_time)
            if t3:
                tickets.append(t3)
            t4 = self._create_rate_4(current_time)
            if t4:
                tickets.append(t4)
        
        t5 = self._create_rate_5(current_time)
        if t5:
            tickets.append(t5)
        return tickets
    
    def _is_fixed_duration_ticket(self, ticket: ParkingTicket) -> bool:
        """判断是否是固定时长的票（1档、2档、24小时票）"""
        return ticket.name in [ParkingRates.RATE_1_NAME, ParkingRates.RATE_2_NAME, ParkingRates.RATE_5_NAME]
    
    def _is_rate_5_ticket(self, ticket: ParkingTicket) -> bool:
        """判断一张票是否是24小时票"""
        return ticket.name == self.rate5_name

    # ---------- 核心算法 ----------
    def _find_all_solutions(self) -> List[Tuple[List[ParkingTicket], float]]:
        """
        统一 DFS 搜索：把所有票种视为不同面额的"钞票"，
        用尽可能少的张数凑齐停车总时长（允许合理超额）。
        返回所有可行组合（已按"费用优先，同费用再比张数"排序）。
        """
        demand_minutes = self.duration_minutes
        if demand_minutes <= 0:
            return [([], 0.0)]

        # 总累计允许超过需求 50%，但至少应能容纳单张 24h 票（1440min）的覆盖范围，
        # 防止小需求把所有短时票剪掉只剩 24h 兜底
        max_total_minutes = max(int(demand_minutes * 1.5), 1440)

        solutions: List[Tuple[List[ParkingTicket], float]] = []
        seen = set()

        def dfs(current_time: datetime, total_cost: float, tickets: List[ParkingTicket], depth: int):
            if depth > 6:
                return

            covered = int((current_time - self.start).total_seconds() / 60)
            if covered > max_total_minutes:
                return

            if current_time >= self.end:
                key = tuple(sorted((t.name, t.price) for t in tickets))
                if key not in seen:
                    seen.add(key)
                    solutions.append((tickets.copy(), total_cost))
                return

            # 按当前剩余需求动态计算单张票允许覆盖的最大时长。
            # 系数 3.0 允许 2档(360min) 覆盖 ~120min 的剩余空缺。
            remaining = int((self.end - current_time).total_seconds() / 60)
            single_limit = max(remaining * 3, 60)  # 至少60min，避免极小剩余时无解

            for ticket in self._get_available_tickets(current_time, True):
                if ticket.expire_time <= current_time:
                    continue
                new_covered = int((ticket.expire_time - self.start).total_seconds() / 60)
                if new_covered > max_total_minutes:
                    continue
                ticket_duration = int((ticket.expire_time - current_time).total_seconds() / 60)
                # 即使覆盖时长超过剩余，但只要不超过 single_limit 且不超总累计就允许
                if ticket_duration > single_limit:
                    continue
                tickets.append(ticket)
                dfs(ticket.expire_time, total_cost + ticket.price, tickets, depth + 1)
                tickets.pop()

        dfs(self.start, 0.0, [], 0)
        return solutions

    def calculate(self) -> Tuple[List[ParkingTicket], float, str, List[Tuple[List[ParkingTicket], float]]]:
        """计算最优停车方案（费用优先，同费用再比张数）。"""
        solutions = self._find_all_solutions()

        # 兜底：DFS 未找到任何方案时，用 24h 票直接铺满
        if not solutions:
            current = self.start
            tickets = []
            total = 0.0
            while current < self.end:
                t5 = self._create_rate_5(current)
                tickets.append(t5)
                total += t5.price
                current = t5.expire_time
            solutions = [(tickets, total)]

        # 按费用优先，同费用再比张数
        solutions.sort(key=lambda x: (x[1], len(x[0])))

        best_tickets, best_total = solutions[0]
        best_key = tuple(sorted((t.name, t.price) for t in best_tickets))

        # 备选方案：最多比最优贵 6 欧元，最多保留 5 条（含推荐）
        result = []
        for tickets, total in solutions:
            if total == best_total or total <= best_total + 6:
                key = tuple(sorted((t.name, t.price) for t in tickets))
                if key != best_key or total == best_total:
                    result.append((tickets, total))
            if len(result) >= 5:
                break
        # 确保推荐方案在首位
        if not result or result[0][1] != best_total:
            result = [(best_tickets, best_total)] + result
            # 去重
            seen_keys = {best_key}
            unique = [result[0]]
            for tickets, total in result[1:]:
                k = tuple(sorted((t.name, t.price) for t in tickets))
                if k not in seen_keys:
                    seen_keys.add(k)
                    unique.append((tickets, total))
            result = unique[:5]

        # 动态生成方案类型描述
        all_are_rate5 = all(self._is_rate_5_ticket(t) for t in best_tickets)
        has_rate5 = any(self._is_rate_5_ticket(t) for t in best_tickets)

        if len(best_tickets) == 1 and self._is_rate_5_ticket(best_tickets[0]):
            note = f"单张{self.rate5_name}"
        elif all_are_rate5:
            note = f"全部{self.rate5_name}"
        elif has_rate5:
            note = f"{self.rate5_name} + 短时组合"
        else:
            note = "短时组合"

        return best_tickets, best_total, note, result


def format_tickets_summary(tickets: List[ParkingTicket]) -> List[str]:
    # 按 (name, expire_str, price) 分组，相同名称且相同到期时间的票合并显示
    groups: List[Tuple[ParkingTicket, int]] = []
    seen_keys: Set[Tuple[str, str, float]] = set()
    for ticket in tickets:
        expire_str = ticket.expire_time.strftime('%Y-%m-%d %H:%M')
        key = (ticket.name, expire_str, ticket.price)
        if key in seen_keys:
            # 找到已有分组累加
            for idx, (t, c) in enumerate(groups):
                t_key = (t.name, t.expire_time.strftime('%Y-%m-%d %H:%M'), t.price)
                if t_key == key:
                    groups[idx] = (t, c + 1)
                    break
        else:
            seen_keys.add(key)
            groups.append((ticket, 1))
    
    result = []
    for ticket, count in groups:
        expire_str = ticket.expire_time.strftime('%Y-%m-%d %H:%M')
        if count == 1:
            result.append(f"{ticket.name} (EUR {ticket.price:.2f}, 有效期至 {expire_str})")
        else:
            result.append(f"{ticket.name} x {count}张 (EUR {ticket.price:.2f}/张, 有效期至 {expire_str})")
    
    return result


def format_solution_summary(tickets: List[ParkingTicket], total: float) -> str:
    ticket_counts = Counter(tickets)
    parts = []
    for ticket, count in sorted(ticket_counts.items(), key=lambda x: x[0].price):
        if count == 1:
            parts.append(ticket.name)
        else:
            parts.append(f"{ticket.name}x{count}")
    return " + ".join(parts) + f" = EUR {total:.2f}"


def get_datetime_from_user(prompt: str) -> datetime:
    print(f"\n{prompt}")
    while True:
        try:
            year = int(input("  年 (例如 2026): "))
            month = int(input("  月 (1-12): "))
            day = int(input("  日 (1-31): "))
            hour = int(input("  时 (0-23): "))
            minute = int(input("  分 (0-59): "))
            dt = datetime(year, month, day, hour, minute)
            return dt
        except ValueError as e:
            print(f"  [错误] 输入无效: {e}，请重新输入")
        except Exception as e:
            print(f"  [错误] 日期时间格式错误: {e}，请重新输入")


def main():
    print("=" * 60)
    print("          意大利停车费计算器")
    print("=" * 60)
    print("\n当前费率:")
    print(f"  1档: {ParkingRates.RATE_1_NAME} EUR {ParkingRates.RATE_1_PRICE:.2f} / {ParkingRates.RATE_1_DURATION}分钟")
    print(f"  2档: {ParkingRates.RATE_2_NAME} EUR {ParkingRates.RATE_2_PRICE:.2f} / {ParkingRates.RATE_2_DURATION}分钟")
    print(f"  3档: {ParkingRates.RATE_3_NAME} EUR {ParkingRates.RATE_3_PRICE:.2f} / 当天{ParkingRates.RATE_3_EXPIRE_HOUR}:{ParkingRates.RATE_3_EXPIRE_MINUTE:02d}到期 "
          f"({ParkingRates.RATE_3_START_HOUR}:{ParkingRates.RATE_3_START_MINUTE:02d}起售)")
    print(f"  4档: {ParkingRates.RATE_4_NAME} EUR {ParkingRates.RATE_4_PRICE:.2f} / 次日{ParkingRates.RATE_4_EXPIRE_HOUR}:{ParkingRates.RATE_4_EXPIRE_MINUTE:02d}到期 "
          f"({ParkingRates.RATE_4_START_HOUR}:{ParkingRates.RATE_4_START_MINUTE:02d}起售)")
    print(f"  5档: {ParkingRates.RATE_5_NAME} EUR {ParkingRates.RATE_5_PRICE:.2f} / {ParkingRates.RATE_5_DURATION_HOURS}小时")
    print("=" * 60)
    
    while True:
        start = get_datetime_from_user("请输入停车开始时间:")
        end = get_datetime_from_user("请输入停车结束时间:")
        
        if end <= start:
            print("\n[错误] 结束时间必须晚于开始时间，请重新输入")
            continue
        
        calc = ParkingCalculator(start, end)
        best_tickets, best_total, note, alternatives = calc.calculate()
        
        print("\n" + "=" * 60)
        print("计算结果")
        print("=" * 60)
        print(f"  开始时间: {start.strftime('%Y-%m-%d %H:%M')}")
        print(f"  结束时间: {end.strftime('%Y-%m-%d %H:%M')}")
        print(f"  总时长:   {calc.duration_minutes} 分钟 ({calc.duration_hours:.1f} 小时)")
        print(f"  方案类型: {note}")
        print("\n  [推荐方案]")
        
        if best_tickets:
            summary_lines = format_tickets_summary(best_tickets)
            for i, line in enumerate(summary_lines, 1):
                print(f"    {i}. {line}")
            print(f"\n  最优费用: EUR {best_total:.2f}")
        else:
            print("  无可行方案")
        
        if len(alternatives) > 1:
            print("\n  [其他可行方案 (供验证对比)]")
            print("  " + "-" * 56)
            best_key = tuple(sorted((t.name, t.price) for t in best_tickets))
            for i, (tickets, total) in enumerate(alternatives, 1):
                key1 = tuple(sorted((t.name, t.price) for t in tickets))
                is_best = (total == best_total and key1 == best_key)
                marker = " [推荐]" if is_best else ""
                summary = format_solution_summary(tickets, total)
                print(f"    {i}. {summary}{marker}")
        elif len(alternatives) == 1 and best_tickets:
            print("\n  [注] 只有这一种可行方案")
        
        print("=" * 60)
        
        again = input("\n是否继续计算其他停车时段？(y/n): ").strip().lower()
        if again not in ['y', 'yes', '是']:
            print("\n感谢使用，再见！")
            break


if __name__ == "__main__":
    main()
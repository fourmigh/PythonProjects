from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from collections import Counter

# ============ 费率常量（统一在此修改） ============
class ParkingRates:
    # 1档：短时票
    RATE_1_PRICE = 2.00      # 欧元
    RATE_1_DURATION = 60     # 分钟
    
    # 2档：中时票
    RATE_2_PRICE = 6.00
    RATE_2_DURATION = 360    # 分钟 (6小时)
    
    # 3档：日间票
    RATE_3_PRICE = 12.00
    RATE_3_START_HOUR = 6    # 6:00 AM 起售（小时部分）
    RATE_3_START_MINUTE = 0  # 6:00 AM 起售（分钟部分）
    RATE_3_EXPIRE_HOUR = 20  # 8:00 PM 到期 (24小时制)
    RATE_3_EXPIRE_MINUTE = 0 # 20:00 到期（分钟部分）
    
    # 4档：夜间票
    RATE_4_PRICE = 20.00
    RATE_4_START_HOUR = 20   # 8:00 PM 起售
    RATE_4_START_MINUTE = 0  # 8:00 PM 起售（分钟部分）
    RATE_4_EXPIRE_HOUR = 5   # 次日 5:59 AM 到期 (小时部分)
    RATE_4_EXPIRE_MINUTE = 59
    
    # 5档：24小时票
    RATE_5_PRICE = 24.00
    RATE_5_DURATION_HOURS = 24


class ParkingTicket:
    """停车票实体"""
    def __init__(self, name: str, price: float, expire_time: datetime):
        self.name = name
        self.price = price
        self.expire_time = expire_time
    
    def covers(self, end_time: datetime) -> bool:
        """检查此票是否覆盖到 end_time"""
        return self.expire_time >= end_time
    
    def __eq__(self, other):
        """名称、价格、有效期都相同才视为相同票"""
        if not isinstance(other, ParkingTicket):
            return False
        return (self.name == other.name and 
                self.price == other.price and 
                self.expire_time == other.expire_time)
    
    def __hash__(self):
        return hash((self.name, self.price, self.expire_time))


class ParkingCalculator:
    """停车费计算器"""
    
    def __init__(self, start_time: datetime, end_time: datetime):
        """
        :param start_time: 停车开始时间（含日期）
        :param end_time:   停车结束时间（含日期）
        """
        self.start = start_time
        self.end = end_time
        self.duration_minutes = int((end_time - start_time).total_seconds() / 60)
    
    def _create_rate_1(self, purchase_time: datetime) -> ParkingTicket:
        """购买1档票（60分钟）"""
        expire = purchase_time + timedelta(minutes=ParkingRates.RATE_1_DURATION)
        return ParkingTicket("1档(短时)", ParkingRates.RATE_1_PRICE, expire)
    
    def _create_rate_2(self, purchase_time: datetime) -> ParkingTicket:
        """购买2档票（360分钟/6小时）"""
        expire = purchase_time + timedelta(minutes=ParkingRates.RATE_2_DURATION)
        return ParkingTicket("2档(中时)", ParkingRates.RATE_2_PRICE, expire)
    
    def _create_rate_3(self, purchase_time: datetime) -> Optional[ParkingTicket]:
        """
        购买日间票（当天20:00到期），需在 6:00 - 19:59 之间购买
        """
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
        
        expire = expire_cutoff
        return ParkingTicket("日间票", ParkingRates.RATE_3_PRICE, expire)
    
    def _create_rate_4(self, purchase_time: datetime) -> Optional[ParkingTicket]:
        """
        购买夜间票（次日5:59到期），需在 20:00 之后购买
        """
        start_cutoff = purchase_time.replace(
            hour=ParkingRates.RATE_4_START_HOUR,
            minute=ParkingRates.RATE_4_START_MINUTE,
            second=0,
            microsecond=0
        )
        
        if purchase_time < start_cutoff:
            return None
        
        expire = purchase_time.replace(
            hour=ParkingRates.RATE_4_EXPIRE_HOUR,
            minute=ParkingRates.RATE_4_EXPIRE_MINUTE,
            second=0,
            microsecond=0
        ) + timedelta(days=1)
        return ParkingTicket("夜间票", ParkingRates.RATE_4_PRICE, expire)
    
    def _create_rate_5(self, purchase_time: datetime) -> ParkingTicket:
        """购买24小时票"""
        expire = purchase_time + timedelta(hours=ParkingRates.RATE_5_DURATION_HOURS)
        return ParkingTicket("24小时票", ParkingRates.RATE_5_PRICE, expire)
    
    def _get_all_single_tickets(self) -> List[ParkingTicket]:
        """获取所有在 start 时刻可购买且能覆盖到 end 的单张票"""
        tickets = []
        
        t1 = self._create_rate_1(self.start)
        if t1.covers(self.end):
            tickets.append(t1)
        
        t2 = self._create_rate_2(self.start)
        if t2.covers(self.end):
            tickets.append(t2)
        
        t3 = self._create_rate_3(self.start)
        if t3 and t3.covers(self.end):
            tickets.append(t3)
        
        t4 = self._create_rate_4(self.start)
        if t4 and t4.covers(self.end):
            tickets.append(t4)
        
        t5 = self._create_rate_5(self.start)
        if t5.covers(self.end):
            tickets.append(t5)
        
        return tickets
    
    def _find_combination(self) -> Optional[Tuple[List[ParkingTicket], float]]:
        """
        尝试用多张票组合覆盖停车时段
        优先原则：1) 总价格最低  2) 价格相同则票数最少
        """
        best = None
        
        def dfs(current_time: datetime, total_cost: float, used_tickets: List[ParkingTicket]):
            nonlocal best
            
            if current_time >= self.end:
                if best is None:
                    best = (used_tickets.copy(), total_cost)
                else:
                    best_cost = best[1]
                    best_count = len(best[0])
                    if total_cost < best_cost or (total_cost == best_cost and len(used_tickets) < best_count):
                        best = (used_tickets.copy(), total_cost)
                return
            
            if best and total_cost > best[1]:
                return
            
            if best and total_cost == best[1] and len(used_tickets) >= len(best[0]):
                return
            
            for ticket_creator in [
                self._create_rate_5,
                self._create_rate_4,
                self._create_rate_3,
                self._create_rate_2,
                self._create_rate_1
            ]:
                ticket = ticket_creator(current_time)
                if ticket and ticket.expire_time > current_time:
                    used_tickets.append(ticket)
                    dfs(ticket.expire_time, total_cost + ticket.price, used_tickets)
                    used_tickets.pop()
        
        dfs(self.start, 0.0, [])
        return best
    
    def calculate(self) -> Tuple[List[ParkingTicket], float, str]:
        """计算最优停车方案"""
        single_tickets = self._get_all_single_tickets()
        if single_tickets:
            best_single = min(single_tickets, key=lambda t: (t.price, t.expire_time))
            return [best_single], best_single.price, "单张票覆盖"
        
        result = self._find_combination()
        if result:
            tickets, total = result
            return tickets, total, "多张票组合"
        
        total_tickets = []
        current = self.start
        total_cost = 0.0
        while current < self.end:
            t5 = self._create_rate_5(current)
            total_tickets.append(t5)
            total_cost += t5.price
            current = t5.expire_time
        return total_tickets, total_cost, "多张24小时票组合"


def format_tickets_summary(tickets: List[ParkingTicket]) -> List[str]:
    """
    将票列表按购买顺序列出，对完全相同的票（同名称、同价格、同时到期）合并显示数量
    """
    ticket_counter = Counter(tickets)
    
    seen = set()
    sorted_items = []
    for ticket in tickets:
        if ticket not in seen:
            seen.add(ticket)
            sorted_items.append((ticket, ticket_counter[ticket]))
    
    result = []
    for ticket, count in sorted_items:
        expire_str = ticket.expire_time.strftime('%Y-%m-%d %H:%M')
        if count == 1:
            result.append(f"{ticket.name} (EUR {ticket.price:.2f}, 有效期至 {expire_str})")
        else:
            result.append(f"{ticket.name} x {count}张 (EUR {ticket.price:.2f}/张, 有效期至 {expire_str})")
    
    return result


def get_datetime_from_user(prompt: str) -> datetime:
    """交互式获取用户输入的日期时间"""
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
    """主程序 - 交互式停车费计算器"""
    print("=" * 60)
    print("          意大利停车费计算器")
    print("=" * 60)
    print("\n当前费率:")
    print(f"  1档: EUR {ParkingRates.RATE_1_PRICE:.2f} / {ParkingRates.RATE_1_DURATION}分钟")
    print(f"  2档: EUR {ParkingRates.RATE_2_PRICE:.2f} / {ParkingRates.RATE_2_DURATION}分钟 (6小时)")
    print(f"  3档(日间): EUR {ParkingRates.RATE_3_PRICE:.2f} / 当天{ParkingRates.RATE_3_EXPIRE_HOUR}:{ParkingRates.RATE_3_EXPIRE_MINUTE:02d}到期 "
          f"({ParkingRates.RATE_3_START_HOUR}:{ParkingRates.RATE_3_START_MINUTE:02d}起售)")
    print(f"  4档(夜间): EUR {ParkingRates.RATE_4_PRICE:.2f} / 次日{ParkingRates.RATE_4_EXPIRE_HOUR}:{ParkingRates.RATE_4_EXPIRE_MINUTE:02d}到期 "
          f"({ParkingRates.RATE_4_START_HOUR}:{ParkingRates.RATE_4_START_MINUTE:02d}起售)")
    print(f"  5档(24小时): EUR {ParkingRates.RATE_5_PRICE:.2f} / 24小时")
    print("=" * 60)
    
    while True:
        start = get_datetime_from_user("请输入停车开始时间:")
        end = get_datetime_from_user("请输入停车结束时间:")
        
        if end <= start:
            print("\n[错误] 结束时间必须晚于开始时间，请重新输入")
            continue
        
        calc = ParkingCalculator(start, end)
        tickets, total, note = calc.calculate()
        
        print("\n" + "=" * 60)
        print("计算结果")
        print("=" * 60)
        print(f"  开始时间: {start.strftime('%Y-%m-%d %H:%M')}")
        print(f"  结束时间: {end.strftime('%Y-%m-%d %H:%M')}")
        print(f"  总时长:   {calc.duration_minutes} 分钟 ({calc.duration_minutes/60:.1f} 小时)")
        print(f"  方案:     {note}")
        print("\n  推荐购票:")
        
        summary_lines = format_tickets_summary(tickets)
        for i, line in enumerate(summary_lines, 1):
            print(f"    {i}. {line}")
        
        print(f"\n  总费用: EUR {total:.2f}")
        print("=" * 60)
        
        again = input("\n是否继续计算其他停车时段？(y/n): ").strip().lower()
        if again not in ['y', 'yes', '是']:
            print("\n感谢使用，再见！")
            break


if __name__ == "__main__":
    main()
# 停车场（自行车停车库）预订系统

一个基于 Python + Tkinter 的停车场/自行车停车库时段预订与车位分配模拟系统。

系统把一天划分为若干等长时段，用户预订连续时段；用户到达时，系统用**位图冲突检测**为其分配具体车位，并通过随机起点扫描分散车位使用。项目同时提供图形界面（时段热力表 + 车位占用模拟窗口）、命令行版本以及自动化压力/随机测试脚本。

## 功能特性

- **按时段预订**：支持选择一个连续时段区间预订，自动校验时段是否已过去、已满或无法满足连续需求。
- **车位分配**：到达时用车位位图找无冲突空位，随机起点环形扫描，不遍历订单
  - `arrive`：唯一的到达分配入口；
  - 正常路径复杂度 `O(总车位数)` 次整数与运算。
- **位图算法**：用整数位图表示某个车位/订单占用的时段，冲突检测退化为位与运算，性能高。
- **预订即保障**：`book` 保证每个时段的预订总数不超过总车位数；用户按开始时段顺序到达，因此任选一个无冲突车位都不会挤占后续预订用户，无需在到达时模拟未来订单。
- **超时处理**：支持用户超时续停、超时占用可视化、强制离场以及失败原因详细分析。
- **图形界面**：
  - 主窗口按时段展示空闲/紧张/已满状态，点击选择预订区间；
  - 车位状态窗口支持手动/自动推进时间、查看每个车位的占用与超时情况；
  - 可运行时重置车位数与时段数。
- **测试工具**：随机测试、压力测试、边界测试，并统计到达分配成功率与耗时。

相关文档：

- `docs/需求文档.md` —— 从代码反推的需求说明
- `docs/实现方法文档.md` —— 当前实现的详细方法与疑点清单

## 项目结构

```
parking_system/
├── __init__.py                 # 包级导出（核心类与 UI 类）
├── core/                       # 核心业务逻辑（与界面无关）
│   ├── __init__.py
│   ├── config.py               # AllocationWeights：诊断路径常量
│   ├── models.py               # User、UserStatus、TimeSlotStatus 数据模型
│   ├── utils.py               # 位图计算与时段重叠判断
│   └── parking_system.py       # ParkingSystem：预订、到达、离开、时间推进
├── ui/                         # Tkinter 图形界面
│   ├── __init__.py
│   ├── shared_utils.py         # 颜色、图例、时间格式化、通用 UI 组件
│   ├── system_proxy.py         # ParkingSystemProxy 单例代理与 UI 刷新回调
│   ├── parkinggui.py           # 主窗口：时段选择与预订
│   └── spot_status_window.py   # 车位状态/时间模拟窗口
├── test_parking_system.py      # 随机、压力、边界测试脚本
└── .gitignore
```

## 快速开始

环境要求：Python 3.10+，仅使用标准库（`tkinter`、`dataclasses`、`typing` 等），无需安装第三方依赖。

启动图形界面：

```bash
python ui/parkinggui.py
```

运行测试脚本（按提示选择测试类型、分配策略和超时模式）：

```bash
python test_parking_system.py
```

> 请在 `parking_system` 目录下执行命令。`ui` 下的脚本会自动把项目根目录加入 `sys.path`。

## 核心概念

### 时段与时间点

- 一天被均分为 `num_slots` 个时段，每个时段 `24 * 60 // num_slots` 分钟。
- 模拟时间用 `time_point` 表示，取值范围 `0 ~ 2 * num_slots`：
  - 偶数表示「某时段开始前」，奇数表示「某时段结束后」；
  - 时段编号从 1 开始，`past_slots = time_point // 2`。

### 位图（Bitmap）

`core/utils.py` 中的 `calculate_bitmap` 把连续时段转换为整数位图：

```python
bitmap = ((1 << (end - start + 1)) - 1) << start
```

第 `i` 位为 1 表示时段 `i` 被占用。两个订单是否冲突只需 `bitmap_a & bitmap_b`；车位占用状态缓存在 `spot_bitmap` 中，便于快速比较。

### 分配算法

到达分配只做一件事：找到与用户占用时段不冲突的车位。

1. `user_bitmap = calculate_bitmap(user.slots)`；
2. 随机选一个起点，环形扫描全部车位；
3. 第一个满足 `spot_bitmap[spot] & user_bitmap == 0` 的车位即为结果。

**为什么不需要遍历订单**：用户严格按 `slots[0]` 的先后到场，任何与当前用户时段重叠的已分配用户都必然覆盖当前用户的起始时段。所以

```
剩余可用车位数 = 总车位数 - 起始时段同时在场人数
```

与历史如何选位无关。只要 `book` 保证每个时段的预订总数 ≤ 总车位数，任选一个无冲突车位都不会导致后续已预订用户无处可停。因此到达路径不需要订单模拟或打分，相关旧模块已删除。

超时续停会突破「每时段预订数 ≤ 总车位数」这一前提，此时不保证一定有车位，属于策略层面需要预留缓冲位或强制挪车才能解决的问题。

### 主要接口

```python
from core import ParkingSystem

system = ParkingSystem(total_spots=100, num_slots=24)

ok, msg = system.book(user_id=1, slots=[3, 4, 5])   # 预订连续时段
ok, msg = system.arrive(1, time_slot=4)              # 到达并随机分配车位
ok, msg = system.depart(1, time_slot=9)              # 离开
system.advance_time(2)                               # 推进模拟时间
status = system.get_slot_status(3)                   # 查询时段状态
```

`ui.system_proxy.ParkingSystemProxy` 是对 `ParkingSystem` 的单例封装，额外提供 UI 刷新回调；GUI 只与代理交互。

## 测试

`test_parking_system.py` 中的 `ParkingSystemAdvancedTester` 提供：

- `random_test`：随机预订组合，统计成功率与耗时；
- `stress_test`：高用户数压力测试；
- `edge_case_test`：边界场景；
- 失败案例分析：输出车位占用、超时用户、冲突时段与推荐车位等详细信息。

程序退出前可调用 `ParkingSystem.print_perf_stats()` 查看各核心函数调用次数与平均耗时（由 `_profile` 装饰器统计）。

## 备注

- 系统当前以「车位数量 + 时段数量」为容量模型，同一车位的时段占用记录保存在 `spot_schedule`。
- `occupied[slot-1]` 表示该时段的预订总数（含已到场用户），只在 `book` 时递增，到达与离开都不减少，用于维持「每时段预订数 ≤ 总车位数」的不变量。
- 所有中文注释与提示文本位于源码中。

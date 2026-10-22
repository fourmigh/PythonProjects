# 停车场（自行车停车库）预订系统

一个基于 Python + Tkinter 的停车场/自行车停车库时段预订与车位分配模拟系统。

系统把一天划分为若干等长时段，用户预订连续时段；用户到达时，系统根据**位图冲突检测**与**多因子打分**为其分配具体车位。项目同时提供图形界面（时段热力表 + 车位占用模拟窗口）、命令行版本以及自动化压力/随机测试脚本。

## 功能特性

- **按时段预订**：支持选择一个连续时段区间预订，自动校验时段是否已过去、已满或无法满足连续需求。
- **车位分配**：提供两种到达分配策略
  - `arrive`：简单分配，取第一个不会影响未来用户的车位；
  - `arrive_smart`：智能分配，基于权重打分选择最优车位。
- **位图算法**：用整数位图表示某个车位/订单占用的时段，冲突检测退化为位与运算，性能高。
- **未来用户保护**：分配车位时检查是否会挤占未来已预订用户的可用车位（可配置快速模式）。
- **超时处理**：支持用户超时续停、超时占用可视化、强制离场以及失败原因详细分析。
- **图形界面**：
  - 主窗口按时段展示空闲/紧张/已满状态，点击选择预订区间；
  - 车位状态窗口支持手动/自动推进时间、查看每个车位的占用与超时情况；
  - 可运行时重置车位数与时段数。
- **测试工具**：随机测试、压力测试、边界测试，并对比简单分配与智能分配的成功率和耗时。

## 项目结构

```
parking_system/
├── __init__.py                 # 包级导出（核心类与 UI 类）
├── core/                       # 核心业务逻辑（与界面无关）
│   ├── __init__.py
│   ├── config.py               # AllocationWeights：分配算法全部权重/阈值
│   ├── models.py               # User、UserStatus、TimeSlotStatus 数据模型
│   ├── utils.py                # 位图计算与时段重叠判断
│   ├── allocation.py           # AllocationManager：智能车位分配与打分
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

`core/allocation.py` 中的 `AllocationManager.allocate_smart` 工作流程：

1. 生成与当前用户时段可能冲突的未来订单位图；
2. 过滤掉与未来订单冲突的车位；
3. 检查分配后未来用户是否仍有车位可用；
4. 对候选车位计算得分，取最高分（同分取编号较小者）。

打分维度与权重集中在 `core/config.py` 的 `AllocationWeights`，包括：

| 维度 | 说明 |
| --- | --- |
| 连续性与相邻空闲 | 左右两侧空闲分别加分 |
| 到达紧迫性 | 立即/下一/再下一时段到达给予不同奖励 |
| 时长匹配 | 长时订单关注后续空闲，短时订单偏向角落车位 |
| 当前空闲 | 与用户时段完全不冲突时加分 |
| 超时风险 | 延长一个时段后仍有冲突则扣分 |
| 冲突惩罚 | 未来冲突给予极高惩罚 |

若严格分配失败，会依次降级：忽略「未来用户可满足」检查 → 直接选择第一个空闲车位。

### 主要接口

```python
from core import ParkingSystem

system = ParkingSystem(total_spots=100, num_slots=24)

ok, msg = system.book(user_id=1, slots=[3, 4, 5])   # 预订连续时段
ok, msg = system.arrive_smart(1, time_slot=4)        # 到达并智能分配车位
ok, msg = system.depart(1, time_slot=9)              # 离开
system.advance_time(2)                               # 推进模拟时间
status = system.get_slot_status(3)                   # 查询时段状态
```

`ui.system_proxy.ParkingSystemProxy` 是对 `ParkingSystem` 的单例封装，额外提供 UI 刷新回调；GUI 只与代理交互。

## 测试

`test_parking_system.py` 中的 `ParkingSystemAdvancedTester` 提供：

- `random_test`：随机预订组合，对比成功率与耗时；
- `stress_test`：高用户数压力测试；
- `edge_case_test`：边界场景；
- 失败案例分析：输出车位占用、超时用户、冲突时段与推荐车位等详细信息。

程序退出前可调用 `ParkingSystem.print_perf_stats()` 查看各核心函数调用次数与平均耗时（由 `_profile` 装饰器统计）。

## 备注

- 系统当前以「车位数量 + 时段数量」为容量模型，同一车位的时段占用记录保存在 `spot_schedule`。
- 所有中文注释与提示文本位于源码中；修改分配效果时优先调整 `core/config.py`，而不是改算法主体。

"""大楼属性：楼型、容量、人群构成与由楼型决定的客流结构。

一次仿真只针对一栋楼。楼型不参与电梯调度，它只决定「画像长什么样」：
这栋楼能住多少人（入住率 × 每层单元数 × 每单元人数）、住客与访客的比例、
四类人群（男/女/儿童/轮椅）各占多少、以及轮椅与儿童的等候与结伴习惯。
画像一旦创建并落盘，楼型就再也不会影响它——与「随机只发生在创建时」的
既有原则一致。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

RESIDENTIAL = "residential"
OFFICE = "office"
BUILDING_TYPES = (RESIDENTIAL, OFFICE)

#: 乘客人群分类。顺序固定，图例、预览与批量分配都按这个顺序展示。
MALE = "male"
FEMALE = "female"
CHILD = "child"
WHEELCHAIR = "wheelchair"
PEOPLE_KINDS = (MALE, FEMALE, CHILD, WHEELCHAIR)

#: 大堂层。住宅住客出门经大堂下楼，商务员工经大堂上楼。
LOBBY_FLOOR = 1

TARGET_LOBBY = "lobby"
TARGET_OFFICE = "office"

#: UI 在总人数超过此值时给出「仿真会变慢」的提示，但不截断生成量。
POPULATION_WARN = 500

#: 住宅楼人群构成：儿童与轮椅合计约一成。
RESIDENTIAL_MIX: dict[str, float] = {
    MALE: 0.45,
    FEMALE: 0.45,
    CHILD: 0.07,
    WHEELCHAIR: 0.03,
}

#: 商务楼人群构成：以办公人群为绝对主体，儿童与轮椅都很少。
OFFICE_MIX: dict[str, float] = {
    MALE: 0.60,
    FEMALE: 0.37,
    CHILD: 0.01,
    WHEELCHAIR: 0.02,
}

#: 楼型缺省人群构成。字段默认值用住宅楼，与 resident_share 的缺省一致。
DEFAULT_MIX: dict[str, float] = dict(RESIDENTIAL_MIX)

MIX_PRESETS: dict[str, dict[str, float]] = {
    RESIDENTIAL: RESIDENTIAL_MIX,
    OFFICE: OFFICE_MIX,
}


def default_mix() -> dict[str, float]:
    """返回一份全新的缺省人群构成，避免可变默认值被就地改写。"""
    return dict(DEFAULT_MIX)


def _normalize_mix(value: object, fallback: dict[str, float]) -> dict[str, float]:
    """把任意输入收敛成四类占比，且四类之和恒为 1。

    四个占比是各自独立输入的，不必凑成 100，这里统一归一化，因此用户
    拖动任意一个滑块都不会让总人数或类别数发生跳变。
    """
    source = value if isinstance(value, dict) else {}
    out: dict[str, float] = {}
    for kind in PEOPLE_KINDS:
        raw = source.get(kind, fallback.get(kind, 0.0))
        try:
            share = float(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            share = 0.0
        out[kind] = max(0.0, share)
    total = sum(out.values())
    if total <= 0:
        out = {kind: float(fallback.get(kind, 0.0)) for kind in PEOPLE_KINDS}
        total = sum(out.values()) or 1.0
    return {kind: round(out[kind] / total, 4) for kind in PEOPLE_KINDS}


def _coerce_float(value: object, fallback: float, low: float, high: float) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        number = fallback
    return min(high, max(low, number))


@dataclass(frozen=True)
class Population:
    """一栋楼应有的乘客规模。"""

    units: int  # 除去大堂层后可分配的单元总数
    occupied: int  # 已入驻单元数
    residents: int  # 住客/员工数
    visitors: int  # 访客数
    #: 四类人群的确切人数，四类之和恒等于 total，供 UI 直接预览
    mix: dict[str, int] = field(default_factory=dict, hash=False)

    @property
    def total(self) -> int:
        return self.residents + self.visitors


@dataclass(frozen=True)
class Building:
    """一栋楼：楼型 + 容量参数 + 住客占比（其余为访客）+ 人群构成。

    住宅的「单元」是一户，商务的「单元」是一家公司，因此每单元人数
    区间在两类楼之间相差一个数量级。

    people_mix 是 dict，frozen dataclass 生成的 __hash__ 会因 dict 不可哈希
    而抛 TypeError，因此用 hash=False 把它排除出哈希。代价是不同人群构成
    的两栋楼哈希相同——这是合法的（哈希冲突允许），而 == 仍能正确区分。
    """

    kind: str = RESIDENTIAL
    resident_share: float = 0.90
    occupancy_rate: float = 0.85
    units_per_floor: int = 4
    occupants_per_unit: tuple[int, int] = (2, 4)
    # 默认留空，由 normalized() 按楼型回退到 MIX_PRESETS[kind]。这里不能
    # 填死一份住宅比例，否则 Building(OFFICE) 这种直接构造会静默沿用住宅
    # 构成，from_json 的回退路径和直接构造的路径就会给出不同结果。
    people_mix: dict[str, float] = field(default_factory=dict, hash=False)
    #: 轮椅乘客愿意等更久：放弃阈值乘以该倍数
    wheelchair_patience: float = 1.5
    #: 儿童出行必须有成人陪同，结伴人数不低于该值
    child_min_companions: int = 2
    #: 儿童更容易等不下去：放弃阈值乘以该倍数
    child_patience: float = 0.6

    def normalized(self) -> Building:
        kind = self.kind if self.kind in BUILDING_TYPES else RESIDENTIAL
        default = BUILDING_PRESETS.get(kind, DEFAULT_BUILDING)
        try:
            share = float(self.resident_share)
        except (TypeError, ValueError):
            share = default.resident_share
        try:
            rate = float(self.occupancy_rate)
        except (TypeError, ValueError):
            rate = default.occupancy_rate
        try:
            units = int(round(float(self.units_per_floor)))
        except (TypeError, ValueError):
            units = default.units_per_floor
        try:
            companions = int(round(float(self.child_min_companions)))
        except (TypeError, ValueError):
            companions = default.child_min_companions
        low, high = _coerce_range(self.occupants_per_unit, default.occupants_per_unit)
        return Building(
            kind,
            round(min(1.0, max(0.0, share)), 4),
            round(min(1.0, max(0.0, rate)), 4),
            max(0, units),
            (low, high),
            # 每次都构造全新 dict：frozen 挡不住 dict 的就地改写
            _normalize_mix(self.people_mix, MIX_PRESETS.get(kind, DEFAULT_MIX)),
            round(
                _coerce_float(
                    self.wheelchair_patience, default.wheelchair_patience, 0.1, 10.0
                ),
                3,
            ),
            max(1, min(20, companions)),
            round(
                _coerce_float(self.child_patience, default.child_patience, 0.1, 10.0),
                3,
            ),
        )

    @property
    def visitor_share(self) -> float:
        return round(1.0 - self.normalized().resident_share, 4)

    def mix_for(self, kind: str) -> float:
        """某一类人群在新建画像里应占的比例。"""
        return self.normalized().people_mix.get(kind, 0.0)

    def category_counts(self, total: int) -> dict[str, int]:
        """把总人数按人群构成拆成四类的确切人数。

        用最大余数法分配，因此四类之和恒等于 total——UI 预览多少人，批量
        生成就是多少人，不存在四舍五入后凑不齐的零头。
        """
        people = max(0, int(total))
        mix = self.normalized().people_mix
        exact = {kind: people * mix.get(kind, 0.0) for kind in PEOPLE_KINDS}
        counts = {kind: int(exact[kind]) for kind in PEOPLE_KINDS}
        left = people - sum(counts.values())
        if left > 0:
            # 先按小数部分降序，同分时按 PEOPLE_KINDS 顺序，保证确定性
            order = sorted(
                PEOPLE_KINDS,
                key=lambda k: (-(exact[k] - counts[k]), PEOPLE_KINDS.index(k)),
            )
            for kind in order[:left]:
                counts[kind] += 1
        return counts

    def capacity(self, floors: int) -> int:
        """可分配单元总数：1 层大堂不设单元。"""
        return max(0, int(floors) - LOBBY_FLOOR) * self.units_per_floor

    def population(self, floors: int, base_seed: int) -> Population:
        """按容量算出这栋楼的住客、访客与四类人群数量。

        随机只来自「每单元人数」这一项，且用参数指纹定种，因此同一栋楼
        在任何时刻、任何界面里算出的规模都完全一致——UI 预览即生成结果。
        """
        from core.profiles import derive_seed  # 局部导入以避开与 profiles 的循环依赖

        b = self.normalized()
        units = b.capacity(floors)
        occupied = int(round(units * b.occupancy_rate))
        fingerprint = (
            f"{b.kind}|{int(floors)}|{b.units_per_floor}|{b.occupancy_rate}"
            f"|{b.occupants_per_unit[0]}-{b.occupants_per_unit[1]}|{b.resident_share}"
        )
        rng = random.Random(derive_seed(base_seed, "population", fingerprint))
        lo, hi = b.occupants_per_unit
        residents = sum(rng.randint(lo, hi) for _ in range(occupied))
        visitors = 0
        if b.resident_share > 0:
            visitors = int(round(residents * b.visitor_share / b.resident_share))
        return Population(
            units, occupied, residents, visitors, b.category_counts(residents + visitors)
        )

    def to_json(self) -> dict:
        return {
            "kind": self.kind,
            "resident_share": self.resident_share,
            "occupancy_rate": self.occupancy_rate,
            "units_per_floor": self.units_per_floor,
            "occupants_per_unit": list(self.occupants_per_unit),
            "people_mix": dict(self.people_mix),
            "wheelchair_patience": self.wheelchair_patience,
            "child_min_companions": self.child_min_companions,
            "child_patience": self.child_patience,
        }

    @staticmethod
    def from_json(data: object) -> Building:
        """缺键或数据损坏时回退到该楼型的预设，保证旧 JSON 仍可加载。"""
        if not isinstance(data, dict):
            return DEFAULT_BUILDING
        try:
            kind = str(data.get("kind", RESIDENTIAL))
            default = BUILDING_PRESETS.get(kind, DEFAULT_BUILDING)
            return Building(
                kind=kind,
                resident_share=float(data.get("resident_share", default.resident_share)),
                occupancy_rate=float(data.get("occupancy_rate", default.occupancy_rate)),
                units_per_floor=int(data.get("units_per_floor", default.units_per_floor)),
                occupants_per_unit=tuple(
                    data.get("occupants_per_unit", default.occupants_per_unit)
                ),
                people_mix=dict(
                    data.get("people_mix", MIX_PRESETS.get(kind, DEFAULT_MIX))
                ),
                wheelchair_patience=float(
                    data.get("wheelchair_patience", default.wheelchair_patience)
                ),
                child_min_companions=int(
                    data.get("child_min_companions", default.child_min_companions)
                ),
                child_patience=float(
                    data.get("child_patience", default.child_patience)
                ),
            ).normalized()
        except (TypeError, ValueError):
            return DEFAULT_BUILDING


def _coerce_range(value: object, fallback: tuple[int, int]) -> tuple[int, int]:
    """把任意输入收敛成一个有序且两端 ≥1 的人数区间。"""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        bounds = [int(value)]
    else:
        try:
            bounds = [int(x) for x in value]  # type: ignore[union-attr]
        except (TypeError, ValueError):
            bounds = []
    if not bounds:
        bounds = list(fallback)
    if len(bounds) == 1:
        bounds.append(bounds[0])
    low = max(1, min(bounds[0], bounds[1]))
    high = max(1, max(bounds[0], bounds[1]))
    return low, high


#: 楼型预设：住宅楼以住客为绝对主体，商务楼以访客为绝对主体。
#: units_per_floor 在住宅是「每层户数」，在商务是「每层公司数」。
#: 最后三个参数是轮椅与儿童的特殊行为参数，两种楼型共用同一套缺省值。
BUILDING_PRESETS: dict[str, Building] = {
    RESIDENTIAL: Building(
        RESIDENTIAL, 0.90, 0.85, 4, (2, 4), dict(RESIDENTIAL_MIX)
    ),
    OFFICE: Building(OFFICE, 0.20, 0.70, 2, (8, 30), dict(OFFICE_MIX)),
}
DEFAULT_BUILDING = BUILDING_PRESETS[RESIDENTIAL]


@dataclass(frozen=True)
class ResidentTemplate:
    """住客/员工作息模板。

    depart 为出门（住宅）或到岗（商务）的时刻窗，stay 为外出/在岗时长。
    target 决定行程目标层的取法：lobby 走大堂，office 走办公层。
    """

    depart: tuple[int, int]
    stay: tuple[int, int]
    target: str
    companions: tuple[int, int] = (1, 1)


@dataclass(frozen=True)
class VisitorTemplate:
    """访客模板：到达时刻窗、停留时长、结伴人数、需要接待的概率。"""

    arrive: tuple[int, int]
    stay: tuple[int, int]
    companions: tuple[int, int] = (1, 4)
    meet_chance: float = 0.0


RESIDENT_TEMPLATES: dict[str, ResidentTemplate] = {
    # 住宅：住客住在高层，早上经大堂下楼外出，傍晚再乘梯回家
    RESIDENTIAL: ResidentTemplate(
        depart=(7 * 60, 9 * 60),
        stay=(8 * 60, 11 * 60),
        target=TARGET_LOBBY,
        companions=(1, 2),
    ),
    # 商务：员工从大堂上楼到办公层，早高峰方向与住宅完全相反
    OFFICE: ResidentTemplate(
        depart=(8 * 60, 9 * 60 + 30),
        stay=(8 * 60, 10 * 60),
        target=TARGET_OFFICE,
        companions=(1, 1),
    ),
}

VISITOR_TEMPLATES: dict[str, VisitorTemplate] = {
    RESIDENTIAL: VisitorTemplate(
        arrive=(9 * 60, 18 * 60),
        stay=(30, 120),
        companions=(1, 4),
        meet_chance=0.0,
    ),
    # 商务：访客集中在办公时段，且常需在前台等人
    OFFICE: VisitorTemplate(
        arrive=(9 * 60, 17 * 60),
        stay=(30, 120),
        companions=(1, 3),
        meet_chance=0.6,
    ),
}


def resident_template(building: Building | None) -> ResidentTemplate:
    return RESIDENT_TEMPLATES[(building or DEFAULT_BUILDING).normalized().kind]


def visitor_template(building: Building | None) -> VisitorTemplate:
    return VISITOR_TEMPLATES[(building or DEFAULT_BUILDING).normalized().kind]


def resident_label_key(building: Building | None) -> str:
    """商务楼里住客语义为「员工」，其余仍为「住客」。"""
    kind = (building or DEFAULT_BUILDING).normalized().kind
    return "profile.kind.staff" if kind == OFFICE else "profile.kind.resident"

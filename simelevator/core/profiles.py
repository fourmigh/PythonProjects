from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

from core.building import (
    CHILD,
    DEFAULT_BUILDING,
    FEMALE,
    LOBBY_FLOOR,
    MALE,
    PEOPLE_KINDS,
    TARGET_LOBBY,
    WHEELCHAIR,
    Building,
    Population,
    resident_template,
    visitor_template,
)

RESIDENT = "resident"
VISITOR = "visitor"

PALETTE = [
    "#3d7ff5",
    "#f5a623",
    "#4ec9a5",
    "#e05c8a",
    "#9b6dff",
    "#ff7043",
    "#5bc0de",
    "#8bc34a",
]

MINUTES_PER_DAY = 1440


def derive_seed(base_seed: int, pid: str, name: str) -> int:
    raw = f"{base_seed}|{pid}|{name}".encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:12], 16)


def derive_color(pid: str) -> str:
    digest = hashlib.sha256(pid.encode("utf-8")).hexdigest()
    return PALETTE[int(digest[:8], 16) % len(PALETTE)]


def derive_gender(pid: str) -> str:
    """旧画像缺失人群分类时的确定性兜底。

    与 derive_color 同一套思路：只看 pid，因此同一个 pid 永远得到同一个
    分类，反复加载不会漂移。真正的比例由 fill_defaults 按大楼人群构成掷出。
    """
    digest = hashlib.sha256(f"gender|{pid}".encode("utf-8")).hexdigest()
    return PEOPLE_KINDS[int(digest[:8], 16) % len(PEOPLE_KINDS)]


def is_people_kind(value: object) -> bool:
    return isinstance(value, str) and value in PEOPLE_KINDS


@dataclass
class TripLeg:
    time_min: int | None = None
    target_floor: int | None = None
    stay_min: int | None = None

    def to_json(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_json(data: dict) -> TripLeg:
        return TripLeg(
            time_min=data.get("time_min"),
            target_floor=data.get("target_floor"),
            stay_min=data.get("stay_min"),
        )


@dataclass
class PassengerProfile:
    pid: str
    name: str
    kind: str = RESIDENT
    gender: str | None = None
    color: str = PALETTE[0]
    home_floor: int | None = None
    main_floor: int | None = None
    legs: list[TripLeg] = field(default_factory=list)
    weekdays: list[int] = field(default_factory=list)
    attendance: float | None = None
    jitter_min: int | None = None
    companions: int | None = None
    abandon_sec: float | None = None
    visitor_arrive: int | None = None
    visitor_stay: int | None = None
    needs_meet: bool = False

    def clone(self) -> PassengerProfile:
        return PassengerProfile.from_json(self.to_json())

    def to_json(self) -> dict:
        data = asdict(self)
        data["legs"] = [leg.to_json() for leg in self.legs]
        return data

    @staticmethod
    def from_json(data: dict) -> PassengerProfile:
        return PassengerProfile(
            pid=data["pid"],
            name=data.get("name", data["pid"]),
            kind=data.get("kind", RESIDENT),
            # 必须显式解析：clone() 走的就是 from_json，漏掉会静默丢字段
            gender=data.get("gender"),
            color=data.get("color", PALETTE[0]),
            home_floor=data.get("home_floor"),
            main_floor=data.get("main_floor"),
            legs=[TripLeg.from_json(x) for x in data.get("legs", [])],
            weekdays=list(data.get("weekdays", [])),
            attendance=data.get("attendance"),
            jitter_min=data.get("jitter_min"),
            companions=data.get("companions"),
            abandon_sec=data.get("abandon_sec"),
            visitor_arrive=data.get("visitor_arrive"),
            visitor_stay=data.get("visitor_stay"),
            needs_meet=bool(data.get("needs_meet", False)),
        )

    def summary_key(self) -> str:
        if self.kind == RESIDENT:
            return "profile.leg_count" if self.legs else "profile.no_legs"
        if self.visitor_arrive is None:
            return "profile.no_arrival"
        return "profile.stay_min"


def _other_floor(rng: random.Random, home: int, floors: int) -> int:
    if floors <= 2:
        return 2 if home != 2 else 1
    choice = rng.randint(2, floors)
    if choice == home:
        choice = home + 1 if home < floors else home - 1
    return max(1, min(floors, choice))


def _fallback_target(home: int, floors: int) -> int:
    """不依赖随机的兜底目标层：非居住层的最低层。"""
    floors = max(2, floors)
    return 2 if home <= 1 else 1


def _resident_home(building: Building, floors: int, rng: random.Random) -> int:
    """住客/员工的起始层：住宅为居住层，商务为固定的大堂层。"""
    if resident_template(building).target == TARGET_LOBBY:
        return rng.randint(2, floors) if floors > 2 else 2
    return LOBBY_FLOOR


def _resident_target(building: Building, home: int, floors: int, rng: random.Random) -> int:
    """住客/员工的行程目标层：住宅经大堂外出，商务上楼到办公层。"""
    floors = max(2, floors)
    if resident_template(building).target == TARGET_LOBBY:
        return 2 if home <= LOBBY_FLOOR else LOBBY_FLOOR
    return _other_floor(rng, LOBBY_FLOOR, floors)


def resolve(profile: PassengerProfile, floors: int, base_seed: int) -> PassengerProfile:
    """安全归一化：只做钳制、去重与静态兜底，绝不随机补全字段。

    随机回填只发生在创建时（见 fill_defaults），因此这里不会因为
    基准种子或楼层数变化而重新掷骰：住客日程为空就保持为空，即从不出行。
    """
    del base_seed  # 归一化与随机种子无关
    resolved = profile.clone()
    floors = max(2, floors)

    if resolved.color not in PALETTE:
        resolved.color = derive_color(resolved.pid)

    if not is_people_kind(resolved.gender):
        # 旧画像没有人群分类：按 pid 确定性补一个，绝不重掷已有值
        resolved.gender = derive_gender(resolved.pid)

    if resolved.kind == RESIDENT:
        # 住客不再存常去楼层，目的层由日程逐段决定
        resolved.main_floor = None
        if resolved.home_floor is None:
            resolved.home_floor = 1
        resolved.home_floor = max(1, min(floors, resolved.home_floor))
        fallback = _fallback_target(resolved.home_floor, floors)
        cursor = None
        for leg in resolved.legs:
            if leg.target_floor is None:
                leg.target_floor = fallback
            leg.target_floor = max(1, min(floors, leg.target_floor))
            if leg.time_min is None:
                leg.time_min = cursor if cursor is not None else 8 * 60
            if leg.stay_min is None:
                leg.stay_min = 60
            leg.time_min = int(leg.time_min) % MINUTES_PER_DAY
            leg.stay_min = max(0, int(leg.stay_min))
            cursor = leg.time_min + leg.stay_min
        resolved.legs.sort(key=lambda x: (x.time_min, x.target_floor))
    else:
        if resolved.visitor_arrive is None:
            resolved.visitor_arrive = 9 * 60
        resolved.visitor_arrive = int(resolved.visitor_arrive) % MINUTES_PER_DAY
        if resolved.visitor_stay is None:
            resolved.visitor_stay = 60
        resolved.visitor_stay = max(1, int(resolved.visitor_stay))
        if resolved.main_floor is None:
            resolved.main_floor = 2 if floors > 1 else 1
        resolved.main_floor = max(1, min(floors, resolved.main_floor))

    if not resolved.weekdays:
        resolved.weekdays = [1, 2, 3, 4, 5]
    resolved.weekdays = sorted({int(d) for d in resolved.weekdays if 1 <= int(d) <= 7})

    if resolved.attendance is None:
        resolved.attendance = 1.0
    resolved.attendance = min(1.0, max(0.0, float(resolved.attendance)))

    if resolved.jitter_min is None:
        resolved.jitter_min = 0
    resolved.jitter_min = max(0, int(resolved.jitter_min))

    if resolved.companions is None:
        resolved.companions = 1
    resolved.companions = max(1, int(resolved.companions))

    if resolved.abandon_sec is None:
        resolved.abandon_sec = 60.0
    resolved.abandon_sec = max(5.0, float(resolved.abandon_sec))
    return resolved


def needs_fill(profile: PassengerProfile) -> bool:
    """画像是否仍有空字段，需要在创建时随机回填。"""
    if profile.color not in PALETTE:
        return True
    if not profile.weekdays:
        return True
    if profile.attendance is None or profile.jitter_min is None:
        return True
    if profile.companions is None or profile.abandon_sec is None:
        return True
    if profile.kind == RESIDENT:
        return profile.home_floor is None or not profile.legs
    if profile.main_floor is None or profile.visitor_arrive is None:
        return True
    return profile.visitor_stay is None


def standard_schedule(
    home_floor: int,
    target_floor: int,
    base_seed: int,
    pid: str,
    name: str,
    building: Building | None = None,
) -> list[TripLeg]:
    """住客的标准作息：按楼型在出门/到岗时刻窗内出发，停留对应时长。

    末段返程由 ProfileGenerator 自动补齐，因此这里只生成「出发」那一段。
    """
    del home_floor  # 目标层已由调用方选定，作息本身与起始层无关
    template = resident_template(building)
    rng = random.Random(derive_seed(base_seed, pid, f"{name}#schedule"))
    return [
        TripLeg(
            time_min=rng.randint(*template.depart),
            target_floor=target_floor,
            stay_min=rng.randint(*template.stay),
        )
    ]


def fill_defaults(
    profile: PassengerProfile,
    floors: int,
    base_seed: int,
    building: Building | None = None,
) -> PassengerProfile:
    """创建时把画像随机补全为可直接落盘的完整数据。

    这是唯一会随机填充画像的入口，只应在新增、批量生成或复制画像时调用。
    resolve() 不生成任何内容，因此住客删空日程后会一直保持为空。
    building 只影响本次创建，不会在之后重新掷骰。
    """
    building = (building or DEFAULT_BUILDING).normalized()
    floors = max(2, floors)
    filled = profile.clone()
    rng = random.Random(derive_seed(base_seed, filled.pid, filled.name))

    if filled.color not in PALETTE:
        filled.color = derive_color(filled.pid)

    if not is_people_kind(filled.gender):
        # 人群分类走独立种子流：既不干扰下面属性随机的既有序列，也让
        # 单个新增画像能按大楼人群构成掷出分类
        gender_rng = random.Random(
            derive_seed(base_seed, filled.pid, f"{filled.name}#gender")
        )
        weights = [building.people_mix.get(kind, 0.0) for kind in PEOPLE_KINDS]
        filled.gender = (
            gender_rng.choices(PEOPLE_KINDS, weights=weights, k=1)[0]
            if sum(weights) > 0
            else MALE
        )

    # 特殊参数只在「本次真的掷过骰」时套用，否则复制/重载会把已落盘的
    # 阈值再乘一次，越滚越大
    abandon_was_blank = filled.abandon_sec is None
    companions_was_blank = filled.companions is None

    if filled.kind == RESIDENT:
        template = resident_template(building)
        filled.main_floor = None
        if filled.home_floor is None:
            filled.home_floor = _resident_home(building, floors, rng)
        if not filled.legs:
            # 目标层用独立种子流：作息随机与属性随机互不干扰
            target_rng = random.Random(
                derive_seed(base_seed, filled.pid, f"{filled.name}#target")
            )
            target = _resident_target(
                building, int(filled.home_floor), floors, target_rng
            )
            filled.legs = standard_schedule(
                int(filled.home_floor),
                target,
                base_seed,
                filled.pid,
                filled.name,
                building,
            )
        else:
            fallback = _resident_target(
                building, int(filled.home_floor), floors, rng
            )
            cursor = None
            for leg in filled.legs:
                if leg.target_floor is None:
                    leg.target_floor = fallback
                if leg.time_min is None:
                    leg.time_min = (
                        cursor if cursor is not None else rng.randint(*template.depart)
                    )
                if leg.stay_min is None:
                    leg.stay_min = rng.randint(*template.stay)
                cursor = (int(leg.time_min) + int(leg.stay_min)) % MINUTES_PER_DAY
    else:
        template = visitor_template(building)
        if filled.main_floor is None:
            filled.main_floor = _other_floor(rng, LOBBY_FLOOR, floors)
        if filled.visitor_arrive is None:
            filled.visitor_arrive = rng.randint(*template.arrive)
        if filled.visitor_stay is None:
            filled.visitor_stay = rng.randint(*template.stay)
        if filled.companions is None:
            filled.companions = rng.randint(*template.companions)
        if not filled.needs_meet and rng.random() < template.meet_chance:
            # 商务访客常需在前台等人，会推迟 5 分钟
            filled.needs_meet = True

    if not filled.weekdays:
        filled.weekdays = [1, 2, 3, 4, 5]
    if filled.attendance is None:
        filled.attendance = round(rng.randint(70, 100) / 100.0, 2)
    if filled.jitter_min is None:
        filled.jitter_min = rng.randint(0, 15)
    if filled.abandon_sec is None:
        filled.abandon_sec = float(rng.randint(30, 90))

    _apply_category_behavior(filled, building, abandon_was_blank, companions_was_blank)

    return resolve(filled, floors, base_seed)


def _apply_category_behavior(
    profile: PassengerProfile,
    building: Building,
    abandon_was_blank: bool,
    companions_was_blank: bool,
) -> None:
    """把轮椅与儿童的特殊参数套到画像上。

    轮椅：不太能久站，愿意等更久；且通常独自出行。
    儿童：身边必须有成人陪同，且更容易等不下去。

    住客的结伴人数在 fill_defaults 里本就不会被掷出（只有访客会掷），
    因此这里允许 companions 仍为 None——那正是「还没定过，正好按分类定」。
    """
    if profile.gender == WHEELCHAIR:
        if abandon_was_blank and profile.abandon_sec is not None:
            profile.abandon_sec = round(
                profile.abandon_sec * building.wheelchair_patience, 1
            )
        if companions_was_blank:
            profile.companions = 1
    elif profile.gender == CHILD:
        if abandon_was_blank and profile.abandon_sec is not None:
            profile.abandon_sec = round(profile.abandon_sec * building.child_patience, 1)
        if companions_was_blank:
            profile.companions = max(
                int(profile.companions or 1), building.child_min_companions
            )



def new_profile(
    kind: str,
    name: str,
    index: int,
    base_seed: int,
) -> PassengerProfile:
    pid = f"P{index:03d}"
    return PassengerProfile(
        pid=pid,
        name=name,
        kind=kind,
        color=PALETTE[index % len(PALETTE)],
    )


def new_resident_leg() -> TripLeg:
    return TripLeg(time_min=None, target_floor=None, stay_min=None)


def _floor_weights(floor_mode: str, floors: int, rng: random.Random) -> list[float]:
    weights: list[float] = []
    for f in range(1, floors + 1):
        if floor_mode == "uniform":
            weights.append(1.0)
        elif floor_mode == "low":
            weights.append(2.0 / max(1, f))
        else:
            weights.append(rng.uniform(0.5, 1.5))
    total = sum(weights) or 1.0
    return [w / total for w in weights]


def make_batch(
    start_index: int,
    base_seed: int,
    floors: int,
    building: Building | None = None,
    floor_mode: str = "uniform",
    start_name: int = 1,
    population: Population | None = None,
) -> list[PassengerProfile]:
    """按大楼容量生成一整批画像。

    批量数量不再由调用方指定，而是由楼的入住率、每层单元数与每单元人数
    算出（见 Building.population），因此 UI 上预览的人数就是这里产出的
    人数。楼层分布模式作用在「锚点层」上：住宅楼是居住层，商务楼是
    办公层，访客则是目的层——三种场景共用同一套加权分布。
    """
    building = (building or DEFAULT_BUILDING).normalized()
    floors = max(2, floors)
    if population is None:
        population = building.population(floors, base_seed)
    rng = random.Random(derive_seed(base_seed, "batch", f"{building.kind}{start_index}"))
    weights = _floor_weights(floor_mode, floors, rng)
    low = 2 if floors > 2 else 1
    n_residents = max(0, int(population.residents))
    # 人群分类用独立种子流：先按 population.mix 摊出确切人数再洗牌，
    # 因此批量生成的实际构成与 UI 预览逐人对得上，且不扰动楼层分布的随机序列
    mix_rng = random.Random(
        derive_seed(base_seed, "batch", f"{building.kind}{start_index}#mix")
    )
    kinds: list[str] = []
    for category in PEOPLE_KINDS:
        kinds.extend([category] * max(0, int(population.mix.get(category, 0))))
    mix_rng.shuffle(kinds)
    out: list[PassengerProfile] = []
    for i in range(max(0, int(population.total))):
        index = start_index + i
        kind = RESIDENT if i < n_residents else VISITOR
        seq = start_name + (i if kind == RESIDENT else i - n_residents)
        name = f"{'住客' if kind == RESIDENT else '访客'}{seq:03d}"
        profile = new_profile(kind, name, index, base_seed)
        if i < len(kinds):
            profile.gender = kinds[i]
        anchor = rng.choices(range(low, floors + 1), weights=weights[low - 1 :], k=1)[0]
        if kind == RESIDENT:
            if resident_template(building).target == TARGET_LOBBY:
                profile.home_floor = anchor
            else:
                # 商务楼：员工从大堂上楼，锚点层即办公层
                profile.home_floor = LOBBY_FLOOR
                profile.legs = [TripLeg(target_floor=anchor)]
        else:
            profile.main_floor = anchor
        out.append(fill_defaults(profile, floors, base_seed, building))
    return out


class ProfileStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.profiles: list[PassengerProfile] = []
        self.building: Building = DEFAULT_BUILDING

    def load(self) -> list[PassengerProfile]:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                # 旧 JSON 没有 building 段时回退到住宅楼预设
                self.building = Building.from_json(data.get("building"))
                self.profiles = [
                    PassengerProfile.from_json(item) for item in data.get("profiles", [])
                ]
                return self.profiles
            except (json.JSONDecodeError, KeyError, OSError, TypeError, ValueError):
                self.profiles = []
        return self.profiles

    def save(self, profiles: list[PassengerProfile] | None = None) -> None:
        if profiles is not None:
            self.profiles = list(profiles)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "building": self.building.normalized().to_json(),
            "profiles": [p.to_json() for p in self.profiles],
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def next_index(self) -> int:
        best = 0
        for profile in self.profiles:
            digits = profile.pid.lstrip("Pp")
            if digits.isdigit():
                best = max(best, int(digits))
        return best + 1


def sample_profiles() -> list[PassengerProfile]:
    def leg(h: int, m: int, floor: int, stay: int) -> TripLeg:
        return TripLeg(time_min=h * 60 + m, target_floor=floor, stay_min=stay)

    return [
        PassengerProfile(
            pid="P001",
            gender=MALE,
            name="张伟",
            kind=RESIDENT,
            color=PALETTE[0],
            home_floor=8,
            legs=[leg(8, 5, 1, 570)],
            weekdays=[1, 2, 3, 4, 5],
            attendance=1.0,
            jitter_min=8,
            companions=1,
            abandon_sec=60.0,
        ),
        PassengerProfile(
            pid="P002",
            gender=FEMALE,
            name="李静",
            kind=RESIDENT,
            color=PALETTE[1],
            home_floor=11,
            legs=[leg(7, 45, 1, 315), leg(13, 0, 11, 60), leg(14, 0, 1, 200)],
            weekdays=[1, 2, 3, 4, 5],
            attendance=0.95,
            jitter_min=5,
            companions=1,
            abandon_sec=45.0,
        ),
        PassengerProfile(
            pid="P003",
            gender=MALE,
            name="王强",
            kind=RESIDENT,
            color=PALETTE[2],
            home_floor=6,
            legs=[leg(9, 0, 1, 480)],
            weekdays=[1, 2, 3, 4, 5],
            attendance=0.9,
            jitter_min=12,
            companions=1,
            abandon_sec=75.0,
        ),
        PassengerProfile(
            pid="P004",
            gender=CHILD,
            name="刘洋",
            kind=RESIDENT,
            color=PALETTE[3],
            home_floor=9,
            legs=[leg(8, 30, 1, 600)],
            weekdays=[1, 2, 3, 4, 5, 6],
            attendance=1.0,
            jitter_min=6,
            companions=2,
            abandon_sec=60.0,
        ),
        PassengerProfile(
            pid="P005",
            gender=FEMALE,
            name="陈晨",
            kind=RESIDENT,
            color=PALETTE[4],
            home_floor=5,
            legs=[leg(8, 0, 1, 240), leg(12, 0, 5, 180)],
            weekdays=[1, 2, 3, 4, 5],
            attendance=0.85,
            jitter_min=10,
            companions=1,
            abandon_sec=50.0,
        ),
        PassengerProfile(
            pid="P006",
            gender=WHEELCHAIR,
            name="赵敏",
            kind=RESIDENT,
            color=PALETTE[5],
            home_floor=12,
            legs=[leg(7, 20, 1, 630)],
            weekdays=[1, 2, 3, 4, 5],
            attendance=0.92,
            jitter_min=4,
            companions=1,
            abandon_sec=55.0,
        ),
        PassengerProfile(
            pid="P007",
            gender=MALE,
            name="访客-客户",
            kind=VISITOR,
            color=PALETTE[6],
            main_floor=10,
            visitor_arrive=10 * 60 + 30,
            visitor_stay=90,
            needs_meet=True,
            weekdays=[1, 2, 3, 4, 5],
            attendance=1.0,
            jitter_min=5,
            companions=2,
            abandon_sec=40.0,
        ),
        PassengerProfile(
            pid="P008",
            gender=FEMALE,
            name="访客-面试官",
            kind=VISITOR,
            color=PALETTE[7],
            main_floor=4,
            visitor_arrive=14 * 60,
            visitor_stay=60,
            weekdays=[1, 2, 3, 4, 5],
            attendance=0.9,
            jitter_min=3,
            companions=1,
            abandon_sec=45.0,
        ),
        PassengerProfile(
            pid="P009",
            gender=CHILD,
            name="访客-供应商",
            kind=VISITOR,
            color=PALETTE[2],
            main_floor=8,
            visitor_arrive=16 * 60,
            visitor_stay=45,
            weekdays=[2, 4],
            attendance=1.0,
            jitter_min=8,
            companions=1,
            abandon_sec=35.0,
        ),
    ]

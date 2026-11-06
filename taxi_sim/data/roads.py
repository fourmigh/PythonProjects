"""可达性保证模块:
1. 点池只存放真实道路折线上的坐标(来自SDK路径规划结果), 天然可达;
2. 起终点优先走路线缓存; 未命中则调SDK规划一次(SDK自带道路吸附);
3. 规划失败的点对(水域/不可达)被丢弃; 所有失败场景兜底为"同一条已缓存折线切片"。
"""
import math
import random


def hav_deg(p, q):
    """两点的近似度数距离(纬度经度混合欧氏, 仅用于仿真内比较)。"""
    dy = p[0] - q[0]
    dx = (p[1] - q[1]) * math.cos(math.radians((p[0] + q[0]) / 2))
    return math.hypot(dx, dy)


def deg_to_m(p, q):
    return hav_deg(p, q) * 111320


def random_point_near(center, span_deg, rng=random):
    """城市范围内随机点(围绕中心高斯分布, 提高路径规划成功率)。"""
    lat = rng.gauss(center[0], span_deg / 4)
    lng = rng.gauss(center[1], span_deg / 4)
    half = span_deg / 2
    lat = max(center[0] - half, min(center[0] + half, lat))
    lng = max(center[1] - half, min(center[1] + half, lng))
    return (round(lat, 6), round(lng, 6))


def nearest_index(points, lat, lng):
    best, bi = float("inf"), 0
    for i, p in enumerate(points):
        d = hav_deg(p, (lat, lng))
        if d < best:
            best, bi = d, i
    return bi


def fallback_route(city, o, d, polylines):
    """兜底: 在缓存折线中选一条, 切出经过起终点的片段(两点必可达)。"""
    best, best_cost = None, float("inf")
    for pts in polylines:
        if len(pts) < 2:
            continue
        io = nearest_index(pts, o[0], o[1])
        id_ = nearest_index(pts, d[0], d[1])
        cost = hav_deg(pts[io], o) + hav_deg(pts[id_], d)
        if cost < best_cost:
            best_cost, best = cost, (pts, io, id_)
    if not best:
        return None
    pts, io, id_ = best
    seg = pts[io:id_ + 1] if io <= id_ else pts[id_:io + 1][::-1]
    return seg


def pick_pair(pool, min_deg=0.005, max_deg=0.08, rng=random, tries=40):
    """从点池取一对起终点(距离在[min_deg,max_deg]内, 约0.5~9km)。"""
    if len(pool) < 2:
        return None
    for _ in range(tries):
        o = rng.choice(pool)
        d = rng.choice(pool)
        dist = hav_deg(o, d)
        if min_deg <= dist <= max_deg:
            return o, d
    return None

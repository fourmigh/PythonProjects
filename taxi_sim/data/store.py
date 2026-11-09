"""SQLite 存储层: 实体表 / 路线缓存 / 可达点池 / 配额台账 / 配额学习值。
所有操作每次打开独立连接, 天然线程安全。
"""
import datetime
import json
import math
import random
import sqlite3

from app_config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS passengers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT NOT NULL, lat REAL NOT NULL, lng REAL NOT NULL,
    dest_lat REAL NOT NULL, dest_lng REAL NOT NULL,
    source TEXT DEFAULT 'sdk', created_at TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS taxis(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT NOT NULL, lat REAL NOT NULL, lng REAL NOT NULL,
    source TEXT DEFAULT 'sdk', created_at TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS route_cache(
    route_key TEXT PRIMARY KEY, city TEXT, origin TEXT, dest TEXT,
    provider TEXT, points TEXT, distance REAL, duration REAL,
    created_at TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS road_points(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT NOT NULL, lat REAL NOT NULL, lng REAL NOT NULL, route_key TEXT,
    UNIQUE(city, lat, lng));
CREATE TABLE IF NOT EXISTS quota_usage(
    provider TEXT NOT NULL, api TEXT NOT NULL, day TEXT NOT NULL,
    used INTEGER DEFAULT 0, PRIMARY KEY(provider, api, day));
CREATE TABLE IF NOT EXISTS learned_quota(
    provider TEXT NOT NULL, api TEXT NOT NULL,
    daily_limit INTEGER NOT NULL, learned_at TEXT DEFAULT (datetime('now','localtime')),
    PRIMARY KEY(provider, api));
CREATE INDEX IF NOT EXISTS idx_rp_city ON road_points(city);
"""


def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as c:
        c.executescript(_SCHEMA)


# ---------------- 实体 ----------------

def add_passengers(city, rows):
    """rows: [(lat,lng,dest_lat,dest_lng,source)]"""
    with _conn() as c:
        c.executemany(
            "INSERT INTO passengers(city,lat,lng,dest_lat,dest_lng,source)"
            " VALUES(?,?,?,?,?,?)",
            [(city, *r) for r in rows])


def add_taxis(city, rows):
    """rows: [(lat,lng,source)]"""
    with _conn() as c:
        c.executemany(
            "INSERT INTO taxis(city,lat,lng,source) VALUES(?,?,?,?)",
            [(city, *r) for r in rows])


def count_passengers(city):
    with _conn() as c:
        return c.execute("SELECT COUNT(*) n FROM passengers WHERE city=?",
                         (city,)).fetchone()["n"]


def count_taxis(city):
    with _conn() as c:
        return c.execute("SELECT COUNT(*) n FROM taxis WHERE city=?",
                         (city,)).fetchone()["n"]


def sample_passengers(city, n):
    with _conn() as c:
        rows = c.execute(
            "SELECT id,lat,lng,dest_lat,dest_lng FROM passengers WHERE city=?"
            " ORDER BY RANDOM() LIMIT ?", (city, n)).fetchall()
    return [(r["id"], r["lat"], r["lng"], r["dest_lat"], r["dest_lng"]) for r in rows]


def sample_taxis(city, n, exclude_ids=()):
    with _conn() as c:
        rows = c.execute(
            "SELECT id,lat,lng FROM taxis WHERE city=? ORDER BY RANDOM() LIMIT ?",
            (city, n + len(exclude_ids))).fetchall()
    out = [(r["id"], r["lat"], r["lng"]) for r in rows if r["id"] not in exclude_ids]
    return out[:n]


# ---------------- 路线缓存 ----------------

def route_key(city, o_lat, o_lng, d_lat, d_lng):
    return f"{city}|{o_lat:.6f},{o_lng:.6f}|{d_lat:.6f},{d_lng:.6f}"


def get_route_cached(key):
    with _conn() as c:
        r = c.execute("SELECT points,distance,duration,provider FROM route_cache"
                      " WHERE route_key=?", (key,)).fetchone()
    if not r:
        return None
    return {"points": json.loads(r["points"]), "distance": r["distance"],
            "duration": r["duration"], "provider": r["provider"]}


def _valid_pt(p):
    """坐标合法性防护: 纬度 ±90, 经度 ±180 (拦截颠倒/脏数据入库)。"""
    return abs(p[0]) <= 90.0 and abs(p[1]) <= 180.0


def put_route(key, city, origin, dest, provider, points, distance, duration):
    points = [p for p in points if _valid_pt(p)]
    if len(points) < 2:
        return
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO route_cache"
            "(route_key,city,origin,dest,provider,points,distance,duration)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (key, city,
             json.dumps([round(origin[0], 6), round(origin[1], 6)]),
             json.dumps([round(dest[0], 6), round(dest[1], 6)]),
             provider,
             json.dumps([[round(p[0], 6), round(p[1], 6)] for p in points]),
             distance, duration))
        add_points(city, points, key, _c=c)


def all_route_points(city):
    """返回所有缓存路线的折线点(用于兜底切片)。"""
    with _conn() as c:
        rows = c.execute("SELECT points FROM route_cache WHERE city=?", (city,)).fetchall()
    return [json.loads(r["points"]) for r in rows]


def cache_size(city):
    with _conn() as c:
        return c.execute("SELECT COUNT(*) n FROM route_cache WHERE city=?",
                         (city,)).fetchone()["n"]


# ---------------- 可达点池 ----------------

def add_points(city, points, route_key_, _c=None):
    sql = "INSERT OR IGNORE INTO road_points(city,lat,lng,route_key) VALUES(?,?,?,?)"
    rows = [(city, round(p[0], 6), round(p[1], 6), route_key_)
            for p in points if _valid_pt(p)]
    if _c is not None:
        _c.executemany(sql, rows)
    else:
        with _conn() as c:
            c.executemany(sql, rows)


def pool_size(city):
    with _conn() as c:
        return c.execute("SELECT COUNT(*) n FROM road_points WHERE city=?",
                         (city,)).fetchone()["n"]


def sample_pool(city, n, exclude=None, min_dist_deg=0.0):
    """从点池随机取 n 个点; exclude: 已取出的点列表, 用于保持点间最小间距。"""
    picked = list(exclude or [])
    out = []
    with _conn() as c:
        rows = c.execute(
            "SELECT lat,lng FROM road_points WHERE city=? ORDER BY RANDOM()",
            (city,)).fetchall()
    for r in rows:
        if len(out) >= n:
            break
        p = (r["lat"], r["lng"])
        if min_dist_deg > 0:
            ok = all(_hav(p, q) >= min_dist_deg for q in picked + out)
            if not ok:
                continue
        out.append(p)
        picked.append(p)
    return out


def _hav(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])


def random_pool_point(city, rng=random):
    with _conn() as c:
        r = c.execute("SELECT lat,lng FROM road_points WHERE city=?"
                      " ORDER BY RANDOM() LIMIT 1", (city,)).fetchone()
    return (r["lat"], r["lng"]) if r else None


# ---------------- 配额台账 ----------------

def _today():
    return datetime.date.today().isoformat()


def quota_used(provider, api):
    with _conn() as c:
        r = c.execute("SELECT used FROM quota_usage WHERE provider=? AND api=? AND day=?",
                      (provider, api, _today())).fetchone()
    return r["used"] if r else 0


def quota_record(provider, api, n=1):
    with _conn() as c:
        c.execute(
            "INSERT INTO quota_usage(provider,api,day,used) VALUES(?,?,?,?)"
            " ON CONFLICT(provider,api,day) DO UPDATE SET used=used+?",
            (provider, api, _today(), n, n))


def quota_set_used(provider, api, used):
    with _conn() as c:
        c.execute(
            "INSERT INTO quota_usage(provider,api,day,used) VALUES(?,?,?,?)"
            " ON CONFLICT(provider,api,day) DO UPDATE SET used=excluded.used",
            (provider, api, _today(), used))


def learn_quota(provider, api, daily_limit):
    with _conn() as c:
        c.execute(
            "INSERT INTO learned_quota(provider,api,daily_limit,learned_at)"
            " VALUES(?,?,?,datetime('now','localtime'))"
            " ON CONFLICT(provider,api) DO UPDATE SET"
            " daily_limit=excluded.daily_limit, learned_at=excluded.learned_at",
            (provider, api, daily_limit))


def get_learned_quota(provider, api):
    with _conn() as c:
        r = c.execute("SELECT daily_limit FROM learned_quota WHERE provider=? AND api=?",
                      (provider, api)).fetchone()
    return r["daily_limit"] if r else None


def quota_snapshot(defaults):
    """UI 用: [{provider, api, used, limit, learned}]"""
    snap = []
    for (provider, api), dft in defaults.items():
        learned = get_learned_quota(provider, api)
        snap.append({
            "provider": provider, "api": api,
            "used": quota_used(provider, api),
            "limit": learned or dft,
            "learned": learned is not None,
        })
    return snap


def init():
    init_db()

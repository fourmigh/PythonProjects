# English string resources (separated from code)
STRINGS = {
    # ---- languages ----
    "lang.zh_CN": "简体中文",
    "lang.en_US": "English",

    # ---- cities (enum) ----
    "city.beijing": "Beijing",
    "city.shanghai": "Shanghai",
    "city.shenzhen": "Shenzhen",
    "city.guangzhou": "Guangzhou",
    "city.chengdu": "Chengdu",
    "city.hangzhou": "Hangzhou",

    # ---- cruise strategies (enum) ----
    "strategy.random": "Random Walk",
    "strategy.snake": "Snake Scan",
    "strategy.hotspot": "Hotspot Greedy",

    # ---- common ----
    "app.title": "Taxi Cruising Simulation — Multi-Map SDK Auto-Switch",
    "menu.system": "&System",
    "menu.settings": "Settings (Keys / Portal Links / Test)...",
    "btn.start": "Start Simulation",
    "btn.stop": "Stop",

    # ---- main window control panel ----
    "panel.control": "Control",
    "panel.city": "City:",
    "panel.taxis": "Taxis:",
    "panel.passengers": "Passengers:",
    "panel.speed": "Speed:",
    "panel.strategy_hint": "Cruise strategies (multi-select, round-robin):",
    "panel.stats": "Statistics",
    "stats.sim_time": "Sim time (s)",
    "stats.delivered": "Orders done",
    "stats.waiting": "Waiting pax",
    "stats.avg_wait": "Avg wait (s)",
    "stats.empty_ratio": "Empty ratio",
    "stats.pool": "Road point pool",
    "quota.group": "Provider quotas (auto-learned)",
    "quota.item": "{provider}/route: left {remain}/{limit} ({src})",
    "quota.learned": "learned",
    "quota.estimated": "estimated",
    "log.group": "Log",

    # ---- main window messages ----
    "msg.need_strategy": "Please select at least one cruise strategy",
    "msg.config_saved": "Settings saved, reloading map...",
    "msg.config_incomplete": "config.ini is incomplete: configure at least one "
                             "provider key in Settings to unlock all features.",
    "msg.sim_stopped": "Simulation stopped",
    "msg.lang_restart": "Language changed, restart to fully apply",

    # ---- settings dialog ----
    "settings.title": "Settings — Only keys required, quotas auto-learned",
    "settings.tab.amap": "AMap",
    "settings.tab.tencent": "Tencent",
    "settings.tab.baidu": "Baidu",
    "settings.tab.general": "General",
    "settings.web_key": "Web-service key (routing):",
    "settings.js_key": "JS API key (map display):",
    "settings.key": "Key:",
    "settings.ak": "AK:",
    "settings.test_key": "Test key",
    "settings.status_none": "—",
    "settings.lang": "Language (restart to apply):",
    "link.amap.apply": "Apply for an AMap key (Web service + JS API)",
    "link.amap.quota": "AMap quota console",
    "link.tencent.apply": "Apply for a Tencent LBS key",
    "link.tencent.quota": "Tencent quota console",
    "link.baidu.apply": "Apply for a Baidu Maps AK",
    "link.baidu.quota": "Baidu console",
    "settings.quota_note": "No need to fill quotas: when the SDK first reports "
                           "an over-limit error, the real quota is auto-learned "
                           "and stored in the local database.",

    # ---- key test results ----
    "key.not_configured": "Key not configured",
    "key.valid": "Key valid",
    "key.valid_quota": "Key valid (daily quota exhausted)",
    "key.valid_qps": "Key valid (QPS limited)",

    # ---- map placeholder ----
    "map.no_key_html": "<h2 style='color:red'>No map provider key configured. "
                       "Please fill in one in Settings.</h2>",

    # ---- simulation engine log (UI-visible) ----
    "engine.start": "Simulation started: {city}, {n} taxis, strategies "
                    "{strats}, passenger target {pax}",
    "engine.no_taxi_warn": "Warning: no taxi data in DB or point pool; "
                           "waiting for seed collection (consumes quota)",
    "engine.bg_done": "Background data generation finished",
    "engine.bg_fail": "Background data generation failed: {err}",
    "engine.passengers_expired": "{n} passenger(s) left after waiting timeout",
    "engine.order_done": "Taxi#{tid} completed an order ({dist:.0f}m)",

    # ---- data generator log (UI-visible) ----
    "gen.seed_progress": "Seed collection: {routes} routes cached, pool "
                         "{pool} points ({provider})",
    "gen.seed_done": "Seed collection finished: {calls} API calls",
    "gen.pool_empty": "Point pool empty and quota insufficient: using "
                      "existing DB data only; the missing part will be "
                      "generated next day when quota resets",
    "gen.entities_added": "Entities generated: +{pax} passengers, "
                          "+{taxis} taxis",

    # ---- simulation settings ----
    "settings.sim_city": "Simulation city:",
    "settings.taxi_count": "Taxi count:",
    "settings.passenger_count": "Passenger count (DB target):",
    "settings.spawn_interval": "Passenger spawn interval (sim seconds):",
    "settings.patience": "Passenger patience (sim seconds):",
    "settings.speed": "Simulation speed multiplier:",
}

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
    "city.current": "Current location (auto)",

    # ---- cruise strategies (enum) ----
    "strategy.random": "Random Walk",
    "strategy.snake": "Snake Scan",
    "strategy.hotspot": "Hotspot Greedy",
    "strategy.grid": "Grid Patrol",
    "strategy.standby": "Hotzone Standby",
    "strategy.roam": "Anti-crowd Roam",
    "strategy.history": "History Hotspots",
    "strategy.station": "Station Standby",

    # ---- strategy schemes panel ----
    "strat.group": "Strategies",
    "strat.hint": "Checked schemes are evenly split across the fleet "
                  "and compared per strategy",
    "strat.add": "➕",
    "strat.add_tip": "Add a strategy scheme",
    "strat.edit": "✏️",
    "strat.edit_tip": "Edit name/params",
    "strat.del": "🗑",
    "strat.del_tip": "Delete selected scheme",
    "strat.dlg.title": "Edit strategy scheme",
    "strat.dlg.name": "Name:",
    "strat.dlg.type": "Type:",
    "strat.p.grid_n": "Grid N (2~6):",
    "strat.p.radius": "Radius (km):",
    "strat.p.top_n": "Hot cells:",
    "strat.p.station": "Station:",
    "strat.p.station_custom": "Custom coordinates",
    "strat.p.station_lat": "Station lat:",
    "strat.p.station_lng": "Station lng:",
    "strat.cmp.empty": "(no enabled scheme)",
    "strat.cmp.row": "{name}: {taxis} taxis, {orders} orders, ¥{income}, "
                     "empty {empty:.0f}%, wait {wait:.0f}s",

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
    "panel.shift": "Shift (hours):",
    "panel.follow": "Follow taxi",
    "map.today": "Today",
    "map.ride": "Trip",
    "panel.strategy_hint": "Cruise strategies (multi-select, round-robin):",
    "panel.strat_cmp": "Strategy comparison",
    "panel.locate": "Locate current position",
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
    "msg.city_switched": "Switched to {city}, map updated",
    "msg.locating": "Locating current position...",
    "msg.located_hit": "Located near {city}, map switched automatically",
    "msg.located_temp": "Current position is not in the built-in city list; "
                        "map centered at ({lat:.3f}, {lng:.3f})",
    "msg.locate_failed": "Locate failed (network or service unavailable), "
                         "please choose a city manually",
    "msg.locate_need": "No location yet, locating now, please retry shortly",
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
    "settings.security_code": "Security code (securityJsCode):",
    "settings.key": "Key:",
    "settings.secret_key": "Secret key (if signature verification is on):",
    "settings.tencent_sig_hint": "Note: if \"signature verification\" is enabled "
                                 "for WebServiceAPI in the console, the Secret Key "
                                 "is required, otherwise requests fail with 111.",
    "settings.ak": "AK:",
    "settings.baidu_sk": "SK (for SN check):",
    "settings.baidu_sn_hint": "Note: a server AK is authorized either by IP "
                              "whitelist or by SN check (AK+SK). If SN is chosen "
                              "in the console, SK is required, otherwise 211.",
    "settings.baidu_js_ak": "Browser AK (map display):",
    "settings.baidu_referer_hint": "Note: if the map fails to load, add a "
                                   "Referer whitelist for the AK in the Baidu "
                                   "console. This app loads pages from "
                                   "taxi-sim.local; or just use *.",
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
    "key.sig_failed": "Signature check failed (111): this key requires a "
                      "Secret Key; fill it in above and retry",
    "key.sn_failed": "SN check failed (211): this AK uses SN verification; "
                     "fill in the matching SK and retry",
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
    "engine.clock_off": "Taxi#{tid} shift ended, heading back to start point",
    "engine.off_duty": "Taxi#{tid} off duty ({orders} orders, ¥{income} today)",
    "engine.fare_info": "Fare: {base} yuan for first {base_km}km + "
                        "{per_km} yuan/km beyond",

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

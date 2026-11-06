# 简体中文文案资源(与代码分离)
STRINGS = {
    # ---- 语言本身 ----
    "lang.zh_CN": "简体中文",
    "lang.en_US": "English",

    # ---- 城市(枚举) ----
    "city.beijing": "北京",
    "city.shanghai": "上海",
    "city.shenzhen": "深圳",
    "city.guangzhou": "广州",
    "city.chengdu": "成都",
    "city.hangzhou": "杭州",

    # ---- 巡游策略(枚举) ----
    "strategy.random": "随机游走",
    "strategy.snake": "蛇形扫描",
    "strategy.hotspot": "热点贪心",

    # ---- 通用 ----
    "app.title": "出租车巡游仿真 — 多地图SDK自动切换",
    "menu.system": "系统(&S)",
    "menu.settings": "设置 (Key / 官网跳转 / 测试)...",
    "btn.start": "开始仿真",
    "btn.stop": "停止",

    # ---- 主窗口控制面板 ----
    "panel.control": "控制",
    "panel.city": "城市:",
    "panel.taxis": "出租车:",
    "panel.passengers": "乘客量:",
    "panel.speed": "速度:",
    "panel.strategy_hint": "巡游策略(多选, 各车轮流分配):",
    "panel.stats": "统计",
    "stats.sim_time": "仿真时长(s)",
    "stats.delivered": "完成订单",
    "stats.waiting": "等待乘客",
    "stats.avg_wait": "平均等待(s)",
    "stats.empty_ratio": "空驶率",
    "stats.pool": "可达点池",
    "quota.group": "各平台配额(自动学习)",
    "quota.item": "{provider}/route: 剩余 {remain}/{limit} ({src})",
    "quota.learned": "已学习",
    "quota.estimated": "预估值",
    "log.group": "日志",

    # ---- 主窗口消息 ----
    "msg.need_strategy": "请至少选择一种巡游策略",
    "msg.config_saved": "配置已保存, 重新加载地图...",
    "msg.config_incomplete": "config.ini 配置不全: 请先在 设置 中填写任意一家平台的 Key, "
                             "填写后其他功能才能使用",
    "msg.sim_stopped": "仿真已停止",
    "msg.lang_restart": "语言已切换, 重启程序后完全生效",

    # ---- 设置界面 ----
    "settings.title": "设置 — 只需填写 Key, 配额自动学习校准",
    "settings.tab.amap": "高德",
    "settings.tab.tencent": "腾讯",
    "settings.tab.baidu": "百度",
    "settings.tab.general": "通用",
    "settings.web_key": "Web服务 Key(路径规划):",
    "settings.js_key": "JS API Key(地图显示):",
    "settings.key": "Key:",
    "settings.ak": "AK:",
    "settings.test_key": "测试 Key",
    "settings.status_none": "—",
    "settings.lang": "语言(重启生效):",
    "link.amap.apply": "申请高德 Key (Web服务 + JS API)",
    "link.amap.quota": "查看高德配额管理",
    "link.tencent.apply": "申请腾讯位置服务 Key",
    "link.tencent.quota": "查看腾讯配额管理",
    "link.baidu.apply": "申请百度地图 AK",
    "link.baidu.quota": "查看百度控制台",
    "settings.quota_note": "配额无需填写: 系统首次触发SDK超限报错时,"
                           "自动学习真实配额并记录到本地数据库。",

    # ---- Key 测试结果 ----
    "key.not_configured": "未配置 Key",
    "key.valid": "Key 有效",
    "key.valid_quota": "Key 有效(今日配额已耗尽)",
    "key.valid_qps": "Key 有效(QPS受限)",

    # ---- 地图占位 ----
    "map.no_key_html": "<h2 style='color:red'>未配置任何地图平台 Key, "
                       "请到 设置 中填写</h2>",

    # ---- 仿真引擎日志(UI可见) ----
    "engine.start": "仿真开始: {city} 出租车 {n} 辆, 策略 {strats}, "
                    "目标乘客量 {pax}",
    "engine.no_taxi_warn": "警告: 数据库与点池均无出租车数据, "
                           "等待种子采集完成(消耗配额)",
    "engine.bg_done": "后台数据生成完成",
    "engine.bg_fail": "后台数据生成失败: {err}",
    "engine.passengers_expired": "{n} 名乘客等待超时离开",
    "engine.order_done": "出租车#{tid} 完成一单 ({dist:.0f}m)",

    # ---- 数据生成器日志(UI可见) ----
    "gen.seed_progress": "种子采集: 已缓存 {routes} 条路线, 点池 {pool} 点 "
                         "({provider})",
    "gen.seed_done": "种子采集结束: 本次调用 {calls} 次",
    "gen.pool_empty": "可达点池为空且配额不足: 本次仅使用数据库已有数据, "
                      "缺失部分将在次日额度恢复后自动补齐",
    "gen.entities_added": "实体生成: 新增乘客 {pax}, 出租车 {taxis}",

    # ---- 仿真设置项 ----
    "settings.sim_city": "仿真城市:",
    "settings.taxi_count": "出租车数量:",
    "settings.passenger_count": "乘客数量(数据库生成目标):",
    "settings.spawn_interval": "乘客投放间隔(仿真秒):",
    "settings.patience": "乘客耐心(仿真秒):",
    "settings.speed": "仿真速度倍率:",
}

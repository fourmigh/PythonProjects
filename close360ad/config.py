import os

SCAN_INTERVAL = 2

AD_TITLE_KEYWORDS = [
    '弹窗', '推荐', '热点', '资讯', '购物', '推广', '广告',
    '推送', '活动', '红包', '抽奖', '优惠', '促销', '提醒',
    '通知', '每日精选', '今日推荐', '精选', '快资讯',
    '安全播报', '功能推荐', '新品推荐', '福利', '礼包',
    '开机', '小助手',
]

AD_CLASS_NAMES = [
    '#32770', 'Qt5QWindowIcon', '360se_Popup',
    'Popup', 'PopWnd', '360SoftMgr_Popup', 'AfxWnd43',
    'mininews',
]

AD_MODULE_PATTERNS = ['360', 'softmgr', 'popwnd', 'live', 'popwndexe', 'leakfixer', 'sesvcr']

EXCLUDE_TITLE_KEYWORDS = ['360安全卫士', '360软件管家', 'Close360Ad']

KILL_AD_PROCESS = False

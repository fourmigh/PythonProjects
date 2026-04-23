# config.py
class AllocationWeights:
    """分配算法权重配置"""
    # 冲突惩罚
    FUTURE_CONFLICT_PENALTY = 1000
    OVERTIME_RISK_PENALTY = 30
    
    # 车位连续性奖励
    CONTINUOUS_BOTH_SIDES = 50
    CONTINUOUS_ONE_SIDE = 20
    
    # 到达紧迫性奖励
    URGENCY_IMMEDIATE = 100
    URGENCY_NEXT = 50
    URGENCY_2ND_NEXT = 20
    
    # 时长匹配奖励
    LONG_TERM_FUTURE_FREE_BASE = 30
    LONG_TERM_FUTURE_FREE_PER_SLOT = 1
    SHORT_TERM_CORNER_BONUS = 30
    
    # 当前空闲奖励
    CURRENT_FREE_BONUS = 30
    
    # 性能优化
    MAX_FUTURE_ORDERS = 10
    MAX_CANDIDATE_SPOTS = 50
    MAX_CHECK_SLOTS = 8
    FREE_SPOTS_THRESHOLD = 10
    
    # 超时配置
    CONSIDER_OVERTIME = True
    OVERTIME_EXTEND_SLOTS = 1
    
    # 车位推荐权重
    OCCUPIED_NO_CONFLICT_SCORE = 80
    OVERTIME_CONFLICT_PENALTY = -50
    NORMAL_CONFLICT_PENALTY = -100
    IDLE_FUTURE_CONFLICT_PENALTY = -30
    
    # 未来用户检查模式
    CHECK_ONLY_CONFLICTING_FUTURE_USERS = True
    
    # 性能优化配置
    MAX_FUTURE_USERS_CHECK = 15
    FAST_CHECK_MODE = True
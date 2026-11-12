# config.py
class AllocationWeights:
    """诊断路径使用的常量。

    到达分配已改为「车位位图 + 随机起点扫描」，不再需要打分权重；
    这里只保留失败诊断（_recommend_spots_for_user）引用到的配置。
    """

    # 超时配置
    CONSIDER_OVERTIME = True
    OVERTIME_EXTEND_SLOTS = 1

    # 诊断时最多检查的未来订单数
    MAX_FUTURE_ORDERS = 10

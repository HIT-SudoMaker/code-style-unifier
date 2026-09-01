def calculate_velocity(d: float, duration_s: float) -> float:
    """
    计算平均速度

    Args:
        d: 行进距离
        duration_s: 持续时间
    Returns:
        float: 平均速度
    Raises:
        ValueError: 持续时间不大于零
    """
    velocity_m_per_s = d / duration_s
    return velocity_m_per_s

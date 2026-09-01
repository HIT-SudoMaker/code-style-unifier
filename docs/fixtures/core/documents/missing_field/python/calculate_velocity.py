def calculate_velocity(distance_m: float, duration_s: float) -> float:
    """
    计算平均速度

    Args:
        distance_m: 行进距离
        duration_s: 持续时间
    Returns:
        float: 平均速度
    """
    velocity_m_per_s = distance_m / duration_s
    return velocity_m_per_s

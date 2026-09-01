/// 计算平均速度
///
/// # Arguments
/// - distance_m：行进距离
/// - duration_s：持续时间
/// # Returns
/// - 平均速度
/// # Errors
/// - 持续时间不大于零时返回错误
pub fn calculate_velocity(
    distance_m: f64,
    duration_s: f64,
) -> Result<f64, &'static str> {
    if duration_s <= 0.0 {
        return Err("持续时间必须大于零");
    }
    let velocity_m_per_s = distance_m / duration_s;
    Ok(velocity_m_per_s)
}

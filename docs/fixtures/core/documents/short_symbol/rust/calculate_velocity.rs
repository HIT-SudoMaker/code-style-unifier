/// 计算平均速度
///
/// # Arguments
/// - d：行进距离
/// - duration_s：持续时间
/// # Returns
/// - 平均速度
/// # Errors
/// - 无
pub fn calculate_velocity(d: f64, duration_s: f64) -> f64 {
    let velocity_m_per_s = d / duration_s;
    velocity_m_per_s
}

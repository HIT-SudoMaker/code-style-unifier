/// 计算平均速度
///
/// # Arguments
/// - distance_m：行进距离
/// - duration_s：持续时间
/// # Returns
/// - 平均速度
pub fn calculate_velocity(distance_m: f64, duration_s: f64) -> f64 {
    let velocity_m_per_s = distance_m / duration_s;
    velocity_m_per_s
}

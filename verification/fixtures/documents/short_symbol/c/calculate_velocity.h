/**
 * 计算平均速度
 *
 * 参数：
 * - d：                行进距离
 * - duration_s：       持续时间
 * - velocity_m_per_s： 平均速度输出位置
 * 返回：
 * - 计算是否成功
 * 错误：
 * - 无
 */
bool calculate_velocity(
    double d,
    double duration_s,
    double *velocity_m_per_s
);

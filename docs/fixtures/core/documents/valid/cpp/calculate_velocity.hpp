/**
 * 计算平均速度
 *
 * 参数：
 * - distance_m：行进距离
 * - duration_s：持续时间
 * 返回：
 * - 平均速度
 * 错误：
 * - duration_s不大于零时抛出std::invalid_argument
 */
double calculate_velocity(double distance_m, double duration_s);

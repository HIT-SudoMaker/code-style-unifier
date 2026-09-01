#include <stdbool.h>

/**
 * 计算平均速度
 *
 * 参数：
 * - distance_m：行进距离
 * - duration_s：持续时间
 * - velocity_m_per_s：平均速度输出位置
 * 返回：
 * - 计算是否成功
 * 错误：
 * - duration_s不大于零时返回false
 */
bool calculate_velocity(
    double distance_m,
    double duration_s,
    double *velocity_m_per_s
);

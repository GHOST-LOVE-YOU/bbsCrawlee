from datetime import datetime

import pytz

from iwhisper.lib.utils import get_env


def is_near_now(time_str: str) -> bool:
    """
    传入一个时间字符串（格式：HH:MM:SS），与当前时间比较（东八区）。
    如果时间间隔小于10分钟，返回True，否则返回False。

    Args:
        time_str: 时间字符串，格式为 "HH:MM:SS"，例如 "14:06:36"

    Returns:
        bool: 时间间隔小于10分钟返回True，否则返回False
    """
    threshold = int(get_env("TIME_THRESHOLD", "600"))
    if threshold == -1:
        return True

    # 设置东八区时区
    tz = pytz.timezone("Asia/Shanghai")

    # 获取当前时间（东八区）
    now = datetime.now(tz)

    # 解析传入的时间字符串
    try:
        time_parts = time_str.split(":")
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        second = int(time_parts[2])
    except (ValueError, IndexError):
        return False

    # 为传入的时间加上当前的年月日，构造完整的datetime对象
    target_time = now.replace(hour=hour, minute=minute, second=second, microsecond=0)

    # 转换为时间戳（Unix时间戳，即从1970年1月1日开始的秒数）
    now_timestamp = now.timestamp()
    target_timestamp = target_time.timestamp()

    # 计算时间差（秒）
    time_diff = now_timestamp - target_timestamp

    # 判断是否小于时间阈值
    return time_diff < threshold

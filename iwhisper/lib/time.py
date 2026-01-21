from datetime import datetime

import pytz

from iwhisper.lib.utils import get_env


def is_near_now(time_str: str, threshold: int | None = None) -> bool:
    """
    传入一个时间字符串，与当前时间比较（东八区）。
    支持两种格式：
    - HH:MM:SS（时分秒），使用当前日期
    - YYYY-MM-DD（年月日），时分秒默认为 23:59:59
    如果时间间隔小于阈值，返回True，否则返回False。

    Args:
        time_str: 时间字符串，格式为 "HH:MM:SS" 或 "YYYY-MM-DD"
        threshold: 可选的时间阈值（秒），如果不指定则从环境变量读取
    Returns:
        bool: 时间间隔小于阈值返回True，否则返回False
    """
    if threshold is None:
        threshold = int(get_env("TIME_THRESHOLD", "600"))
    if threshold == -1:
        return True

    # 设置东八区时区
    tz = pytz.timezone("Asia/Shanghai")
    # 获取当前时间（东八区）
    now = datetime.now(tz)

    try:
        if "-" in time_str:
            # 年月日格式：YYYY-MM-DD
            date_parts = time_str.split("-")
            year = int(date_parts[0])
            month = int(date_parts[1])
            day = int(date_parts[2])
            # 时分秒设为 23:59:59
            target_time = now.replace(
                year=year,
                month=month,
                day=day,
                hour=23,
                minute=59,
                second=59,
                microsecond=0,
            )
        else:
            # 时分秒格式：HH:MM:SS
            time_parts = time_str.split(":")
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            second = int(time_parts[2])
            target_time = now.replace(
                hour=hour, minute=minute, second=second, microsecond=0
            )
    except (ValueError, IndexError):
        return False

    # 计算时间差（秒）
    time_diff = now.timestamp() - target_time.timestamp()

    # 判断是否小于时间阈值
    return time_diff < threshold

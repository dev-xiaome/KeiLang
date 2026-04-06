#!/usr/bin/env python

import time as _time  # 避免命名冲突

from stdlib import kei as stdlib
from lib.object import *

def sleep(seconds):
    """睡眠指定秒数"""
    stdlib.check(seconds, KeiInt, KeiFloat, name='time.sleep')
    _time.sleep(seconds.value)
    return null  # 返回 null 表示成功

def time():
    """返回当前时间戳（秒）"""
    return KeiFloat(_time.time())

def gmtime(secs=None):
    """返回 UTC 时间元组"""
    if secs is None:
        t = _time.gmtime()
    else:
        stdlib.check(secs, KeiInt, KeiFloat, name='time.gmtime')
        t = _time.gmtime(secs.value)

    # 转换成 KeiList
    return KeiList([
        KeiInt(t.tm_year),   # 年
        KeiInt(t.tm_mon),    # 月
        KeiInt(t.tm_mday),   # 日
        KeiInt(t.tm_hour),   # 时
        KeiInt(t.tm_min),    # 分
        KeiInt(t.tm_sec),    # 秒
        KeiInt(t.tm_wday),   # 星期几（0-6）
        KeiInt(t.tm_yday),   # 一年中的第几天
        KeiInt(t.tm_isdst)   # 夏令时
    ])

def localtime(secs=None):
    """返回本地时间元组"""
    if secs is None:
        t = _time.localtime()
    else:
        stdlib.check(secs, KeiInt, KeiFloat, name='time.localtime')
        t = _time.localtime(secs.value)

    return KeiList([
        KeiInt(t.tm_year),
        KeiInt(t.tm_mon),
        KeiInt(t.tm_mday),
        KeiInt(t.tm_hour),
        KeiInt(t.tm_min),
        KeiInt(t.tm_sec),
        KeiInt(t.tm_wday),
        KeiInt(t.tm_yday),
        KeiInt(t.tm_isdst)
    ])

def strftime(format, t=None):
    """格式化时间"""
    stdlib.check(format, KeiString, name='time.strftime')

    if t is None:
        t = _time.localtime()
    else:
        stdlib.check(t, KeiList, name='time.strftime')
        # 将 KeiList 转换为 time.struct_time
        t = _time.struct_time((
            t.items[0].value,  # tm_year
            t.items[1].value,  # tm_mon
            t.items[2].value,  # tm_mday
            t.items[3].value,  # tm_hour
            t.items[4].value,  # tm_min
            t.items[5].value,  # tm_sec
            t.items[6].value,  # tm_wday
            t.items[7].value,  # tm_yday
            t.items[8].value   # tm_isdst
        ))

    return KeiString(_time.strftime(format.value, t))

# 导出
__all__ = ['sleep', 'time', 'gmtime', 'localtime', 'strftime']

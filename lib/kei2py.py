#!/usr/bin/env python

from lib.object import *

def to_float(x):
    """将 Kei 类型转换为 Python float"""
    if isinstance(x, (KeiFloat, KeiInt)):
        return float(x.value)
    else:
        raise KeiError("TypeError", "需要float")

def to_int(x):
    """将 Kei 类型转换为 Python int"""
    if isinstance(x, (KeiInt)):
        return int(x.value)
    else:
        raise KeiError("TypeError", "需要int")

def to_str(x):
    """将 Kei 类型转换为 Python str"""
    if isinstance(x, KeiString):
        return str(x.value)
    else:
        raise KeiError("TypeError", "需要string")

def to_bool(x):
    """将 Kei 类型转换为 Python bool"""
    if isinstance(x, KeiBool):
        return bool(x.value)
    else:
        raise KeiError("TypeError", "需要bool")

def to_list(x):
    """将 Kei 类型转换为 Python list"""
    if isinstance(x, KeiList):
        return [to_python(item) for item in x.items]
    else:
        raise KeiError("TypeError", "需要list")

def to_dict(x):
    """将 Kei 类型转换为 Python dict"""
    if isinstance(x, KeiDict):
        return {k: to_python(v) for k, v in x.items.items()}
    else:
        raise KeiError("TypeError", "需要dict")

def to_python(x):
    if isinstance(x, KeiInt):
        return x.value
    if isinstance(x, KeiFloat):
        return x.value
    if isinstance(x, KeiString):
        return x.value
    if isinstance(x, KeiBool):
        return x.value
    if isinstance(x, KeiList):
        return [to_python(item) for item in x.items]
    if isinstance(x, KeiDict):
        return {k: to_python(v) for k, v in x.items.items()}
    return x

__all__ = ["to_float", "to_int", "to_str", "to_bool", "to_list", "to_dict", "to_python"]

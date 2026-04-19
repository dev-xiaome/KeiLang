#!/usr/bin/env python

def to_float(x):
    """将 Kei 类型转换为 Python float"""
    from object import KeiFloat, KeiInt, KeiError

    if isinstance(x, (KeiFloat, KeiInt)):
        return float(x.value)
    elif isinstance(x, (float, int)):
        return x
    else:
        raise KeiError("TypeError", "需要float")

def to_int(x):
    """将 Kei 类型转换为 Python int"""
    from object import KeiInt, KeiError

    if isinstance(x, KeiInt):
        return int(x.value)
    elif isinstance(x, int):
        return x
    else:
        raise KeiError("TypeError", "需要int")

def to_str(x):
    """将 Kei 类型转换为 Python str"""
    from object import KeiString, KeiError

    if isinstance(x, KeiString):
        return str(x.value)
    elif isinstance(x, str):
        return x
    else:
        raise KeiError("TypeError", "需要string")

def to_bool(x):
    """将 Kei 类型转换为 Python bool"""
    from object import KeiBool, KeiError

    if isinstance(x, KeiBool):
        return bool(x.value)
    elif isinstance(x, bool):
        return x
    else:
        raise KeiError("TypeError", "需要bool")

def to_list(x):
    """将 Kei 类型转换为 Python list"""
    from object import KeiList, KeiError

    if isinstance(x, KeiList):
        return [to_python(item) for item in x.items]
    elif isinstance(x, list):
        return x
    else:
        raise KeiError("TypeError", "需要list")

def to_dict(x):
    """将 Kei 类型转换为 Python dict"""
    from object import KeiDict, KeiError

    if isinstance(x, KeiDict):
        return {k: to_python(v) for k, v in x.items.items()}
    elif isinstance(x, dict):
        return x
    else:
        raise KeiError("TypeError", "需要dict")

def to_python(x):
    from object import KeiInt, KeiFloat, KeiString, KeiBool, KeiList, KeiDict
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

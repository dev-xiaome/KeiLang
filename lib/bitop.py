#!/usr/bin/env python
"""KeiLang 位运算模块"""

from object import KeiInt, KeiBase
from lib.kei2py import to_int

def _to_int(value):
    """转换为 Python int"""
    if isinstance(value, KeiInt):
        return value.value
    return int(value)

def _to_kei(value):
    """转换为 KeiInt"""
    return KeiInt(value)

def band(a, b):
    """按位与 &"""
    return _to_kei(_to_int(a) & _to_int(b))

def bor(a, b):
    """按位或 |"""
    return _to_kei(_to_int(a) | _to_int(b))

def bxor(a, b):
    """按位异或 ^"""
    return _to_kei(_to_int(a) ^ _to_int(b))

def bnot(a, bits=32):
    """按位取反 ~（限制在指定位数内，默认 32 位）"""
    val = _to_int(a)
    mask = (1 << bits) - 1
    return _to_kei((~val) & mask)

def lshift(a, n):
    """左移 <<"""
    return _to_kei(_to_int(a) << _to_int(n))

def rshift(a, n):
    """右移 >>"""
    return _to_kei(_to_int(a) >> _to_int(n))

def bset(a, pos, value=1):
    """设置第 pos 位（0 开始）为 value（0 或 1）"""
    val = _to_int(a)
    if value:
        return _to_kei(val | (1 << _to_int(pos)))
    else:
        return _to_kei(val & ~(1 << _to_int(pos)))

def bget(a, pos):
    """获取第 pos 位的值（0 或 1）"""
    val = _to_int(a)
    return _to_kei((val >> _to_int(pos)) & 1)

def btoggle(a, pos):
    """翻转第 pos 位"""
    val = _to_int(a)
    return _to_kei(val ^ (1 << _to_int(pos)))

def bcount(a):
    """计算二进制中 1 的个数（popcount）"""
    val = _to_int(a)
    return _to_kei(bin(val).count('1'))

def bprint(a, bits=8):
    """打印二进制表示（指定位数）"""
    val = _to_int(a)
    return bin(val & ((1 << bits) - 1))[2:].zfill(bits)

# 模块导出
__all__ = [
    'band', 'bor', 'bxor', 'bnot',
    'lshift', 'rshift',
    'bset', 'bget', 'btoggle',
    'bcount', 'bprint'
]
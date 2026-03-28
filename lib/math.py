#!/usr/bin/env python

import math as _math
from lib.object import *
from lib.kei2py import *

# 常量
pi = KeiFloat(_math.pi)
e = KeiFloat(_math.e)

# 基本函数
def abs(x):
    x = to_float(x)
    return abs(x)

def sqrt(x):
    x = to_float(x)
    if x < 0:
        raise Exception("不能对负数开平方")
    return _math.sqrt(x)

def sin(x):
    x = to_float(x)
    return _math.sin(x)

def cos(x):
    x = to_float(x)
    return _math.cos(x)

def tan(x):
    x = to_float(x)
    return _math.tan(x)

def asin(x):
    x = to_float(x)
    return _math.asin(x)

def acos(x):
    x = to_float(x)
    return _math.acos(x)

def atan(x):
    x = to_float(x)
    return _math.atan(x)

def atan2(y, x):
    y = to_float(y)
    x = to_float(x)
    return _math.atan2(y, x)

def sinh(x):
    x = to_float(x)
    return _math.sinh(x)

def cosh(x):
    x = to_float(x)
    return _math.cosh(x)

def tanh(x):
    x = to_float(x)
    return _math.tanh(x)

def pow(x, y):
    x = to_float(x)
    y = to_float(y)
    return x ** y

def exp(x):
    x = to_float(x)
    return _math.exp(x)

def log(x, base=None):
    x = to_float(x)
    if base is None:
        return _math.log(x)
    base = to_float(base)
    return _math.log(x, base)

def log10(x):
    x = to_float(x)
    return _math.log10(x)

def log2(x):
    x = to_float(x)
    return _math.log2(x)

def floor(x):
    x = to_float(x)
    return _math.floor(x)

def ceil(x):
    x = to_float(x)
    return _math.ceil(x)

def round(x, ndigits=0):
    x = to_float(x)
    if isinstance(ndigits, (KeiFloat, KeiInt)):
        ndigits = ndigits.value
    return round(x, ndigits)

def trunc(x):
    x = to_float(x)
    return _math.trunc(x)

def modf(x):
    x = to_float(x)
    frac, intp = _math.modf(x)
    return (frac, intp)

def fmod(x, y):
    x = to_float(x)
    y = to_float(y)
    return _math.fmod(x, y)

def gcd(a, b):
    a = to_int(a)
    b = to_int(b)
    return _math.gcd(a, b)

def lcm(a, b):
    a = to_int(a)
    b = to_int(b)
    return a * b // _math.gcd(a, b)

def comb(n, k):
    n = to_int(n)
    k = to_int(k)
    return _math.comb(n, k)

def perm(n, k):
    n = to_int(n)
    k = to_int(k)
    return _math.perm(n, k)

def degrees(rad):
    rad = to_float(rad)
    return _math.degrees(rad)

def radians(deg):
    deg = to_float(deg)
    return _math.radians(deg)

def hypot(*args):
    args = [to_float(a) for a in args]
    return _math.hypot(*args)

def dist(p, q):
    p = [to_float(x) for x in p]
    q = [to_float(x) for x in q]
    return _math.dist(p, q)

def isclose(a, b, rel_tol=1e-9, abs_tol=0.0):
    a = to_float(a)
    b = to_float(b)
    if isinstance(rel_tol, (KeiFloat, KeiInt)):
        rel_tol = rel_tol.value
    if isinstance(abs_tol, (KeiFloat, KeiInt)):
        abs_tol = abs_tol.value
    return _math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)

def isfinite(x):
    x = to_float(x)
    return _math.isfinite(x)

def isinf(x):
    x = to_float(x)
    return _math.isinf(x)

def isnan(x):
    x = to_float(x)
    return _math.isnan(x)

def pibbp(terms):
    from decimal import Decimal
    if isinstance(terms, KeiFloat):
        terms = terms.value
    pi = Decimal(0)
    for k in range(terms):
        term = Decimal(1) / (Decimal(16) ** k) * (
            Decimal(4)/(8*k+1) -
            Decimal(2)/(8*k+4) -
            Decimal(1)/(8*k+5) -
            Decimal(1)/(8*k+6)
        )
        pi += term
    return KeiFloat(pi)

__all__ = [
    'pi', 'e',
    'abs', 'sqrt', 'sin', 'cos', 'tan',
    'asin', 'acos', 'atan', 'atan2',
    'sinh', 'cosh', 'tanh',
    'pow', 'exp', 'log', 'log10', 'log2',
    'floor', 'ceil', 'round', 'trunc', 'modf', 'fmod',
    'gcd', 'lcm', 'comb', 'perm',
    'degrees', 'radians', 'hypot', 'dist',
    'isclose', 'isfinite', 'isinf', 'isnan'
]

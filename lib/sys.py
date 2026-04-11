#!/usr/bin/env python

from object import *
from kei import __kei__

def __getattr__(name):
    """模块级别的动态属性"""
    if name == "argv":
        return __kei__.argv
    if name == "stack":
        return __kei__.stack
    if name == "scriptfile":
        return __kei__.file

    raise KeiError("AttributeError", f"sys没有属性: {name}")

# 可选：导出常用名字
__all__ = ['__getattr__', 'argv', 'stack', 'scriptfile']

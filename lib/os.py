#!/usr/bin/env python

import os as _os
from pathlib import Path
from lib.object import *
from lib.kei2py import *

class KeiPath:
    """KeiLang 的路径类"""
    def __init__(self, *parts):
        # 转换所有部分为字符串
        str_parts = [to_str(p) for p in parts]
        self.path = Path(*str_parts)

    def __truediv__(self, other):
        """支持 path / "subdir" """
        return KeiPath(self.path, to_str(other))

    def __str__(self):
        return str(self.path)

    def __repr__(self):
        return f"{self.path}"

    def __getitem__(self, key):
        """支持下标操作，返回路径的组成部分"""
        parts = str(self.path).split(_os.sep)

        # 如果是整数索引
        if isinstance(key, int):
            if 0 <= key < len(parts):
                return parts[key]
            return undefined

        # 如果是字符串（可能是属性名）
        if isinstance(key, str):
            # 如果是方法名，返回方法
            if key in ['exists', 'isfile', 'isdir', 'abs', 'resolve']:
                return getattr(self, key)
            # 否则可能是路径的一部分
            if key in parts:
                return key
            return undefined

        # 其他类型报错
        raise TypeError(f"KeiPath 对象不支持 {type(key)} 类型的索引")

    def exists(self):
        return true if self.path.exists() else false

    def isfile(self):
        return true if self.path.is_file() else false

    def isdir(self):
        return true if self.path.is_dir() else false

    def abs(self):
        return KeiPath(self.path.absolute())

    def resolve(self):
        return KeiPath(self.path.resolve())

def path(*parts):
    """创建路径对象"""
    return KeiPath(*parts)

def getcwd():
    return KeiString(_os.getcwd())

def listdir(path="."):
    p = to_str(path)
    return KeiList([KeiString(f) for f in _os.listdir(p)])

def mkdir(path, mode=0o777):
    p = to_str(path)
    _os.mkdir(p, mode)
    return null

def remove(path):
    p = to_str(path)
    _os.remove(p)
    return null

def rename(src, dst):
    src_str = to_str(src)
    dst_str = to_str(dst)
    _os.rename(src_str, dst_str)
    return null

def exists(path):
    p = to_str(path)
    return true if _os.path.exists(p) else false

def isfile(path):
    p = to_str(path)
    return true if _os.path.isfile(p) else false

def isdir(path):
    p = to_str(path)
    return true if _os.path.isdir(p) else false

def chdir(path):
    p = to_str(path)
    _os.chdir(p)

# 导出
__all__ = ['path', 'getcwd', 'listdir', 'mkdir', 'remove', 'rename', 'exists', 'isfile', 'isdir', 'chdir']

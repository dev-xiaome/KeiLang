#!/usr/bin/env python

from object import *
from lib.kei2py import *
from lib.python import topy, tokei
import numpy as np

class array(KeiBase):
    def __init__(self, shape_or_data, dtype='int64'):
        super().__init__("array")

        # 支持传入 numpy 数组、列表、或形状
        if isinstance(shape_or_data, np.ndarray):
            self._np = shape_or_data
        elif isinstance(shape_or_data, (list, tuple)) and len(shape_or_data) == 2:
            # 形状参数：创建全零数组
            self._np = np.zeros(shape_or_data, dtype=dtype)
        elif isinstance(shape_or_data, (list, tuple)):
            # 数据参数：从列表创建
            self._np = np.array(shape_or_data, dtype=dtype)
        elif isinstance(shape_or_data, (int, KeiInt)):
            size = shape_or_data.value if isinstance(shape_or_data, KeiInt) else shape_or_data
            self._np = np.zeros(size, dtype=dtype)
        else:
            raise KeiError("TypeError", f"array 不支持的类型: {type(shape_or_data)}")

        self._methods = {
            "push": self._push,
            "pop": self._pop,
            "get": self._get,
            "set": self._set,
            "length": self._length,
            "slice": self._slice,
            "join": self._join,
            "copy": self._copy,
            "reshape": self._reshape,
            "transpose": self._transpose,
            "flatten": self._flatten,
            "sum": self._sum,
            "mean": self._mean,
            "min": self._min,
            "max": self._max,
            "argmin": self._argmin,
            "argmax": self._argmax,
            "dot": self._dot,
        }

    def __len__(self):
        return len(self._np)

    def __bool__(self):
        return len(self._np) > 0

    def _length(self):
        return KeiInt(len(self._np))
    def length(self):
        return self._length()

    def _get(self, index):
        if isinstance(index, KeiInt):
            i = index.value
        else:
            i = int(index)
        if 0 <= i < len(self._np):
            val = self._np[i]
            if isinstance(val, np.ndarray):
                return array(val)
            return tokei(val)
        return undefined
    def get(self, index):
        return self._get(index)

    def _set(self, index, value):
        if isinstance(index, KeiInt):
            i = index.value
        else:
            i = int(index)
        if 0 <= i < len(self._np):
            self._np[i] = topy(value)
            return value
        elif i == len(self._np):
            self._push(value)
            return value
        return undefined
    def set(self, index, value):
        return self._set(index, value)

    def _push(self, *values):
        for v in values:
            py_val = topy(v)
            # 确保 py_val 是数组可接受的形式
            if not isinstance(py_val, (list, np.ndarray)):
                py_val = [py_val]
            self._np = np.append(self._np, py_val)  # type: ignore
        return self
    def push(self, *values):
        return self._push(*values)

    def _pop(self):
        if len(self._np) == 0:
            return undefined
        val = self._np[-1]
        self._np = self._np[:-1]
        return tokei(val)
    def pop(self):
        return self._pop()

    def _slice(self, start=None, end=None):
        s = start.value if isinstance(start, KeiInt) else (start or 0)
        e = end.value if isinstance(end, KeiInt) else (end if end is not None else len(self._np))
        return array(self._np[s:e])
    def slice(self, start=None, end=None):
        return self._slice(start, end)

    def _join(self, separator=""):
        sep = separator.value if isinstance(separator, KeiString) else str(separator)
        return KeiString(sep.join(str(tokei(x)) for x in self._np))
    def join(self, separator=""):
        return self._join(separator)

    def _copy(self):
        return array(self._np.copy())
    def copy(self):
        return self._copy()

    # 运算符重载（利用 NumPy 的向量化）
    def __add__(self, other):
        if isinstance(other, array):
            return array(self._np + other._np)
        return array(self._np + topy(other))

    def __sub__(self, other):
        if isinstance(other, array):
            return array(self._np - other._np)
        return array(self._np - topy(other))

    def __mul__(self, other):
        if isinstance(other, array):
            return array(self._np * other._np)
        return array(self._np * topy(other))

    def __truediv__(self, other):
        if isinstance(other, array):
            return array(self._np / other._np)
        return array(self._np / topy(other))

    def __getitem__(self, key):
        # 字符串 key 应该走属性访问，不是 NumPy 索引
        if isinstance(key, str):
            return getattr(self, key, undefined)

        if isinstance(key, KeiInt):
            key = key.value
        elif isinstance(key, slice):
            start = key.start.value if isinstance(key.start, KeiInt) else key.start
            stop = key.stop.value if isinstance(key.stop, KeiInt) else key.stop
            step = key.step.value if isinstance(key.step, KeiInt) else key.step
            key = slice(start, stop, step)

        result = self._np[key]
        if isinstance(result, np.ndarray):
            return array(result)
        return tokei(result)

    def __setitem__(self, key, value):
        if isinstance(key, KeiInt):
            key = key.value
        self._np[key] = topy(value)

    def __delitem__(self, key):
        if isinstance(key, KeiInt):
            key = key.value
        self._np = np.delete(self._np, key)

    def __repr__(self):
        return f"<array shape={self._np.shape} dtype={self._np.dtype}>"

    def __iter__(self):
        for item in self._np:
            yield tokei(item)

    def __contains__(self, item):
        return item in self._np.tolist()

    def __str__(self):
        return self.__repr__()

    def __content__(self):
        return self.__repr__()

    def _reshape(self, *shape):
        """改变形状"""
        if len(shape) == 1 and isinstance(shape[0], (list, tuple, KeiList)):
            shape = shape[0]
        new_shape = []
        for s in shape:
            if isinstance(s, KeiInt):
                new_shape.append(s.value)
            else:
                new_shape.append(int(s))
        return array(self._np.reshape(tuple(new_shape)))
    def reshape(self, *shape):
        return self._reshape(*shape)

    def _transpose(self):
        """转置"""
        return array(self._np.T)
    def transpose(self):
        return self._transpose()

    def _flatten(self):
        """展平为一维"""
        return array(self._np.flatten())
    def flatten(self):
        return self._flatten()

    def _sum(self, axis=None):
        """求和"""
        if axis is not None:
            axis = axis.value if isinstance(axis, KeiInt) else int(axis)
        result = self._np.sum(axis=axis)
        if isinstance(result, np.ndarray):
            return array(result)
        return tokei(result)
    def sum(self, axis=None):
        return self._sum(axis)

    def _mean(self, axis=None):
        """平均值"""
        if axis is not None:
            axis = axis.value if isinstance(axis, KeiInt) else int(axis)
        result = self._np.mean(axis=axis)
        if isinstance(result, np.ndarray):
            return array(result)
        return tokei(result)
    def mean(self, axis=None):
        return self._mean(axis)

    def _min(self, axis=None):
        """最小值"""
        if axis is not None:
            axis = axis.value if isinstance(axis, KeiInt) else int(axis)
        result = self._np.min(axis=axis)
        if isinstance(result, np.ndarray):
            return array(result)
        return tokei(result)
    def min(self, axis=None):
        return self._min(axis)

    def _max(self, axis=None):
        """最大值"""
        if axis is not None:
            axis = axis.value if isinstance(axis, KeiInt) else int(axis)
        result = self._np.max(axis=axis)
        if isinstance(result, np.ndarray):
            return array(result)
        return tokei(result)
    def max(self, axis=None):
        return self._max(axis)

    def _argmin(self, axis=None):
        """最小值的索引"""
        if axis is not None:
            axis = axis.value if isinstance(axis, KeiInt) else int(axis)
        result = self._np.argmin(axis=axis)
        if isinstance(result, np.ndarray):
            return array(result)
        return tokei(result)
    def argmin(self, axis=None):
        return self._argmin(axis)

    def _argmax(self, axis=None):
        """最大值的索引"""
        if axis is not None:
            axis = axis.value if isinstance(axis, KeiInt) else int(axis)
        result = self._np.argmax(axis=axis)
        if isinstance(result, np.ndarray):
            return array(result)
        return tokei(result)
    def argmax(self, axis=None):
        return self._argmax(axis)

    def _dot(self, other):
        if isinstance(other, array):
            return array(self._np.dot(other._np))
        py_other = topy(other)
        # 强制转为 numpy 数组
        if not isinstance(py_other, np.ndarray):
            py_other = np.array(py_other)
        return array(self._np.dot(py_other))
    def dot(self, other):
        return self._dot(other)

def zeros(shape):
    if isinstance(shape, KeiList):
        shape = tuple(to_int(i) for i in shape.items)
    elif isinstance(shape, KeiInt):
        shape = (shape.value,)
    else:
        shape = tuple(shape)

    if len(shape) == 1:
        shape = (shape[0], 1)

    return array(shape)

def ones(shape):
    if isinstance(shape, KeiList):
        shape = tuple(to_int(i) for i in shape.items)
    elif isinstance(shape, KeiInt):
        shape = (shape.value,)
    else:
        shape = tuple(shape)

    if len(shape) == 1:
        shape = (shape[0], 1)

    return array(np.ones(shape, dtype='int64'))

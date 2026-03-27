#!/usr/bin/env python

import copy
import math
from typing import Any, Dict, Union, Callable
from decimal import Decimal, InvalidOperation

# ========== 基础值类型 ==========

class _undefined:
    def __repr__(self): return "undefined"
    def __str__(self): return "undefined"
    def __bool__(self): return False
    def __eq__(self, other): return isinstance(other, _undefined)
    def __hash__(self): return 0

class _null:
    def __repr__(self): return "null"
    def __str__(self): return "null"
    def __bool__(self): return False
    def __eq__(self, other): return isinstance(other, _null)
    def __hash__(self): return 0

class _omit:
    def __repr__(self): return "..."
    def __str__(self): return "..."
    def __bool__(self): return False
    def __eq__(self, other): return isinstance(other, _omit)
    def __hash__(self): return 0

undefined = _undefined()
null = _null()
omit = _omit()

# ========== 类型别名 ==========

KeiValue = Union['KeiBase', int, float, str, bool, list, dict, None]
KeiNumber = Union[int, float, 'KeiInt', 'KeiFloat']

# ========== Kei 对象元类 ==========

class KeiMeta(type):
    def __instancecheck__(cls, instance):
        # 直接检查类型, 不要调用 isinstance！
        if cls is KeiFloat and type(instance) is KeiInt:
            return True
        # 其他情况正常检查
        return type(instance) is cls or issubclass(type(instance), cls)

# ========== Kei 对象基类 ==========

class KeiBase(metaclass=KeiMeta):
    """所有Kei对象的基类"""
    def __init__(self, type_name: str):
        self._type = type_name
        self._methods: Dict[str, Callable] = {}
        self._props: Dict[str, KeiValue] = {}
        self.value: Any = None

    def __getitem__(self, key: Any) -> Any:
        """支持 obj[key] 和 obj.key """
        # 1. 先找方法
        if key in self._methods:
            method = self._methods[key]
            # 如果已经是 bound method, 直接返回
            if hasattr(method, '__self__'):
                return method
            # 否则包装
            return self._wrap_method(method)
        # 2. 再找属性
        if key in self._props:
            return self._props[key]
        # 3. 默认返回undefined
        return undefined

    def __setitem__(self, key: Any, _value: Any) -> None:
        """支持 obj[key] = value 和 obj.key = value"""
        self._props[key] = _value

    def _wrap_method(self, method: Callable) -> Callable:
        """包装方法, 支持 self 绑定"""
        def bound(*args: Any, **kwargs: Any) -> Any:
            return method(self, *args, **kwargs)
        return bound

    def __repr__(self) -> str:
        return f"<{self._type} object>"

# ========== 错误对象 ==========

class KeiException(Exception, KeiBase):
    """KeiLang 异常基类, 同时继承 Python 的 KeiError 和 KeiBase"""
    def __init__(self, types="", value=""):
        Exception.__init__(self, value)
        KeiBase.__init__(self, "error")

        self.value = value
        self.type = types

    def __str__(self):
        return self.value

    def __repr__(self):
        return f"{self.value}"

class KeiError(Exception, KeiBase):
    def __init__(self, types="", value="", code=None, linenum=-1):
        Exception.__init__(self, f"{types}: {value}" if value else types)
        KeiBase.__init__(self, "error")
        if isinstance(types, KeiString):
            self.types = types.value
        else:
            self.types = types

        if value:
            if isinstance(value, KeiString):
                self.value = value.value
            else:
                self.value = value
        else:
            self.value = self.types

        self.code    = code
        self.linenum = linenum

    def __repr__(self):
        return f"{self.types}"

class Error(KeiError):
    def __init__(self, types="", value=""):
        super().__init__(types, value)

        if isinstance(types, KeiString):
            self.types = types.value
        else:
            self.types = types

        self._methods = {
            'type': self.type,
            'message': self.message,
            'value': self.value
        }

        if isinstance(value, KeiString):
            self.value = value.value
        else:
            self.value = value

    def type(self):
        """返回错误类型"""
        return KeiString(self.types)

    def message(self):
        """返回错误信息"""
        return KeiString(self.value)

    # 删除 __getitem__ 或者保留但不影响
    def __getitem__(self, key):
        return super().__getitem__(key)

# ========== 数值类型 ==========

class KeiInt(KeiBase):
    def __init__(self, _value):
        super().__init__("int")
        if isinstance(_value, (KeiInt, KeiFloat)):
            self.value = int(_value.value)
        else:
            self.value = int(_value)

        self._methods = {
            "abs": self.abs,
            "pow": self.pow,
            "sqrt": self.sqrt,
        }

    def __setitem__(self, key, value):
        raise KeiError("IndexError", "整数不支持索引赋值")

    def __floordiv__(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            if other.value == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiInt(self.value // other.value)
        return KeiInt(self.value // other)

    def __bool__(self):
        return self.value > 0

    def __hash__(self):
        return hash(self.value)

    def abs(self):
        return KeiInt(abs(self.value))

    def pow(self, exponent):
        if isinstance(exponent, (KeiInt, KeiFloat)):
            return KeiFloat(self.value ** exponent.value)
        return KeiFloat(self.value ** exponent)

    def sqrt(self):
        return KeiFloat(math.sqrt(self.value))

    # 🔥 修复后的运算符重载 🔥
    def __add__(self, other):
        if isinstance(other, KeiInt):
            return KeiInt(self.value + other.value)
        if isinstance(other, KeiFloat):
            return KeiFloat(self.value + other.value)
        return KeiInt(self.value + other)

    def __sub__(self, other):
        if isinstance(other, KeiInt):
            return KeiInt(self.value - other.value)
        if isinstance(other, KeiFloat):
            return KeiFloat(self.value - other.value)
        return KeiInt(self.value - other)

    def __mul__(self, other):
        if isinstance(other, KeiInt):
            return KeiInt(self.value * other.value)
        if isinstance(other, KeiFloat):
            return KeiFloat(self.value * other.value)
        return KeiInt(self.value * other)

    def __truediv__(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            if other.value == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiFloat(self.value / other.value)
        if other == 0:
            raise KeiError("ZeroDivisionError", "除数不能为零")
        return KeiFloat(self.value / other)

    def __mod__(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            if other.value == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiInt(self.value % other.value)
        if other == 0:
            raise KeiError("ZeroDivisionError", "除数不能为零")
        return KeiInt(self.value % other)

    def __pow__(self, other):
        if isinstance(other, KeiInt):
            return KeiInt(self.value ** other.value)
        if isinstance(other, KeiFloat):
            return KeiFloat(self.value ** other.value)
        return KeiInt(self.value ** other)

    # 比较运算符（不用改，已经正确）
    def __eq__(self, other):
        if isinstance(other, KeiInt):
            return true if self.value == other.value else false
        if isinstance(other, KeiFloat):
            return true if float(self.value) == other.value else false
        return false

    def __ne__(self, other):
        if isinstance(other, KeiInt):
            return true if self.value != other.value else false
        if isinstance(other, KeiFloat):
            return true if float(self.value) != other.value else false
        return true

    def __lt__(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return true if self.value < other.value else false
        return false

    def __gt__(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return true if self.value > other.value else false
        return false

    def __le__(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return true if self.value <= other.value else false
        return false

    def __ge__(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return true if self.value >= other.value else false
        return false

    def __repr__(self):
        return f"{self.value}"

class KeiFloat(KeiBase):
    def __init__(self, _value):
        super().__init__("float")

        # 统一转成 Decimal
        if isinstance(_value, KeiInt):
            self.value = Decimal(_value.value)
        elif isinstance(_value, KeiFloat):
            self.value = Decimal(str(_value.value))  # 避免精度丢失
        elif isinstance(_value, (int, float)):
            # 关键！用字符串转，避免 float 精度问题
            self.value = Decimal(str(_value))
        elif isinstance(_value, str):
            self.value = Decimal(_value)
        elif isinstance(_value, Decimal):
            self.value = _value
        else:
            self.value = Decimal(str(_value))

        self._methods = {
            "abs": self.abs,
            "round": self.round,
            "floor": self.floor,
            "ceil": self.ceil,
            "take": self.take,
        }

    def __setitem__(self, key, value):
        raise KeiError("IndexError", "浮点数不支持索引赋值")

    def __floordiv__(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            if other.value == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiInt(self.value // other.value)
        return KeiInt(self.value // other)

    def __bool__(self):
        return self.value > 0

    def __hash__(self):
        return hash(self.value)

    def abs(self):
        return KeiFloat(abs(self.value))

    def round(self):
        # Decimal 的 round 需要指定舍入模式
        return KeiFloat(self.value.quantize(Decimal('1.')))

    def floor(self):
        # Decimal 没有直接的 floor，但可以用 to_integral 向下取整
        from decimal import ROUND_FLOOR
        return KeiInt(int(self.value.to_integral(rounding=ROUND_FLOOR)))

    def ceil(self):
        from decimal import ROUND_CEILING
        return KeiInt(int(self.value.to_integral(rounding=ROUND_CEILING)))

    def take(self, digits):
        if isinstance(digits, KeiInt):
            d = digits.value
        else:
            d = int(digits)
        # 保留 d 位小数
        quant = Decimal('1.' + '0' * d)
        try:
            return KeiFloat(self.value.quantize(quant))
        except InvalidOperation:
            raise KeiError("ArithmeticError", "浮点数精度错误: 精度不足")

    def places(self):
        """返回小数位数"""
        exp = self.value.as_tuple().exponent
        return abs(exp if exp < 0 else 0)

    # 运算符重载
    def __add__(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return KeiFloat(self.value + Decimal(str(other.value)))
        return KeiFloat(self.value + Decimal(str(other)))

    def __sub__(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return KeiFloat(self.value - Decimal(str(other.value)))
        return KeiFloat(self.value - Decimal(str(other)))

    def __mul__(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return KeiFloat(self.value * Decimal(str(other.value)))
        return KeiFloat(self.value * Decimal(str(other)))

    def __truediv__(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            if other.value == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiFloat(self.value / Decimal(str(other.value)))
        if other == 0:
            raise KeiError("ZeroDivisionError", "除数不能为零")
        return KeiFloat(self.value / Decimal(str(other)))

    def __pow__(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            # Decimal 的幂运算要求指数也是 Decimal
            return KeiFloat(self.value ** Decimal(str(other.value)))
        return KeiFloat(self.value ** Decimal(str(other)))

    # 比较运算符
    def __eq__(self, other):
        if isinstance(other, KeiFloat):
            return true if self.value == other.value else false
        if isinstance(other, KeiInt):
            return true if self.value == Decimal(other.value) else false
        return false

    def __ne__(self, other):
        if isinstance(other, KeiFloat):
            return true if self.value != other.value else false
        if isinstance(other, KeiInt):
            return true if self.value != Decimal(other.value) else false
        return true

    def __lt__(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return true if self.value < Decimal(str(other.value)) else false
        return false

    def __gt__(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return true if self.value > Decimal(str(other.value)) else false
        return false

    def __le__(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return true if self.value <= Decimal(str(other.value)) else false
        return false

    def __ge__(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return true if self.value >= Decimal(str(other.value)) else false
        return false

    def __repr__(self):
        # 如果是整数，显示为整数
        if self.value == self.value.to_integral():
            return str(int(self.value))
        # 否则去掉末尾的0
        s = str(self.value)
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
        return s

# ========== 布尔类型 ==========

class KeiBool(KeiBase):
    _instance_true = None
    _instance_false = None

    def __new__(cls, value):
        if value:
            if cls._instance_true is None:
                cls._instance_true = super().__new__(cls)
            return cls._instance_true
        else:
            if cls._instance_false is None:
                cls._instance_false = super().__new__(cls)
            return cls._instance_false

    def __init__(self, value):
        if not hasattr(self, '_initialized'):
            super().__init__("bool")
            self.value = value
            self._initialized = True

            self._methods = {
                "not": self.not_,
                "and": self.and_,
                "or": self.or_,
                "xor": self.xor,
            }

    def not_(self):
        return KeiBool(not self.value)

    def and_(self, other):
        if isinstance(other, KeiBool):
            return KeiBool(self.value and other.value)
        return KeiBool(self.value and bool(other))

    def or_(self, other):
        if isinstance(other, KeiBool):
            return KeiBool(self.value or other.value)
        return KeiBool(self.value or bool(other))

    def xor(self, other):
        if isinstance(other, KeiBool):
            return KeiBool(self.value ^ other.value)
        return KeiBool(self.value ^ bool(other))

    def __bool__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, KeiBool):
            return true if self.value == other.value else false
        return false

    def __repr__(self):
        return "true" if self.value else "false"

true = KeiBool(True)
false = KeiBool(False)

# ========== 字符串类型 ==========

class KeiString(KeiBase):
    def __init__(self, _value):
        super().__init__("string")
        if isinstance(_value, KeiString):
            self.value = _value.value
        else:
            self.value = str(_value)

        self._methods = {
            "upper": self.upper,
            "lower": self.lower,
            "split": self.split,
            "join": self.join,
            "replace": self.replace,
            "strip": self.strip,
            "startswith": self.startswith,
            "endswith": self.endswith,
            "contains": self.contains,
            "length": self.length,
            "char_at": self.char_at,
            "index_of": self.index_of,
            "center": self.center
        }

    def __setitem__(self, key, value):
        """支持 str[index] = new_str，可以插入任意长度"""
        # 处理索引
        if isinstance(key, KeiInt):
            idx = key.value
        elif isinstance(key, int):
            idx = key
        else:
            raise KeiError("TypeError", "字符串索引必须是整数")

        # 支持负数索引
        if idx < 0:
            idx = len(self.value) + idx

        if 0 <= idx < len(self.value):
            # 把 value 转成字符串
            if isinstance(value, KeiString):
                new_str = value.value
            else:
                new_str = str(value)

            # 替换从 idx 开始的字符
            # 原字符串: 前面 + 新字符串 + 后面
            self.value = self.value[:idx] + new_str + self.value[idx+1:]
        else:
            return undefined

    def __bool__(self):
        return len(self.value) > 0

    def __hash__(self):
        return hash(self.value)

    def upper(self):
        return KeiString(self.value.upper())

    def lower(self):
        return KeiString(self.value.lower())

    def center(self, width, fill=' '):
        """字符串居中

        Args:
            width: 总宽度 (KeiInt 或 int)
            fill: 填充字符 (KeiString 或 str)，默认为空格

        Returns:
            居中对齐后的 KeiString
        """
        # 转换参数
        if isinstance(width, KeiInt):
            w = width.value
        else:
            w = int(width)

        if isinstance(fill, KeiString):
            fill_char = fill.value[0] if fill.value else ' '
        else:
            fill_char = str(fill)[0] if str(fill) else ' '

        # 获取字符串长度（支持中文）
        text_len = len(self.value)

        # 如果宽度小于等于字符串长度，返回原字符串
        if w <= text_len:
            return self

        # 计算左右填充
        left = (w - text_len) // 2
        right = w - text_len - left

        # 构建结果
        result = fill_char * left + self.value + fill_char * right
        return KeiString(result)

    def split(self, separator=None):
        if separator is None or separator is undefined:
            parts = self.value.split()
        else:
            if isinstance(separator, KeiString):
                sep = separator.value
            else:
                sep = str(separator)
            parts = self.value.split(sep)
        return KeiList([KeiString(p) for p in parts])

    def join(self, iterable):
        if isinstance(iterable, KeiList):
            items = [str(item) for item in iterable.items]
        else:
            items = [str(iterable)]
        return KeiString(self.value.join(items))

    def replace(self, old, new):
        if isinstance(old, KeiString):
            old_str = old.value
        else:
            old_str = str(old)
        if isinstance(new, KeiString):
            new_str = new.value
        else:
            new_str = str(new)
        return KeiString(self.value.replace(old_str, new_str))

    def strip(self):
        return KeiString(self.value.strip())

    def startswith(self, prefix):
        if isinstance(prefix, KeiString):
            p = prefix.value
        else:
            p = str(prefix)
        return true if self.value.startswith(p) else false

    def endswith(self, suffix):
        if isinstance(suffix, KeiString):
            s = suffix.value
        else:
            s = str(suffix)
        return true if self.value.endswith(s) else false

    def contains(self, substr):
        if isinstance(substr, KeiString):
            s = substr.value
        else:
            s = str(substr)
        return true if s in self.value else false

    def length(self):
        return KeiInt(len(self.value))

    def char_at(self, index):
        if isinstance(index, KeiInt):
            i = index.value
        else:
            i = int(index)
        if 0 <= i < len(self.value):
            return KeiString(self.value[i])
        return undefined

    def index_of(self, substr):
        if isinstance(substr, KeiString):
            s = substr.value
        else:
            s = str(substr)
        try:
            return KeiInt(self.value.index(s))
        except ValueError:
            return KeiInt(-1)

    # 运算符重载
    def __add__(self, other):
        if isinstance(other, KeiString):
            return KeiString(self.value + other.value)
        return KeiString(self.value + str(other))

    def __mul__(self, other):
        """字符串乘法，支持重复"""
        if isinstance(other, (KeiInt, int)):
            n = other.value if isinstance(other, KeiInt) else other
            return KeiString(self.value * n)
        return undefined

    def __rmul__(self, other):
        """支持 3 * "Hello" 这种形式"""
        return self.__mul__(other)

    # 比较运算符
    def __eq__(self, other):
        if isinstance(other, KeiString):
            return true if self.value == other.value else false
        return false

    def __ne__(self, other):
        if isinstance(other, KeiString):
            return true if self.value != other.value else false
        return true

    def __lt__(self, other):
        if isinstance(other, KeiString):
            return true if self.value < other.value else false
        return false

    def __gt__(self, other):
        if isinstance(other, KeiString):
            return true if self.value > other.value else false
        return false

    def __le__(self, other):
        if isinstance(other, KeiString):
            return true if self.value <= other.value else false
        return false

    def __ge__(self, other):
        if isinstance(other, KeiString):
            return true if self.value >= other.value else false
        return false

    def __repr__(self):
        return f'{self.value}'

    def __getitem__(self, key):
        """支持字符串索引和切片"""

        # 处理切片
        if isinstance(key, slice):
            start = key.start
            stop = key.stop
            step = key.step if key.step is not None else 1

            # 转换 Kei 对象为 Python 值
            if isinstance(start, KeiInt):
                start = start.value
            if isinstance(stop, KeiInt):
                stop = stop.value
            if isinstance(step, KeiInt):
                step = step.value

            # 处理负数索引
            length = len(self.value)
            if start is None:
                start = 0 if step > 0 else length - 1
            elif start < 0:
                start = length + start

            if stop is None:
                stop = length if step > 0 else -1
            elif stop < 0:
                stop = length + stop

            # 生成切片结果
            result = []
            i = start
            while (step > 0 and i < stop) or (step < 0 and i > stop):
                if 0 <= i < length:
                    result.append(self.value[i])
                i += step

            return KeiString(''.join(result))

        # 处理数字索引
        if isinstance(key, KeiInt):
            idx = key.value
        elif isinstance(key, int):
            idx = key
        else:
            return super().__getitem__(key)

        # ✨ 支持负数索引 ✨
        if idx < 0:
            idx = len(self.value) + idx

        if 0 <= idx < len(self.value):
            return KeiString(self.value[idx])
        return undefined

# ========== 列表类型 ==========

class KeiList(KeiBase):
    def __init__(self, _items=None):
        super().__init__("list")
        self.items = _items if _items is not None else []

        self._methods = {
            "push": self.push,
            "pop": self.pop,
            "get": self.get,
            "set": self.set,
            "length": self.length,
            "map": self.map,
            "filter": self.filter,
            "reduce": self.reduce,
            "foreach": self.foreach,
            "slice": self.slice,
            "concat": self.concat,
            "join": self.join,
            "reverse": self.reverse,
            "sort": self.sort,
            "index_of": self.index_of,
            "includes": self.includes,
            "uniq": self.uniq,
            "append": self.append,
        }

    def __bool__(self):
        return len(self.items) > 0

    def append(self, *values):
        for v in values:
            self.items.append(v)
        return self if values else undefined

    def uniq(self):
        result = []
        if self.items:
            for i in self.items:
                if i not in result:
                    result.append(i)

        return KeiList(result)

    def push(self, *values):
        for v in values:
            self.items.append(v)
        return self if values else undefined

    def pop(self):
        if not self.items:
            return undefined
        return self.items.pop()

    def get(self, index):
        if isinstance(index, KeiInt):
            i = index.value
        else:
            i = int(index)
        if 0 <= i < len(self.items):
            return self.items[i]
        return undefined

    def set(self, index, _value):
        if isinstance(index, KeiInt):
            i = index.value
        else:
            i = int(index)
        if 0 <= i < len(self.items):
            self.items[i] = _value
        elif i == len(self.items):
            self.items.append(_value)
        else:
            return undefined
        return _value

    def length(self):
        return KeiInt(len(self.items))

    def map(self, func):
        result = []
        for item in self.items:
            if callable(func):
                new_val = func(item)
            else:
                new_val = func(item)
            result.append(new_val)
        return KeiList(result)

    def filter(self, func):
        result = []
        for item in self.items:
            if callable(func):
                if func(item):
                    result.append(item)
            else:
                if func(item):
                    result.append(item)
        return KeiList(result)

    def reduce(self, func, initial=undefined):
        if not self.items:
            return initial

        # 初始化
        if initial is undefined:
            acc = self.items[0]
            start = 1
        else:
            acc = initial
            start = 0

        # 累加
        for i in range(start, len(self.items)):
            # 调用 func，但确保返回的是值不是列表
            result = func(acc, self.items[i])

            # 如果结果是列表且长度为1，可能是包装错了
            if isinstance(result, KeiList) and len(result.items) == 1:
                acc = result.items[0]
            else:
                acc = result

        return acc

    def foreach(self, func):
        for item in self.items:
            func(item)
        return undefined

    def slice(self, start=None, end=None):
        s = start.value if isinstance(start, KeiInt) else (start or 0)
        e = end.value if isinstance(end, KeiInt) else (end if end is not None else len(self.items))
        return KeiList(self.items[s:e])

    def concat(self, other):
        if isinstance(other, KeiList):
            return KeiList(self.items + other.items)
        return KeiList(self.items + [other])

    def join(self, separator=""):
        if isinstance(separator, KeiString):
            sep = separator.value
        else:
            sep = str(separator)
        return KeiString(sep.join(str(item) for item in self.items))

    def reverse(self):
        self.items.reverse()
        return self

    def sort(self, key=None, reverse=false):
        rev = reverse.value if isinstance(reverse, KeiBase) else bool(reverse)
        if key and key is not undefined:
            self.items.sort(key=lambda x: key(x).value if isinstance(key(x), KeiBase) else key(x), reverse=rev)
        else:
            self.items.sort(reverse=rev)
        return self

    def index_of(self, _value):
        try:
            return KeiInt(self.items.index(_value))
        except ValueError:
            return KeiInt(-1)

    def includes(self, _value):
        return true if _value in self.items else false

    def __setitem__(self, key, value):
        if isinstance(key, KeiInt):
            idx = key.value
        elif isinstance(key, int):
            idx = key
        else:
            raise KeiError("TypeError", "列表索引必须是整数")

        if 0 <= idx < len(self.items):
            self.items[idx] = value
        else:
            return undefined

    def __or__(self, other):
        """列表的 | 操作 - 合并"""
        if isinstance(other, KeiList):
            # 合并
            result = []

            for item in self.items + other.items:
                result.append(item)

            return KeiList(result)
        return undefined

    def __getitem__(self, key):
        """支持 list[index] 和 list[start:end:step] 语法"""

        # 处理切片
        if isinstance(key, slice):
            # 获取切片的 start, stop, step
            start = key.start
            stop = key.stop
            step = key.step if key.step is not None else 1

            # 转换 Kei 对象为 Python 值
            if isinstance(start, KeiInt):
                start = start.value
            if isinstance(stop, KeiInt):
                stop = stop.value
            if isinstance(step, KeiInt):
                step = step.value

            # 处理负数索引
            length = len(self.items)
            if start is None:
                start = 0 if step > 0 else length - 1
            elif start < 0:
                start = length + start

            if stop is None:
                stop = length if step > 0 else -1
            elif stop < 0:
                stop = length + stop

            # 生成切片结果
            result = []
            i = start
            while (step > 0 and i < stop) or (step < 0 and i > stop):
                if 0 <= i < length:
                    result.append(self.items[i])
                i += step

            return KeiList(result)

        # 处理数字索引
        if isinstance(key, KeiInt):
            idx = key.value
        elif isinstance(key, int):
            idx = key
        else:
            return super().__getitem__(key)

        # ✨✨✨ 新增：支持负数索引 ✨✨✨
        if idx < 0:
            idx = len(self.items) + idx

        if 0 <= idx < len(self.items):
            return self.items[idx]
        return undefined

    # 运算符重载
    def __add__(self, other):
        if isinstance(other, KeiList):
            return KeiList(self.items + other.items)
        return KeiList(self.items + [other])

    def __mul__(self, other):
        if isinstance(other, (KeiInt, int)):
            n = other.value if isinstance(other, KeiInt) else other
            return KeiList(self.items * n)
        return undefined

    def __sub__(self, other):
        if isinstance(other, KeiList):
            result = [x for x in self.items if x not in other.items]
            return KeiList(result)
        return KeiList([x for x in self.items if x != other])

    # 比较运算符
    def __eq__(self, other):
        if isinstance(other, KeiList):
            if len(self.items) != len(other.items):
                return false
            for i, j in zip(self.items, other.items):
                if i != j:
                    return false
            return true
        return false

    def __ne__(self, other):
        if isinstance(other, KeiList):
            return true if not self.__eq__(other) else false
        return true

    def __lt__(self, other):
        if isinstance(other, KeiList):
            return true if len(self.items) < len(other.items) else false
        return false

    def __gt__(self, other):
        if isinstance(other, KeiList):
            return true if len(self.items) > len(other.items) else false
        return false

    def __le__(self, other):
        if isinstance(other, KeiList):
            return true if len(self.items) <= len(other.items) else false
        return false

    def __ge__(self, other):
        if isinstance(other, KeiList):
            return true if len(self.items) >= len(other.items) else false
        return false

    def __repr__(self):
        items = ", ".join(repr(i) for i in self.items)
        return f"[{items}]"

# ========== 字典类型 ==========

class KeiDict(KeiBase):
    def __init__(self, pairs=None):
        super().__init__("dict")
        self.items = pairs if pairs is not None else {}

        self._methods = {
            "keys": self.keys,
            "values": self.values,
            "get": self.get,
            "set": self.set,
            "has": self.has,
            "delete": self.delete,
            "clear": self.clear,
            "length": self.length,
            "update": self.update,
            "map": self.map,
        }

    def __or__(self, other):
        """字典的 | 操作 - 合并（类似 Python 3.9+ 的 | 操作符）"""
        if isinstance(other, KeiDict):
            new_dict = self.items.copy()
            new_dict.update(other.items)
            return KeiDict(new_dict)
        return undefined

    def __getitem__(self, key):
        """支持 dict[key] 语法和方法查找"""

        # 1. 先尝试方法查找（通过父类）
        if isinstance(key, str) or isinstance(key, KeiString):
            key_str = key.value if isinstance(key, KeiString) else key
            # 检查是否是方法名
            if key_str in self._methods:
                return super().__getitem__(key_str)

        # 将 Kei 对象转换为 Python 值作为键
        if isinstance(key, KeiString):
            k = key.value
        elif isinstance(key, KeiInt):
            k = key.value
        elif isinstance(key, KeiFloat):
            k = key.value
        elif isinstance(key, KeiBool):
            k = key.value
        else:
            k = key

        # 查找键
        if k in self.items:
            return self.items[k]

        # 3. 最后尝试父类的方法查找（如果上面没处理到）
        return super().__getitem__(key)

    def __setitem__(self, key, _value):
        """支持 dict[key] = value 语法"""
        # 将 Kei 对象转换为 Python 值作为键
        if isinstance(key, KeiString):
            k = key.value
        elif isinstance(key, KeiInt):
            k = key.value
        elif isinstance(key, KeiFloat):
            k = key.value
        elif isinstance(key, KeiBool):
            k = key.value
        else:
            k = key

        self.items[k] = _value

    def map(self, func):
        for k in self.items:
            self.items[k] = func(self.items[k])
        return self

    def keys(self):
        return KeiList([KeiString(k) for k in self.items.keys()])

    def values(self):
        return KeiList(list(self.items.values()))

    def get(self, key, default=undefined):
        if isinstance(key, str):
            return self.items.get(key, default)
        if isinstance(key, KeiString):
            return self.items.get(key.value, default)
        return self.items.get(str(key), default)

    def set(self, key, _value):
        if isinstance(key, str):
            self.items[key] = _value
        elif isinstance(key, KeiString):
            self.items[key.value] = _value
        else:
            self.items[str(key)] = _value
        return _value

    def has(self, key):
        if isinstance(key, str):
            return true if key in self.items else false
        if isinstance(key, KeiString):
            return true if key.value in self.items else false
        return true if str(key) in self.items else false

    def delete(self, key):
        if isinstance(key, str):
            if key in self.items:
                del self.items[key]
                return true
        elif isinstance(key, KeiString):
            k = key.value
            if k in self.items:
                del self.items[k]
                return true
        else:
            k = str(key)
            if k in self.items:
                del self.items[k]
                return true
        return false

    def clear(self):
        self.items.clear()
        return null

    def length(self):
        return KeiInt(len(self.items))

    def update(self, other):
        if isinstance(other, KeiDict):
            self.items.update(other.items)
        elif isinstance(other, dict):
            self.items.update(other)
        return self

    def __contains__(self, key):
        """支持 'key' in dict 语法"""
        # 将 Kei 对象转换为 Python 值作为键
        if isinstance(key, KeiString):
            k = key.value
        elif isinstance(key, KeiInt):
            k = key.value
        elif isinstance(key, KeiFloat):
            k = key.value
        elif isinstance(key, KeiBool):
            k = key.value
        else:
            k = key

        return k in self.items

    # 运算符重载
    def __add__(self, other):
        if isinstance(other, KeiDict):
            new_dict = self.items.copy()
            new_dict.update(other.items)
            return KeiDict(new_dict)
        return undefined

    # 比较运算符
    def __eq__(self, other):
        if isinstance(other, KeiDict):
            if len(self.items) != len(other.items):
                return false
            for k, v in self.items.items():
                if k not in other.items or other.items[k] != v:
                    return false
            return true
        return false

    def __ne__(self, other):
        if isinstance(other, KeiDict):
            return true if not self.__eq__(other) else false
        return true

    def __bool__(self):
        return len(self.items) > 0

    def __repr__(self):
        items = ", ".join(f"{k}: {repr(v)}" for k, v in self.items.items())
        return f"{{{items}}}"

# ========== 函数类型 ==========

class KeiFunction(KeiBase):
    __kei__ = {}

    def __init__(self, func_obj: dict, env: dict):
        super().__init__("function")
        self.func_obj = func_obj
        self.env = env
        self.__name__ = func_obj['name'] if func_obj['name'] else "lambda"

        # 设置父环境引用（这是实际的环境，包含所有变量值）
        self.__env__ = func_obj.get('closure', env)

    def __call__(self, *args, **kwargs):
        """调用 KeiLang 函数"""
        from kei import runtoken

        if KeiFunction.__kei__.get('stack') is None:
            KeiFunction.__kei__['stack'] = []

        KeiFunction.__kei__['stack'].append(self.__name__)

        params     = self.func_obj['params']  # ['a', 'b', '*rest'] 或 ['a', 'b', '**kw']
        typeassert = self.func_obj.get('typeassert', None)

        # ===== 1. 分离参数类型 =====
        regular_params = []      # 普通参数名
        star_param = None        # *args 参数名
        starstar_param = None    # **kwargs 参数名

        for p in params:
            if p.startswith('**'):
                starstar_param = p[2:]  # 去掉 **
            elif p.startswith('*'):
                star_param = p[1:]      # 去掉 *
            else:
                regular_params.append(p)

        # ===== 2. 合并位置参数和关键字参数 =====
        # 先把所有位置参数转成列表
        all_args = list(args)

        # 复制 kwargs，因为我们要修改
        remaining_kwargs = kwargs.copy()

        # ===== 3. 填充普通参数 =====
        # 先填充已经有的位置参数
        final_args = []
        for i, param_name in enumerate(regular_params):
            if i < len(all_args):
                # 有位置参数
                final_args.append(all_args[i])

            elif param_name in remaining_kwargs:
                # 从关键字参数里拿
                final_args.append(remaining_kwargs.pop(param_name))

            elif param_name in self.func_obj.get('defaults', {}):
                # 使用默认值
                default_val_node = self.func_obj['defaults'][param_name]

                default_val, _ = runtoken(default_val_node, self.__env__)
                final_args.append(default_val)
            else:
                # 都没有，用 undefined
                final_args.append(undefined)

        # ===== 4. 处理剩余的位置参数 =====
        # 超出普通参数数量的位置参数
        extra_args = all_args[len(regular_params):]

        # ===== 5. 准备调用环境 =====
        # 创建新的函数调用环境
        new_env = {}

        # 设置父环境引用
        try:
            new_env = copy.deepcopy(self.__env__)
        except:
            try:
                new_env = copy.copy(self.__env__)
            except:
                new_env = self.__env__.copy()

        # ===== 6. 绑定参数到环境 =====
        # 绑定普通参数
        for i, param_name in enumerate(regular_params):
            new_env[param_name] = final_args[i]

        # 绑定 *args 参数
        if star_param:
            # 把所有剩余的位置参数打包成 KeiList
            star_values = []
            for arg in extra_args:
                star_values.append(arg)
            new_env[star_param] = KeiList(star_values)

        # 绑定 **kwargs 参数
        if starstar_param:
            # 把剩余的关键字参数打包成 KeiDict
            new_env[starstar_param] = KeiDict(remaining_kwargs)
        elif remaining_kwargs:
            # 没有 **kwargs 但有多余的关键字参数，报错
            raise KeiError("SyntaxError", f"函数 {self.__name__} 收到未预料的关键字参数: {list(remaining_kwargs.keys())}")

        # ===== 7. 执行函数体 =====

        try:
            result = null
            for stmt in self.func_obj['body']:
                val, is_return = runtoken(stmt, new_env)
                if is_return:
                    result = val
                    break

            if bool(new_env.get('__typeassert__', False)) and typeassert is not None:
                from kei import runtoken

                hint = runtoken(typeassert, new_env)[0]

                if isinstance(hint, KeiList):
                    for h in hint.items:
                        if type(result) is KeiInt and h is KeiFloat:
                            break

                        if not isinstance(h, type):
                            h = type(h)

                        if (isinstance(result, h) or (isinstance(result, type) and issubclass(result, h))):
                            break
                    else:
                        raise KeiError("TypeError", f"类型错误: 期望 {content(hint)}, 得到 {content(type(result))}")

                else:
                    if type(result) is KeiInt and hint is KeiFloat:
                        return result

                    if not isinstance(hint, type):
                        hint = type(hint)

                    if not (isinstance(result, hint) or (isinstance(result, type) and issubclass(result, hint))):
                        raise KeiError("TypeError", f"类型错误: 期望 {content(hint)}, 得到 {content(type(result))}")

            print(id(KeiFunction.__kei__))
            if not KeiFunction.__kei__['catch']:
                KeiFunction.__kei__['stack'].pop()
            return result

        except:
            raise

    def __repr__(self) -> str:
        return f"<function {self.__name__}>"

# ========== 类类型 ==========

class KeiClass(KeiBase):
    def __init__(self, class_obj: dict, env: dict):
        super().__init__("class")
        self.class_obj = class_obj
        self.env = env
        self.value = class_obj
        self.__name__ = class_obj['name']

    def __call__(self, *args: Any, **kwargs: Any) -> 'KeiInstance':
        """实例化类"""

        # 创建实例
        instance = KeiInstance(self)

        # 查找 __init__ 方法
        init_method = self.class_obj['methods_map'].get('__init__')
        if init_method:
            try:
                new_env = copy.deepcopy(init_method['closure'])
            except:
                try:
                    new_env = copy.copy(init_method['closure'])
                except:
                    new_env = init_method['closure']

            new_env['self'] = instance

            # 绑定参数（跳过 self）
            params = init_method['params'][1:]  # 去掉 self

            for i, p in enumerate(params):
                if i < len(args):
                    new_env[p] = args[i]
                elif p in kwargs:
                    new_env[p] = kwargs[p]
                elif p in init_method.get('defaults', {}):
                    from kei import runtoken
                    default_val, _ = runtoken(init_method['defaults'][p], init_method['closure'])
                    new_env[p] = default_val
                else:
                    new_env[p] = undefined

            # 执行 __init__ 方法体
            from kei import runtoken
            for stmt in init_method['body']:
                val, is_return = runtoken(stmt, new_env)
                if is_return and val is not None:
                    break

        return instance

    def __getitem__(self, key):
        if key in self.class_obj['methods_map']:
            method_obj = self.class_obj['methods_map'][key]
            if method_obj.get('is_property'):
                # 属性：返回描述符
                return KeiProperty(method_obj)
            return KeiMethod(method_obj, self)

    def __repr__(self) -> str:
        return f"<class {self.__name__}>"

class KeiProperty(KeiBase):
    """属性描述符"""
    def __init__(self, method_obj: dict):
        super().__init__("property")
        self.method_obj = method_obj
        self.__name__ = method_obj['name']

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        # 调用方法获取值
        bound = KeiBoundMethod(self.method_obj, obj)
        return bound()

    def __repr__(self):
        return f"<property {self.__name__}>"

# ========== 实例类型 ==========

class KeiInstance(KeiBase):
    """类的实例"""
    def __init__(self, klass: KeiClass):
        super().__init__("instance")
        self._class = klass
        self._attrs = {}  # 实例属性

    def __getitem__(self, key):
        # 1. 先找实例属性
        if key in self._attrs:
            return self._attrs[key]

        # 2. 找类方法
        if hasattr(self._class, 'class_obj') and 'methods_map' in self._class.class_obj:
            methods_map = self._class.class_obj['methods_map']
            if key in methods_map:
                method_obj = methods_map[key]
                # 检查是否是属性
                if method_obj.get('is_property'):
                    # 属性：直接调用并返回值
                    bound = KeiBoundMethod(method_obj, self)
                    return bound()

                # 普通方法：返回绑定方法
                return KeiBoundMethod(method_obj, self)

        return undefined

    def __setitem__(self, key, _value):
        """设置实例属性"""
        self._attrs[key] = _value

    def _get_method(self, name):
        """获取方法（自动绑定）"""
        method = self[name]
        if method is undefined:
            return None
        return method

    # ========== 运算符重载 ==========
    def __add__(self, other):
        method = self._get_method('__add__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method(other)
        return undefined

    def __sub__(self, other):
        method = self._get_method('__sub__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method(other)
        return undefined

    def __mul__(self, other):
        method = self._get_method('__mul__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method(other)
        return undefined

    def __truediv__(self, other):
        method = self._get_method('__truediv__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method(other)
        return undefined

    def __floordiv__(self, other):
        method = self._get_method('__floordiv__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method(other)
        return undefined

    def __mod__(self, other):
        method = self._get_method('__mod__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method(other)
        return undefined

    def __pow__(self, other):
        method = self._get_method('__pow__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method(other)
        return undefined

    def __eq__(self, other):
        method = self._get_method('__eq__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method(other)

        return true if self is other else false

    def __ne__(self, other):
        method = self._get_method('__ne__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method(other)
        return true if self is not other else false

    def __lt__(self, other):
        method = self._get_method('__lt__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method(other)
        return undefined

    def __gt__(self, other):
        method = self._get_method('__gt__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method(other)
        return undefined

    def __le__(self, other):
        method = self._get_method('__le__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method(other)
        return undefined

    def __ge__(self, other):
        method = self._get_method('__ge__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method(other)
        return undefined

    def __and__(self, other):
        method = self._get_method('__and__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method(other)
        return undefined

    def __or__(self, other):
        method = self._get_method('__or__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method(other)
        return undefined

    def __xor__(self, other):
        method = self._get_method('__xor__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method(other)
        return undefined

    def __neg__(self):
        method = self._get_method('__neg__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method()
        return undefined

    def __pos__(self):
        method = self._get_method('__pos__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method()
        return undefined

    def __invert__(self):
        method = self._get_method('__invert__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method()
        return undefined

    def __repr__(self):
        return f"<instance {self._class.__name__}>"

    def __call__(self):
        method = self._get_method('__call__')
        if method is undefined or not callable(method):
            return undefined
        if method:
            return method()
        return undefined

# ========== 方法类型 ==========

class KeiMethod(KeiBase):
    """类的方法（未绑定）"""
    def __init__(self, method_obj: dict, klass: KeiClass):
        super().__init__("method")
        self.method_obj = method_obj
        self.klass = klass
        self.__name__ = method_obj['name']
        # 检查是否是静态方法
        self.is_static = False
        self.is_property = method_obj.get('is_property', False)
        if 'decorators' in method_obj:
            for dec in method_obj['decorators']:
                if dec['value'] == 'static':
                    self.is_static = True
                    break

    def bind(self, instance: KeiInstance) -> 'KeiBoundMethod':
        """绑定方法到实例"""
        return KeiBoundMethod(self.method_obj, instance)

    def __get__(self, obj, objtype=None):
        """描述符协议，让方法变成属性"""
        if obj is None:
            return self
        if self.is_property:
            # 直接调用方法，返回结果
            bound = KeiBoundMethod(self.method_obj, obj)
            return bound()
        return self.bind(obj)

    def __call__(self, *args, **kwargs):
        """作为未绑定方法调用"""
        if self.is_static:
            # 静态方法：直接调用，不需要 self
            # 创建绑定方法但没有实例
            bound = KeiBoundMethod(self.method_obj, None)
            return bound(*args, **kwargs)
        else:
            # 普通方法：需要 self 参数
            if not args or not isinstance(args[0], KeiInstance):
                raise KeiError("NameError", f"未绑定方法 {self.__name__} 需要 self 参数")
            instance = args[0]
            bound = self.bind(instance)
            return bound(*args[1:], **kwargs)

    def __repr__(self):
        return f"<method {self.__name__}>"

class KeiBoundMethod(KeiBase):
    """绑定到实例的方法"""
    def __init__(self, method_obj: dict, instance: KeiInstance | None):
        super().__init__("bound_method")
        self.method_obj = method_obj
        self.instance = instance
        self.__name__ = method_obj['name']

    def __call__(self, *args, **kwargs):
        # 创建新的环境
        new_env = {}

        # 复制闭包
        if 'closure' in self.method_obj:
            for key, value in self.method_obj['closure'].items():
                if key == '__parent__':
                    new_env[key] = value
                elif isinstance(value, (int, float, str, bool, _undefined, _null)):
                    new_env[key] = value
                elif value is true or value is false:
                    new_env[key] = value
                else:
                    try:
                        new_env[key] = copy.copy(value)
                    except:
                        new_env[key] = value

        # 设置 self（如果有实例）
        if self.instance is not None:
            new_env['self'] = self.instance

        # 绑定参数
        params = self.method_obj['params']
        if self.instance is not None:
            params_to_use = params[1:]
        else:
            params_to_use = params

        for i, p in enumerate(params_to_use):
            if i < len(args):
                new_env[p] = args[i]
            elif p in kwargs:
                new_env[p] = kwargs[p]
            else:
                new_env[p] = undefined

        # 执行方法体
        result = None
        for stmt in self.method_obj['body']:
            from kei import runtoken
            val, is_return = runtoken(stmt, new_env)
            if is_return:
                result = val
                break
        return result

    def __repr__(self):
        return f"<method {self.__name__}>"

# ========== 命名空间类型 ==========

class KeiNamespace(KeiBase):
    def __init__(self, name: str, env: dict):
        super().__init__("namespace")
        self.__name__ = name
        self.env = env

    def __getattr__(self, key):
        """直接返回 KeiFunction 对象"""
        if key in self.env:
            return self.env[key]
        return undefined

    def __getitem__(self, key):
        result = self.env.get(key, undefined)

        return result

    def __repr__(self):
        return f"<namespace {self.__name__}>"

# ========== 引用类型 ==========

class KeiRef(KeiBase):
    """引用类 - 指向环境中的变量"""
    def __init__(self, env, name):
        self._env = env      # 环境引用
        self._name = name    # 变量名

        super().__init__("ref")

    def _resolve(self):
        """解析到实际对象（处理链式引用）"""
        target = self._env.get(self._name)
        # 如果 target 也是 Ref，继续解析
        while isinstance(target, KeiRef):
            target = target._resolve()
        return target

    def __getattr__(self, name):
        """所有属性访问转发给实际对象"""
        # 保护内部属性
        if name in ('_env', '_name', '_resolve'):
            return object.__getattribute__(self, name)
        target = self._resolve()
        if target is None:
            raise KeiError("NameError", f"引用的变量 {self._name} 不存在")
        return getattr(target, name)

    def __setattr__(self, name, value):
        """属性赋值转发给实际对象"""
        if name in ('_env', '_name'):
            super().__setattr__(name, value)
            return
        target = self._resolve()
        if target is None:
            raise KeiError("NameError", f"引用的变量 {self._name} 不存在")
        setattr(target, name, value)

    def __getitem__(self, key):
        """索引访问转发"""
        target = self._resolve()
        return target[key]

    def __setitem__(self, key, value):
        """索引赋值转发"""
        target = self._resolve()
        target[key] = value

    def __call__(self, *args, **kwargs):
        """函数调用转发"""
        target = self._resolve()
        return target(*args, **kwargs)

    # ==== 运算符重载 ====
    def __add__(self, other):
        target = self._resolve()
        return target + other

    def __sub__(self, other):
        target = self._resolve()
        return target - other

    def __mul__(self, other):
        target = self._resolve()
        return target * other

    def __truediv__(self, other):
        target = self._resolve()
        return target / other

    def __floordiv__(self, other):
        target = self._resolve()
        return target // other

    def __mod__(self, other):
        target = self._resolve()
        return target % other

    def __pow__(self, other):
        target = self._resolve()
        return target ** other

    # ==== 比较运算符 ====
    def __eq__(self, other):
        target = self._resolve()
        return target == other

    def __ne__(self, other):
        target = self._resolve()
        return target != other

    def __lt__(self, other):
        target = self._resolve()
        return target < other

    def __gt__(self, other):
        target = self._resolve()
        return target > other

    def __le__(self, other):
        target = self._resolve()
        return target <= other

    def __ge__(self, other):
        target = self._resolve()
        return target >= other

    # ==== 类型转换 ====
    def __bool__(self):
        target = self._resolve()
        return bool(target)

    def __len__(self):
        target = self._resolve()
        return len(target)

    def __iter__(self):
        target = self._resolve()
        return iter(target)

    def __contains__(self, item):
        target = self._resolve()
        return item in target

    # ==== value 属性 ====
    @property
    def value(self):
        target = self._resolve()
        if hasattr(target, 'value'):
            return target.value
        return target

    @value.setter
    def value(self, new_val):
        target = self._resolve()
        if hasattr(target, 'value'):
            target.value = new_val
        elif hasattr(target, 'items'):
            # items 类型怎么处理？这语义不明确
            raise KeiError("SyntaxError", "不能直接给容器类型赋值 value")
        else:
            self._env[self._name] = new_val

    @property
    def items(self):
        target = self._resolve()
        if hasattr(target, 'items'):
            return target.items
        raise AttributeError("'KeiRef' object has no attribute 'items'")

    @items.setter
    def items(self, new_items):
        target = self._resolve()
        if hasattr(target, 'items'):
            target.items = new_items
        else:
            raise AttributeError("'KeiRef' object has no attribute 'items'")

    # ==== 字符串表示 ====
    def __repr__(self):
        target = self._resolve()
        return repr(target)

    def __str__(self):
        target = self._resolve()
        return str(target)

# ========== 工厂函数 ==========

def content(obj, _seen=None, _depth=0, _in_container=False):
    """统一的 content 显示函数 - 返回字符串"""
    if _seen is None:
        _seen = set()

    if _depth > 100:
        return "..."

    obj_id = id(obj)
    if obj_id in _seen:
        # 循环引用, 但不要直接返回 <circular>
        # 而是尝试返回一个有用的表示
        if isinstance(obj, dict):
            return "{...}"  # 表示这是个字典的循环引用
        if isinstance(obj, list):
            return "[...]"
        if isinstance(obj, KeiDict):
            return "{...}"
        if isinstance(obj, KeiList):
            return "[...]"
        return "<circular>"

    _seen.add(obj_id)

    try:
        # ===== 处理特殊单例 =====
        if obj is undefined: return "undefined"
        if obj is null: return "null"
        if obj is true: return "true"
        if obj is false: return "false"
        if obj is omit: return "..."

        # ===== 处理 Kei 对象实例 =====
        if isinstance(obj, KeiInt): return f"{obj.value}"
        if isinstance(obj, KeiFloat): return f"{obj.value}"
        if isinstance(obj, KeiString):
            # 字符串：在容器里加引号，否则不加
            if _in_container:
                value = obj.value
                if '"' in obj.value:
                    if "'" in obj.value:
                        value = value.replace("'", "\\'")

                    return f"'{value}'"
                else:
                    return f'"{value}"'

            return obj.value
        if isinstance(obj, KeiBool): return "true" if obj.value else "false"

        if isinstance(obj, KeiList):
            items = [content(item, _seen, _depth + 1, _in_container=True) for item in obj.items]
            return "[" + ", ".join(items) + "]"

        if isinstance(obj, KeiDict):
            items = []
            for k, v in obj.items.items():
                k_str = content(k, _seen, _depth + 1, _in_container=True)
                v_str = content(v, _seen, _depth + 1, _in_container=True)
                items.append(f"{k_str}: {v_str}")
            return "{" + ", ".join(items) + "}"

        if isinstance(obj, KeiFunction): return f"<function {obj.__name__}>"
        if isinstance(obj, KeiClass): return f"<class {obj.__name__}>"
        if isinstance(obj, KeiInstance): return f"<instance {obj._class.__name__}>"
        if isinstance(obj, KeiNamespace): return f"<namespace {obj.__name__}>"
        if isinstance(obj, (KeiMethod, KeiBoundMethod)): return f"<method {obj.__name__}>"
        if isinstance(obj, KeiRef): return f"{obj}"
        if isinstance(obj, KeiError): return f"{obj.value}"

        # ===== 处理 Kei 类型本身（类对象） =====
        if isinstance(obj, type):
            if obj == KeiBase: return "<class any>"
            if obj == KeiInt: return "<class int>"
            if obj == KeiFloat: return "<class float>"
            if obj == KeiString: return "<class string>"
            if obj == KeiBool: return "<class bool>"
            if obj == KeiList: return "<class list>"
            if obj == KeiDict: return "<class dict>"
            if obj == KeiFunction: return "<class function>"
            if obj == KeiClass: return "<class class>"
            if obj == KeiInstance: return "<class instance>"
            if obj == KeiNamespace: return "<class namespace>"
            if obj == _undefined: return "<class undefined>"
            if obj == _null: return "<class null>"

        # ===== 处理 Python 原生对象 =====
        # 函数
        if callable(obj):
            if hasattr(obj, '__name__'):
                return f"<function {obj.__name__}>"
            return "<function>"

        # 模块
        if isinstance(obj, type(__import__('sys'))):
            name = getattr(obj, '__name__', 'unknown')
            return f"<module {name}>"

        # 类型
        if isinstance(obj, type):
            return f"<type {obj.__name__}>"

        # 列表
        if isinstance(obj, list):
            items = [content(item, _seen, _depth + 1, True) for item in obj]
            return "[" + ", ".join(items) + "]"

        # 字典
        if isinstance(obj, dict):
            items = []
            for k, v in obj.items():
                k_str = content(k, _seen, _depth + 1, True)
                v_str = content(v, _seen, _depth + 1, True)
                items.append(f"{k_str}: {v_str}")
            return "{" + ", ".join(items) + "}"

        # 元组
        if isinstance(obj, tuple):
            items = [content(item, _seen, _depth + 1, True) for item in obj]
            if len(items) == 1:
                return "(" + items[0] + ",)"
            return "(" + ", ".join(items) + ")"

        # 集合
        if isinstance(obj, set):
            items = [content(item, _seen, _depth + 1, True) for item in obj]
            return "{" + ", ".join(items) + "}"

        # 字符串
        if isinstance(obj, str):
            # Python 字符串：在容器里加引号
            if _in_container:
                if "'" in obj:
                    obj = obj.replace("'", "\\'")

                    return f"'{obj}'"
                else:
                    return f'"{obj}"'

            return obj

        # 数字、布尔、None 等
        if obj is None:
            return "null"
        if isinstance(obj, bool):
            return "true" if obj else "false"
        if isinstance(obj, (int, float)):
            return str(obj)

        # 其他 Python 对象
        try:
            repr_str = repr(obj)
            if len(repr_str) > 100:
                repr_str = repr_str[:97] + "..."
            return repr_str
        except:
            return f"<object>"

    finally:
        # 从 seen 集合中移除
        _seen.remove(obj_id)

# ========== 常量 ==========

HASVALUE = [
    KeiInt,
    KeiFloat,
    KeiString,
    KeiBool,
    KeiRef
]

HASITMES = [
    KeiList,
    KeiDict
]

# ========== 导出 ==========

__all__ = [
    'undefined', 'null', 'true', 'false', 'omit',
    'KeiBase', 'KeiInt', 'KeiFloat', 'KeiString',
    'KeiList', 'KeiDict', 'KeiBool',
    'KeiFunction', 'KeiClass', 'KeiNamespace',
    'KeiInstance', 'KeiMethod', 'KeiBoundMethod',
    'content', 'KeiRef',
    '_undefined', '_null',
    'KeiException', 'KeiError', 'Error',
    'HASVALUE', 'HASITMES'
]

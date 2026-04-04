#!/usr/bin/env python

import copy
import math
from typing import Any, Dict, Union, Callable, Optional
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from lib.kei2py import *

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
        if cls is KeiFloat and type(instance) is KeiInt:
            return True
        return type(instance) is cls or issubclass(type(instance), cls)


# ========== Kei 对象基类 ==========

class KeiBase(metaclass=KeiMeta):
    """所有Kei对象的基类"""
    def __init__(self, type_name: str):
        self._type = type_name
        self._methods: Dict[str, Callable] = {}
        self._props: Dict[str, KeiValue] = {}
        self.value: Any = None
        self._class = None

    def _get_method(self, name: str) -> Optional[Callable]:
        """获取方法（优先实例属性，再类方法）"""
        if name in self._props:
            val = self._props[name]
            if callable(val):
                return val
            return None
        if name in self._methods:
            return self._methods[name]
        if self._class is not None:
            return self._class._get_method(name)
        return None

    def _wrap_method(self, method: Callable) -> Callable:
        def bound(*args: Any, **kwargs: Any) -> Any:
            return method(self, *args, **kwargs)
        return bound

    def __getitem__(self, key: Any) -> Any:
        method = self._get_method('__getitem__')
        if method:
            return method(key)
        return self._default_getitem(key)

    def __setitem__(self, key: Any, value: Any) -> None:
        method = self._get_method('__setitem__')
        if method:
            method(key, value)
            return
        self._default_setitem(key, value)

    def __delitem__(self, key: Any) -> None:
        method = self._get_method('__delitem__')
        if method:
            method(key)
            return
        if key in self._props:
            del self._props[key]

    def __len__(self) -> int:
        method = self._get_method('__len__')
        if method:
            return method()
        return len(self._props)

    def __contains__(self, key: Any) -> bool:
        method = self._get_method('__contains__')
        if method:
            return method(key)
        return key in self._props

    def __iter__(self):
        method = self._get_method('__iter__')
        if method:
            return method()
        return iter(self._props.keys())

    def _default_getitem(self, key):
        """默认的 __getitem__ 实现，子类可以覆盖"""
        if isinstance(key, str):
            if key in self._methods:
                method = self._methods[key]
                if hasattr(method, '__self__'):
                    return method
                return self._wrap_method(method)
            if key in self._props:
                return self._props[key]
            return undefined
        return undefined

    def _default_setitem(self, key, value):
        """默认的 __setitem__ 实现，子类可以覆盖"""
        if isinstance(key, str):
            self._props[key] = value
        else:
            raise KeiError("TypeError", f"不支持的类型作为键: {type(key)}")

    # ========== 算术运算符 ==========
    def __add__(self, other):
        method = self._get_method('__add__')
        if method:
            return method(other)
        return undefined

    def __radd__(self, other):
        method = self._get_method('__radd__')
        if method:
            return method(other)
        return self.__add__(other)

    def __sub__(self, other):
        method = self._get_method('__sub__')
        if method:
            return method(other)
        return undefined

    def __rsub__(self, other):
        method = self._get_method('__rsub__')
        if method:
            return method(other)
        return undefined

    def __mul__(self, other):
        method = self._get_method('__mul__')
        if method:
            return method(other)
        return undefined

    def __rmul__(self, other):
        method = self._get_method('__rmul__')
        if method:
            return method(other)
        return self.__mul__(other)

    def __truediv__(self, other):
        method = self._get_method('__truediv__')
        if method:
            return method(other)
        return undefined

    def __rtruediv__(self, other):
        method = self._get_method('__rtruediv__')
        if method:
            return method(other)
        return undefined

    def __floordiv__(self, other):
        method = self._get_method('__floordiv__')
        if method:
            return method(other)
        return undefined

    def __rfloordiv__(self, other):
        method = self._get_method('__rfloordiv__')
        if method:
            return method(other)
        return undefined

    def __mod__(self, other):
        method = self._get_method('__mod__')
        if method:
            return method(other)
        return undefined

    def __rmod__(self, other):
        method = self._get_method('__rmod__')
        if method:
            return method(other)
        return undefined

    def __pow__(self, other):
        method = self._get_method('__pow__')
        if method:
            return method(other)
        return undefined

    def __rpow__(self, other):
        method = self._get_method('__rpow__')
        if method:
            return method(other)
        return undefined

    # ========== 位运算符 ==========
    def __and__(self, other):
        method = self._get_method('__and__')
        if method:
            return method(other)
        return undefined

    def __rand__(self, other):
        method = self._get_method('__rand__')
        if method:
            return method(other)
        return self.__and__(other)

    def __or__(self, other):
        method = self._get_method('__or__')
        if method:
            return method(other)
        return undefined

    def __ror__(self, other):
        method = self._get_method('__ror__')
        if method:
            return method(other)
        return self.__or__(other)

    def __xor__(self, other):
        method = self._get_method('__xor__')
        if method:
            return method(other)
        return undefined

    def __rxor__(self, other):
        method = self._get_method('__rxor__')
        if method:
            return method(other)
        return self.__xor__(other)

    def __lshift__(self, other):
        method = self._get_method('__lshift__')
        if method:
            return method(other)
        return undefined

    def __rlshift__(self, other):
        method = self._get_method('__rlshift__')
        if method:
            return method(other)
        return undefined

    def __rshift__(self, other):
        method = self._get_method('__rshift__')
        if method:
            return method(other)
        return undefined

    def __rrshift__(self, other):
        method = self._get_method('__rrshift__')
        if method:
            return method(other)
        return undefined

    def __invert__(self):
        method = self._get_method('__invert__')
        if method:
            return method()
        return undefined

    # ========== 一元运算符 ==========
    def __neg__(self):
        method = self._get_method('__neg__')
        if method:
            return method()
        return undefined

    def __pos__(self):
        method = self._get_method('__pos__')
        if method:
            return method()
        return undefined

    def __abs__(self):
        method = self._get_method('__abs__')
        if method:
            return method()
        return undefined

    # ========== 比较运算符 ==========
    def __eq__(self, other):
        method = self._get_method('__eq__')
        if method:
            return method(other)
        return true if self is other else false

    def __ne__(self, other):
        method = self._get_method('__ne__')
        if method:
            return method(other)
        return true if self is not other else false

    def __lt__(self, other):
        method = self._get_method('__lt__')
        if method:
            return method(other)
        return undefined

    def __gt__(self, other):
        method = self._get_method('__gt__')
        if method:
            return method(other)
        return undefined

    def __le__(self, other):
        method = self._get_method('__le__')
        if method:
            return method(other)
        return undefined

    def __ge__(self, other):
        method = self._get_method('__ge__')
        if method:
            return method(other)
        return undefined

    # ========== 类型转换 ==========
    def __int__(self):
        method = self._get_method('__int__')
        if method:
            return method()
        raise KeiError("TypeError", f"无法将 {self} 转为 int")

    def __float__(self):
        method = self._get_method('__float__')
        if method:
            return method()
        raise KeiError("TypeError", f"无法将 {self} 转为 float")

    def __str__(self):
        method = self._get_method('__str__')
        if method:
            return method()
        return repr(self)

    def __repr__(self):
        method = self._get_method('__repr__')
        if method:
            return method()
        return f"<{self._type} object>"

    def __bool__(self):
        method = self._get_method('__bool__')
        if method:
            return method()
        return True

    def __call__(self, *args, **kwargs):
        method = self._get_method('__call__')
        if method:
            return method(*args, **kwargs)
        return undefined

    def __dir__(self):
        """默认返回用户可见的属性和方法"""
        # 收集公开方法
        public_methods = [m for m in self._methods.keys()]
        # 收集公开属性
        public_props = [p for p in self._props.keys()]
        return public_methods + public_props

# ========== 错误对象 ==========

class KeiException(Exception, KeiBase):
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
        Exception.__init__(self, f"[{types}] {value}" if value else types)
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

        self._methods = {
            "message": self.message,
            "type": self.type
        }

    def __repr__(self):
        return f"{self.types}"

    def message(self, new=None):
        if new is not None:
            if isinstance(new, HASVALUE):
                self.value = str(new.value)
            else:
                raise KeiError("TypeError", f"无法修改message为{content(type(new))}")
            return self
        else:
            return KeiString(self.value)

    def type(self, new=None):
        if new is not None:
            if isinstance(new, HASVALUE):
                self.types = str(new.value)
            else:
                raise KeiError("TypeError", f"无法修改message为{content(type(new))}")
            return self
        else:
            return KeiString(self.types)


# ========== 数值类型 ==========

class KeiInt(KeiBase):
    def __init__(self, _value):
        super().__init__("int")
        try:
            if isinstance(_value, HASVALUE):
                self.value = int(_value.value)
            else:
                self.value = int(_value)
        except:
            raise KeiError("TypeError", f"无法把 {content(_value)} 转为 int")

        self._methods = {
            "abs": self._abs,
            "pow": self._pow,
            "sqrt": self._sqrt,
            "take": self._take
        }

    def _take(self, digits):
        return KeiFloat(self.value).take(digits)
    def take(self, digits):
        return self._take(digits)

    def __bool__(self):
        return self.value != 0

    def __hash__(self):
        return hash(self.value)

    def _abs(self):
        return KeiInt(abs(self.value))
    def abs(self):
        return self._abs()

    def _pow(self, exponent):
        exp_val = to_float(exponent) if isinstance(exponent, (KeiInt, KeiFloat)) else float(exponent)
        return KeiFloat(self.value ** exp_val)
    def pow(self, exponent):
        return self._pow(exponent)

    def _sqrt(self):
        return KeiFloat(math.sqrt(self.value))
    def sqrt(self):
        return self._sqrt()

    def _default_add(self, other):
        if isinstance(other, KeiInt):
            return KeiInt(self.value + other.value)
        if isinstance(other, KeiFloat):
            return KeiFloat(self.value + to_float(other))
        if isinstance(other, KeiString):
            return KeiString(str(self.value) + other.value)
        if isinstance(other, (int, float)):
            return KeiFloat(self.value + other)
        return undefined

    def __add__(self, other):
        method = self._get_method('__add__')
        if method:
            return method(other)
        return self._default_add(other)

    def __radd__(self, other):
        method = self._get_method('__radd__')
        if method:
            return method(other)
        return self._default_add(other)

    def _default_sub(self, other):
        if isinstance(other, KeiInt):
            return KeiInt(self.value - other.value)
        if isinstance(other, KeiFloat):
            return KeiFloat(self.value - to_float(other))
        if isinstance(other, (int, float)):
            return KeiFloat(self.value - other)
        return undefined

    def __sub__(self, other):
        method = self._get_method('__sub__')
        if method:
            return method(other)
        return self._default_sub(other)

    def __rsub__(self, other):
        method = self._get_method('__rsub__')
        if method:
            return method(other)
        if isinstance(other, (int, float)):
            return KeiFloat(other - self.value)
        return undefined

    def _default_mul(self, other):
        if isinstance(other, KeiInt):
            return KeiInt(self.value * other.value)
        if isinstance(other, KeiFloat):
            return KeiFloat(self.value * to_float(other))
        if isinstance(other, (int, float)):
            return KeiFloat(self.value * other)
        if isinstance(other, KeiString):
            return KeiString(other.value * self.value)
        return undefined

    def __mul__(self, other):
        method = self._get_method('__mul__')
        if method:
            return method(other)
        return self._default_mul(other)

    def __rmul__(self, other):
        method = self._get_method('__rmul__')
        if method:
            return method(other)
        return self._default_mul(other)

    def _default_truediv(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            val = to_float(other)
            if val == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiFloat(self.value / val)
        if isinstance(other, (int, float)):
            if other == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiFloat(self.value / other)
        return undefined

    def __truediv__(self, other):
        method = self._get_method('__truediv__')
        if method:
            return method(other)
        return self._default_truediv(other)

    def __rtruediv__(self, other):
        method = self._get_method('__rtruediv__')
        if method:
            return method(other)
        if isinstance(other, (int, float)):
            if self.value == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiFloat(other / self.value)
        return undefined

    def _default_floordiv(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            val = to_float(other)
            if val == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiInt(self.value // val)
        if isinstance(other, (int, float)):
            if other == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiInt(self.value // other)
        return undefined

    def __floordiv__(self, other):
        method = self._get_method('__floordiv__')
        if method:
            return method(other)
        return self._default_floordiv(other)

    def __rfloordiv__(self, other):
        method = self._get_method('__rfloordiv__')
        if method:
            return method(other)
        if isinstance(other, (int, float)):
            if self.value == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiInt(other // self.value)
        return undefined

    def _default_mod(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            val = to_float(other)
            if val == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiInt(self.value % val)
        if isinstance(other, (int, float)):
            if other == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiInt(self.value % other)
        return undefined

    def __mod__(self, other):
        method = self._get_method('__mod__')
        if method:
            return method(other)
        return self._default_mod(other)

    def __rmod__(self, other):
        method = self._get_method('__rmod__')
        if method:
            return method(other)
        if isinstance(other, (int, float)):
            if self.value == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiInt(other % self.value)
        return undefined

    def _default_pow(self, other):
        if isinstance(other, KeiInt):
            return KeiInt(self.value ** other.value)
        if isinstance(other, KeiFloat):
            return KeiFloat(self.value ** to_float(other))
        if isinstance(other, (int, float)):
            return KeiFloat(self.value ** other)
        return undefined

    def __pow__(self, other):
        method = self._get_method('__pow__')
        if method:
            return method(other)
        return self._default_pow(other)

    def __rpow__(self, other):
        method = self._get_method('__rpow__')
        if method:
            return method(other)
        if isinstance(other, (int, float)):
            return KeiFloat(other ** self.value)
        return undefined

    def _default_and(self, other):
        if isinstance(other, KeiInt):
            return KeiInt(self.value & other.value)
        if isinstance(other, int):
            return KeiInt(self.value & other)
        return undefined

    def __and__(self, other):
        method = self._get_method('__and__')
        if method:
            return method(other)
        return self._default_and(other)

    def __rand__(self, other):
        method = self._get_method('__rand__')
        if method:
            return method(other)
        return self._default_and(other)

    def _default_or(self, other):
        if isinstance(other, KeiInt):
            return KeiInt(self.value | other.value)
        if isinstance(other, int):
            return KeiInt(self.value | other)
        return undefined

    def __or__(self, other):
        method = self._get_method('__or__')
        if method:
            return method(other)
        return self._default_or(other)

    def __ror__(self, other):
        method = self._get_method('__ror__')
        if method:
            return method(other)
        return self._default_or(other)

    def _default_xor(self, other):
        if isinstance(other, KeiInt):
            return KeiInt(self.value ^ other.value)
        if isinstance(other, int):
            return KeiInt(self.value ^ other)
        return undefined

    def __xor__(self, other):
        method = self._get_method('__xor__')
        if method:
            return method(other)
        return self._default_xor(other)

    def __rxor__(self, other):
        method = self._get_method('__rxor__')
        if method:
            return method(other)
        return self._default_xor(other)

    def _default_lshift(self, other):
        if isinstance(other, KeiInt):
            return KeiInt(self.value << other.value)
        if isinstance(other, int):
            return KeiInt(self.value << other)
        return undefined

    def __lshift__(self, other):
        method = self._get_method('__lshift__')
        if method:
            return method(other)
        return self._default_lshift(other)

    def __rlshift__(self, other):
        method = self._get_method('__rlshift__')
        if method:
            return method(other)
        if isinstance(other, int):
            return KeiInt(other << self.value)
        return undefined

    def _default_rshift(self, other):
        if isinstance(other, KeiInt):
            return KeiInt(self.value >> other.value)
        if isinstance(other, int):
            return KeiInt(self.value >> other)
        return undefined

    def __rshift__(self, other):
        method = self._get_method('__rshift__')
        if method:
            return method(other)
        return self._default_rshift(other)

    def __rrshift__(self, other):
        method = self._get_method('__rrshift__')
        if method:
            return method(other)
        if isinstance(other, int):
            return KeiInt(other >> self.value)
        return undefined

    def _default_invert(self):
        return KeiInt(~self.value)

    def __invert__(self):
        method = self._get_method('__invert__')
        if method:
            return method()
        return self._default_invert()

    def _default_eq(self, other):
        if isinstance(other, KeiInt):
            return true if self.value == other.value else false
        if isinstance(other, KeiFloat):
            return true if self.value == to_float(other) else false
        if isinstance(other, (int, float)):
            return true if self.value == other else false
        return false

    def __eq__(self, other):
        method = self._get_method('__eq__')
        if method:
            return method(other)
        return self._default_eq(other)

    def _default_ne(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return true if self.value != to_float(other) else false
        if isinstance(other, (int, float)):
            return true if self.value != other else false
        return true

    def __ne__(self, other):
        method = self._get_method('__ne__')
        if method:
            return method(other)
        return self._default_ne(other)

    def _default_lt(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return true if self.value < to_float(other) else false
        if isinstance(other, (int, float)):
            return true if self.value < other else false
        return false

    def __lt__(self, other):
        method = self._get_method('__lt__')
        if method:
            return method(other)
        return self._default_lt(other)

    def _default_gt(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return true if self.value > to_float(other) else false
        if isinstance(other, (int, float)):
            return true if self.value > other else false
        return false

    def __gt__(self, other):
        method = self._get_method('__gt__')
        if method:
            return method(other)
        return self._default_gt(other)

    def _default_le(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return true if self.value <= to_float(other) else false
        if isinstance(other, (int, float)):
            return true if self.value <= other else false
        return false

    def __le__(self, other):
        method = self._get_method('__le__')
        if method:
            return method(other)
        return self._default_le(other)

    def _default_ge(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return true if self.value >= to_float(other) else false
        if isinstance(other, (int, float)):
            return true if self.value >= other else false
        return false

    def __ge__(self, other):
        method = self._get_method('__ge__')
        if method:
            return method(other)
        return self._default_ge(other)

    def __float__(self):
        return KeiFloat(self.value)

    def __repr__(self):
        method = self._get_method('__repr__')
        if method:
            return method()
        return f"{self.value}"


class KeiFloat(KeiBase):
    def __init__(self, _value):
        super().__init__("float")
        try:
            if isinstance(_value, KeiInt):
                self.value = Decimal(_value.value)
            elif isinstance(_value, KeiFloat):
                self.value = Decimal(str(_value.value))
            elif isinstance(_value, (int, float)):
                self.value = Decimal(str(_value))
            elif isinstance(_value, str):
                self.value = Decimal(_value)
            elif isinstance(_value, Decimal):
                self.value = _value
            else:
                self.value = Decimal(str(_value))
        except:
            raise KeiError("TypeError", f"无法把 {content(_value)} 转为 float")

        self._methods = {
            "abs": self._abs,
            "round": self._round,
            "floor": self._floor,
            "ceil": self._ceil,
            "take": self._take,
        }

    def __float__(self):
        return float(self.value)

    def __bool__(self):
        return self.value != 0

    def __hash__(self):
        return hash(self.value)

    def _abs(self):
        return KeiFloat(abs(self.value))
    def abs(self):
        return self._abs()

    def _round(self):
        return KeiFloat(self.value.quantize(Decimal('1.'), rounding=ROUND_HALF_EVEN))
    def round(self):
        return self._round()

    def _floor(self):
        from decimal import ROUND_FLOOR
        return KeiInt(int(self.value.to_integral(rounding=ROUND_FLOOR)))
    def floor(self):
        return self._floor()

    def _ceil(self):
        from decimal import ROUND_CEILING
        return KeiInt(int(self.value.to_integral(rounding=ROUND_CEILING)))
    def ceil(self):
        return self._ceil()

    def _take(self, digits):
        if isinstance(digits, KeiInt):
            d = digits.value
        else:
            d = int(digits)
        quant = Decimal('1.' + '0' * d)
        try:
            return KeiFloat(self.value.quantize(quant, rounding=ROUND_HALF_EVEN))
        except InvalidOperation:
            raise KeiError("ArithmeticError", "浮点数精度错误: 精度不足")
    def take(self, digits):
        return self._take(digits)

    def places(self):
        exp = self.value.as_tuple().exponent
        return abs(exp if exp < 0 else 0)

    def _default_add(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return KeiFloat(self.value + Decimal(str(to_float(other))))
        if isinstance(other, (int, float)):
            return KeiFloat(self.value + Decimal(str(other)))
        if isinstance(other, KeiString):
            return KeiString(str(self.value) + other.value)
        return undefined

    def __add__(self, other):
        method = self._get_method('__add__')
        if method:
            return method(other)
        return self._default_add(other)

    def __radd__(self, other):
        method = self._get_method('__radd__')
        if method:
            return method(other)
        return self._default_add(other)

    def _default_sub(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return KeiFloat(self.value - Decimal(str(to_float(other))))
        if isinstance(other, (int, float)):
            return KeiFloat(self.value - Decimal(str(other)))
        return undefined

    def __sub__(self, other):
        method = self._get_method('__sub__')
        if method:
            return method(other)
        return self._default_sub(other)

    def __rsub__(self, other):
        method = self._get_method('__rsub__')
        if method:
            return method(other)
        if isinstance(other, (int, float)):
            return KeiFloat(Decimal(str(other)) - self.value)
        return undefined

    def _default_mul(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return KeiFloat(self.value * Decimal(str(to_float(other))))
        if isinstance(other, (int, float)):
            return KeiFloat(self.value * Decimal(str(other)))
        if isinstance(other, KeiString):
            return KeiString(other.value * float(self.value))
        return undefined

    def __mul__(self, other):
        method = self._get_method('__mul__')
        if method:
            return method(other)
        return self._default_mul(other)

    def __rmul__(self, other):
        method = self._get_method('__rmul__')
        if method:
            return method(other)
        return self._default_mul(other)

    def _default_truediv(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            val = Decimal(str(to_float(other)))
            if val == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiFloat(self.value / val)
        if isinstance(other, (int, float)):
            val = Decimal(str(other))
            if val == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiFloat(self.value / val)
        return undefined

    def __truediv__(self, other):
        method = self._get_method('__truediv__')
        if method:
            return method(other)
        return self._default_truediv(other)

    def __rtruediv__(self, other):
        method = self._get_method('__rtruediv__')
        if method:
            return method(other)
        if isinstance(other, (int, float)):
            if self.value == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiFloat(Decimal(str(other)) / self.value)
        return undefined

    def _default_floordiv(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            val = Decimal(str(to_float(other)))
            if val == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiInt(self.value // val)
        if isinstance(other, (int, float)):
            val = Decimal(str(other))
            if val == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiInt(self.value // val)
        return undefined

    def __floordiv__(self, other):
        method = self._get_method('__floordiv__')
        if method:
            return method(other)
        return self._default_floordiv(other)

    def __rfloordiv__(self, other):
        method = self._get_method('__rfloordiv__')
        if method:
            return method(other)
        if isinstance(other, (int, float)):
            if self.value == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiInt(Decimal(str(other)) // self.value)
        return undefined

    def _default_mod(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            val = Decimal(str(to_float(other)))
            if val == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiFloat(self.value % val)
        if isinstance(other, (int, float)):
            val = Decimal(str(other))
            if val == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiFloat(self.value % val)
        return undefined

    def __mod__(self, other):
        method = self._get_method('__mod__')
        if method:
            return method(other)
        return self._default_mod(other)

    def __rmod__(self, other):
        method = self._get_method('__rmod__')
        if method:
            return method(other)
        if isinstance(other, (int, float)):
            if self.value == 0:
                raise KeiError("ZeroDivisionError", "除数不能为零")
            return KeiFloat(Decimal(str(other)) % self.value)
        return undefined

    def _default_pow(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return KeiFloat(self.value ** Decimal(str(to_float(other))))
        if isinstance(other, (int, float)):
            return KeiFloat(self.value ** Decimal(str(other)))
        return undefined

    def __pow__(self, other):
        method = self._get_method('__pow__')
        if method:
            return method(other)
        return self._default_pow(other)

    def __rpow__(self, other):
        method = self._get_method('__rpow__')
        if method:
            return method(other)
        if isinstance(other, (int, float)):
            return KeiFloat(Decimal(str(other)) ** self.value)
        return undefined

    def _default_eq(self, other):
        if isinstance(other, KeiFloat):
            return true if self.value == other.value else false
        if isinstance(other, KeiInt):
            return true if self.value == Decimal(other.value) else false
        if isinstance(other, (int, float)):
            return true if float(self.value) == other else false
        return false

    def __eq__(self, other):
        method = self._get_method('__eq__')
        if method:
            return method(other)
        return self._default_eq(other)

    def _default_ne(self, other):
        if isinstance(other, KeiFloat):
            return true if self.value != other.value else false
        if isinstance(other, KeiInt):
            return true if self.value != Decimal(other.value) else false
        if isinstance(other, (int, float)):
            return true if float(self.value) != other else false
        return true

    def __ne__(self, other):
        method = self._get_method('__ne__')
        if method:
            return method(other)
        return self._default_ne(other)

    def _default_lt(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return true if self.value < Decimal(str(to_float(other))) else false
        if isinstance(other, (int, float)):
            return true if float(self.value) < other else false
        return false

    def __lt__(self, other):
        method = self._get_method('__lt__')
        if method:
            return method(other)
        return self._default_lt(other)

    def _default_gt(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return true if self.value > Decimal(str(to_float(other))) else false
        if isinstance(other, (int, float)):
            return true if float(self.value) > other else false
        return false

    def __gt__(self, other):
        method = self._get_method('__gt__')
        if method:
            return method(other)
        return self._default_gt(other)

    def _default_le(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return true if self.value <= Decimal(str(to_float(other))) else false
        if isinstance(other, (int, float)):
            return true if float(self.value) <= other else false
        return false

    def __le__(self, other):
        method = self._get_method('__le__')
        if method:
            return method(other)
        return self._default_le(other)

    def _default_ge(self, other):
        if isinstance(other, (KeiInt, KeiFloat)):
            return true if self.value >= Decimal(str(to_float(other))) else false
        if isinstance(other, (int, float)):
            return true if float(self.value) >= other else false
        return false

    def __ge__(self, other):
        method = self._get_method('__ge__')
        if method:
            return method(other)
        return self._default_ge(other)

    def __repr__(self):
        method = self._get_method('__repr__')
        if method:
            return method()
        if self.value == self.value.to_integral():
            return str(int(self.value))
        s = str(self.value)
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
        return s


# ========== 布尔类型 ==========

class KeiBool(KeiBase):
    _instance_true = None
    _instance_false = None

    def __new__(cls, value):
        try:
            if value:
                if cls._instance_true is None:
                    cls._instance_true = super().__new__(cls)
                return cls._instance_true
            else:
                if cls._instance_false is None:
                    cls._instance_false = super().__new__(cls)
                return cls._instance_false
        except:
            raise KeiError("TypeError", f"无法把 {content(value)} 转为 bool")

    def __init__(self, value):
        if not hasattr(self, '_initialized'):
            super().__init__("bool")
            self.value = value
            self._initialized = True

            self._methods = {
                "not": self._not,
                "and": self._and,
                "or": self._or,
                "xor": self._xor,
            }

    def _not(self):
        return KeiBool(not self.value)
    def not_(self):
        return self._not()

    def _and(self, other):
        if isinstance(other, KeiBool):
            return KeiBool(self.value and other.value)
        return KeiBool(self.value and bool(other))
    def and_(self, other):
        return self._and(other)

    def _or(self, other):
        if isinstance(other, KeiBool):
            return KeiBool(self.value or other.value)
        return KeiBool(self.value or bool(other))
    def or_(self, other):
        return self._or(other)

    def _xor(self, other):
        if isinstance(other, KeiBool):
            return KeiBool(self.value ^ other.value)
        return KeiBool(self.value ^ bool(other))
    def xor(self, other):
        return self._xor(other)

    def __bool__(self):
        return self.value

    def __and__(self, other):
        method = self._get_method('__and__')
        if method:
            return method(other)
        if isinstance(other, KeiBool):
            return KeiBool(self.value and other.value)
        return KeiBool(self.value and bool(other))

    def __rand__(self, other):
        return self.__and__(other)

    def __or__(self, other):
        method = self._get_method('__or__')
        if method:
            return method(other)
        if isinstance(other, KeiBool):
            return KeiBool(self.value or other.value)
        return KeiBool(self.value or bool(other))

    def __ror__(self, other):
        return self.__or__(other)

    def __xor__(self, other):
        method = self._get_method('__xor__')
        if method:
            return method(other)
        if isinstance(other, KeiBool):
            return KeiBool(self.value ^ other.value)
        return KeiBool(self.value ^ bool(other))

    def __rxor__(self, other):
        return self.__xor__(other)

    def __eq__(self, other):
        method = self._get_method('__eq__')
        if method:
            return method(other)
        if isinstance(other, KeiBool):
            return true if self.value == other.value else false
        return false

    def __repr__(self):
        method = self._get_method('__repr__')
        if method:
            return method()
        return "true" if self.value else "false"


true = KeiBool(True)
false = KeiBool(False)


# ========== 字符串类型 ==========

class KeiString(KeiBase):
    def __init__(self, _value):
        super().__init__("string")
        try:
            if isinstance(_value, HASVALUE):
                self.value = str(_value.value)
            else:
                self.value = str(_value)
        except:
            raise KeiError("TypeError", f"无法把 {content(_value)} 转为 string")

        self._methods = {
            "upper": self._upper,
            "lower": self._lower,
            "split": self._split,
            "join": self._join,
            "replace": self._replace,
            "strip": self._strip,
            "startswith": self._startswith,
            "endswith": self._endswith,
            "contains": self._contains,
            "length": self._length,
            "char_at": self._char_at,
            "index_of": self._index_of,
            "center": self._center,
            "append": self._append,
            "push": self._push
        }

    def _append(self, *values):
        for value in values:
            if isinstance(value, HASVALUE):
                self.value = self.value + str(value.value)
            else:
                self.value = self.value + str(value)
        return KeiString(self.value)
    def append(self, *values):
        return self._append(*values)

    def _push(self, *values):
        for value in values:
            if isinstance(value, HASVALUE):
                self.value = self.value + str(value.value)
            else:
                self.value = self.value + str(value)
        return KeiString(self.value)
    def push(self, *values):
        return self._push(*values)

    def __bool__(self):
        return len(self.value) > 0

    def __hash__(self):
        return hash(self.value)

    def _upper(self):
        return KeiString(self.value.upper())
    def upper(self):
        return self._upper()

    def _lower(self):
        return KeiString(self.value.lower())
    def lower(self):
        return self._lower()

    def _center(self, width, fill=' '):
        if isinstance(width, KeiInt):
            w = width.value
        else:
            w = int(width)

        if isinstance(fill, KeiString):
            fill_char = fill.value[0] if fill.value else ' '
        else:
            fill_char = str(fill)[0] if str(fill) else ' '

        text_len = len(self.value)
        if w <= text_len:
            return self

        left = (w - text_len) // 2
        right = w - text_len - left
        result = fill_char * left + self.value + fill_char * right
        return KeiString(result)
    def center(self, width, fill=' '):
        return self._center(width, fill)

    def _split(self, separator=None):
        if separator is None or separator is undefined:
            parts = self.value.split()
        else:
            if isinstance(separator, KeiString):
                sep = separator.value
            else:
                sep = str(separator)
            parts = self.value.split(sep)
        return KeiList([KeiString(p) for p in parts])
    def split(self, separator=None):
        return self._split(separator)

    def _join(self, iterable):
        if isinstance(iterable, KeiList):
            items = [str(item) for item in iterable.items]
        else:
            items = [str(iterable)]
        return KeiString(self.value.join(items))
    def join(self, iterable):
        return self._join(iterable)

    def _replace(self, old, new):
        if isinstance(old, KeiString):
            old_str = old.value
        else:
            old_str = str(old)
        if isinstance(new, KeiString):
            new_str = new.value
        else:
            new_str = str(new)
        return KeiString(self.value.replace(old_str, new_str))
    def replace(self, old, new):
        return self._replace(old, new)

    def _strip(self):
        return KeiString(self.value.strip())
    def strip(self):
        return self._strip()

    def _startswith(self, prefix):
        if isinstance(prefix, KeiString):
            p = prefix.value
        else:
            p = str(prefix)
        return true if self.value.startswith(p) else false
    def startswith(self, prefix):
        return self._startswith(prefix)

    def _endswith(self, suffix):
        if isinstance(suffix, KeiString):
            s = suffix.value
        else:
            s = str(suffix)
        return true if self.value.endswith(s) else false
    def endswith(self, suffix):
        return self._endswith(suffix)

    def _contains(self, substr):
        if isinstance(substr, KeiString):
            s = substr.value
        else:
            s = str(substr)
        return true if s in self.value else false
    def contains(self, substr):
        return self._contains(substr)

    def _length(self):
        return KeiInt(len(self.value))
    def length(self):
        return self._length()

    def _char_at(self, index):
        if isinstance(index, KeiInt):
            i = index.value
        else:
            i = int(index)
        if 0 <= i < len(self.value):
            return KeiString(self.value[i])
        return undefined
    def char_at(self, index):
        return self._char_at(index)

    def _index_of(self, substr):
        if isinstance(substr, KeiString):
            s = substr.value
        else:
            s = str(substr)
        try:
            return KeiInt(self.value.index(s))
        except ValueError:
            return KeiInt(-1)
    def index_of(self, substr):
        return self._index_of(substr)

    def _default_getitem(self, key):
        """覆盖基类的 _default_getitem，支持字符串索引"""
        if isinstance(key, str):
            if key in self._methods:
                method = self._methods[key]
                if hasattr(method, '__self__'):
                    return method
                return self._wrap_method(method)
            if key in self._props:
                return self._props[key]
            return undefined

        if isinstance(key, slice):
            start = key.start
            stop = key.stop
            step = key.step if key.step is not None else 1

            if isinstance(start, KeiInt):
                start = start.value
            if isinstance(stop, KeiInt):
                stop = stop.value
            if isinstance(step, KeiInt):
                step = step.value

            length = len(self.value)
            if start is None:
                start = 0 if step > 0 else length - 1
            elif start < 0:
                start = length + start

            if stop is None:
                stop = length if step > 0 else -1
            elif stop < 0:
                stop = length + stop

            result = []
            i = start
            while (step > 0 and i < stop) or (step < 0 and i > stop):
                if 0 <= i < length:
                    result.append(self.value[i])
                i += step

            return KeiString(''.join(result))

        if isinstance(key, KeiInt):
            idx = key.value
        elif isinstance(key, int):
            idx = key
        else:
            return undefined

        if idx < 0:
            idx = len(self.value) + idx

        if 0 <= idx < len(self.value):
            return KeiString(self.value[idx])
        return undefined

    def _default_setitem(self, key, value):
        """覆盖基类的 _default_setitem，支持字符串属性赋值"""
        if isinstance(key, str):
            if key in self._methods:
                raise KeiError("TypeError", f"不能修改方法 {key}")
            self._props[key] = value
            return

        if isinstance(key, KeiInt):
            idx = key.value
        elif isinstance(key, int):
            idx = key
        else:
            raise KeiError("TypeError", f"不支持的类型作为索引: {type(key)}")

        if idx < 0:
            idx = len(self.value) + idx

        if 0 <= idx < len(self.value):
            if isinstance(value, KeiString):
                new_str = value.value
            else:
                new_str = str(value)
            self.value = self.value[:idx] + new_str + self.value[idx+1:]

    def __getitem__(self, key):
        method = self._get_method('__getitem__')
        if method:
            return method(key)
        return self._default_getitem(key)

    def __setitem__(self, key, value):
        method = self._get_method('__setitem__')
        if method:
            method(key, value)
            return
        self._default_setitem(key, value)

    def __add__(self, other):
        method = self._get_method('__add__')
        if method:
            return method(other)
        if isinstance(other, HASVALUE):
            return KeiString(self.value + str(other.value))
        if isinstance(other, (int, float, str)):
            return KeiString(self.value + str(other))
        return undefined

    def __radd__(self, other):
        method = self._get_method('__radd__')
        if method:
            return method(other)
        if isinstance(other, (int, float, str)):
            return KeiString(str(other) + self.value)
        return undefined

    def __mul__(self, other):
        method = self._get_method('__mul__')
        if method:
            return method(other)
        if isinstance(other, (KeiInt, int)):
            n = other.value if isinstance(other, KeiInt) else other
            return KeiString(self.value * n)
        return undefined

    def __rmul__(self, other):
        return self.__mul__(other)

    def __eq__(self, other):
        method = self._get_method('__eq__')
        if method:
            return method(other)
        if isinstance(other, KeiString):
            return true if self.value == other.value else false
        return false

    def __ne__(self, other):
        method = self._get_method('__ne__')
        if method:
            return method(other)
        if isinstance(other, KeiString):
            return true if self.value != other.value else false
        return true

    def __lt__(self, other):
        method = self._get_method('__lt__')
        if method:
            return method(other)
        if isinstance(other, KeiString):
            return true if self.value < other.value else false
        return false

    def __gt__(self, other):
        method = self._get_method('__gt__')
        if method:
            return method(other)
        if isinstance(other, KeiString):
            return true if self.value > other.value else false
        return false

    def __le__(self, other):
        method = self._get_method('__le__')
        if method:
            return method(other)
        if isinstance(other, KeiString):
            return true if self.value <= other.value else false
        return false

    def __ge__(self, other):
        method = self._get_method('__ge__')
        if method:
            return method(other)
        if isinstance(other, KeiString):
            return true if self.value >= other.value else false
        return false

    def __repr__(self):
        method = self._get_method('__repr__')
        if method:
            return method()
        return f'{self.value}'


# ========== 列表类型 ==========

class KeiList(KeiBase):
    def __init__(self, _items=None):
        super().__init__("list")
        self.items = _items if _items is not None else []

        self._methods = {
            "push": self._push,
            "pop": self._pop,
            "get": self._get,
            "set": self._set,
            "length": self._length,
            "map": self._map,
            "filter": self._filter,
            "reduce": self._reduce,
            "foreach": self._foreach,
            "slice": self._slice,
            "concat": self._concat,
            "join": self._join,
            "reverse": self._reverse,
            "sort": self._sort,
            "index_of": self._index_of,
            "includes": self._includes,
            "uniq": self._uniq,
            "append": self._append,
        }

    def __bool__(self):
        return len(self.items) > 0

    def __len__(self):
        method = self._get_method('__len__')
        if method:
            return method()
        return len(self.items)

    def _append(self, *values):
        for v in values:
            self.items.append(v)
        return self
    def append(self, *values):
        return self._append(*values)

    def _uniq(self):
        result = []
        if self.items:
            for i in self.items:
                if i not in result:
                    result.append(i)
        return KeiList(result)
    def uniq(self):
        return self._uniq()

    def _push(self, *values):
        for v in values:
            self.items.append(v)
        return self
    def push(self, *values):
        return self._push(*values)

    def _pop(self):
        if not self.items:
            return undefined
        return self.items.pop()
    def pop(self):
        return self._pop()

    def _get(self, index):
        if isinstance(index, KeiInt):
            i = index.value
        else:
            i = int(index)
        if 0 <= i < len(self.items):
            return self.items[i]
        return undefined
    def get(self, index):
        return self._get(index)

    def _set(self, index, _value):
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
    def set(self, index, _value):
        return self._set(index, _value)

    def _length(self):
        return KeiInt(len(self.items))
    def length(self):
        return self._length()

    def _map(self, func):
        result = []
        for item in self.items:
            if callable(func):
                new_val = func(item)
            else:
                new_val = func(item)
            result.append(new_val)
        return KeiList(result)
    def map(self, func):
        return self._map(func)

    def _filter(self, func):
        result = []
        for item in self.items:
            if callable(func):
                if func(item):
                    result.append(item)
            else:
                if func(item):
                    result.append(item)
        return KeiList(result)
    def filter(self, func):
        return self._filter(func)

    def _reduce(self, func, initial=undefined):
        if not self.items:
            return initial

        if initial is undefined:
            acc = self.items[0]
            start = 1
        else:
            acc = initial
            start = 0

        for i in range(start, len(self.items)):
            result = func(acc, self.items[i])
            if isinstance(result, KeiList) and len(result.items) == 1:
                acc = result.items[0]
            else:
                acc = result
        return acc
    def reduce(self, func, initial=undefined):
        return self._reduce(func, initial)

    def _foreach(self, func):
        for item in self.items:
            func(item)
        return undefined
    def foreach(self, func):
        return self._foreach(func)

    def _slice(self, start=None, end=None):
        s = start.value if isinstance(start, KeiInt) else (start or 0)
        e = end.value if isinstance(end, KeiInt) else (end if end is not None else len(self.items))
        return KeiList(self.items[s:e])
    def slice(self, start=None, end=None):
        return self._slice(start, end)

    def _concat(self, other):
        if isinstance(other, KeiList):
            return KeiList(self.items + other.items)
        return KeiList(self.items + [other])
    def concat(self, other):
        return self._concat(other)

    def _join(self, separator=""):
        if isinstance(separator, KeiString):
            sep = separator.value
        else:
            sep = str(separator)
        return KeiString(sep.join(str(item) for item in self.items))
    def join(self, separator=""):
        return self._join(separator)

    def _reverse(self):
        self.items.reverse()
        return self
    def reverse(self):
        return self._reverse()

    def _sort(self, key=None, reverse=false):
        rev = reverse.value if isinstance(reverse, KeiBase) else bool(reverse)
        if key and key is not undefined:
            self.items.sort(key=lambda x: key(x).value if isinstance(key(x), KeiBase) else key(x), reverse=rev)
        else:
            self.items.sort(reverse=rev)
        return self
    def sort(self, key=None, reverse=false):
        return self._sort(key, reverse)

    def _index_of(self, _value):
        try:
            return KeiInt(self.items.index(_value))
        except ValueError:
            return KeiInt(-1)
    def index_of(self, _value):
        return self._index_of(_value)

    def _includes(self, _value):
        return true if _value in self.items else false
    def includes(self, _value):
        return self._includes(_value)

    def _default_getitem(self, key):
        """覆盖基类的 _default_getitem，支持字符串属性访问"""
        if isinstance(key, str):
            if key in self._methods:
                method = self._methods[key]
                if hasattr(method, '__self__'):
                    return method
                return self._wrap_method(method)
            if key in self._props:
                return self._props[key]
            return undefined

        if isinstance(key, slice):
            start = key.start
            stop = key.stop
            step = key.step if key.step is not None else 1

            if isinstance(start, KeiInt):
                start = start.value
            if isinstance(stop, KeiInt):
                stop = stop.value
            if isinstance(step, KeiInt):
                step = step.value

            length = len(self.items)
            if start is None:
                start = 0 if step > 0 else length - 1
            elif start < 0:
                start = length + start

            if stop is None:
                stop = length if step > 0 else -1
            elif stop < 0:
                stop = length + stop

            result = []
            i = start
            while (step > 0 and i < stop) or (step < 0 and i > stop):
                if 0 <= i < length:
                    result.append(self.items[i])
                i += step

            return KeiList(result)

        if isinstance(key, KeiInt):
            idx = key.value
        elif isinstance(key, int):
            idx = key
        else:
            return undefined

        if idx < 0:
            idx = len(self.items) + idx

        if 0 <= idx < len(self.items):
            return self.items[idx]
        return undefined

    def _default_setitem(self, key, value):
        """覆盖基类的 _default_setitem，支持字符串属性赋值"""
        if isinstance(key, str):
            if key in self._methods:
                raise KeiError("TypeError", f"不能修改方法 {key}")
            self._props[key] = value
            return

        if isinstance(key, KeiInt):
            idx = key.value
        elif isinstance(key, int):
            idx = key
        else:
            raise KeiError("TypeError", f"列表索引必须是整数, 得到 {type(key)}")

        if idx < 0:
            idx = len(self.items) + idx

        if 0 <= idx < len(self.items):
            self.items[idx] = value
        elif idx == len(self.items):
            self.items.append(value)
        else:
            raise KeiError("IndexError", f"列表索引超出范围: {idx}")

    def __getitem__(self, key):
        method = self._get_method('__getitem__')
        if method:
            return method(key)
        return self._default_getitem(key)

    def __setitem__(self, key, value):
        method = self._get_method('__setitem__')
        if method:
            method(key, value)
            return
        self._default_setitem(key, value)

    def __add__(self, other):
        method = self._get_method('__add__')
        if method:
            return method(other)
        if isinstance(other, KeiList):
            return KeiList(self.items + other.items)
        return KeiList(self.items + [other])

    def __radd__(self, other):
        method = self._get_method('__radd__')
        if method:
            return method(other)
        return KeiList([other] + self.items)

    def __mul__(self, other):
        method = self._get_method('__mul__')
        if method:
            return method(other)
        if isinstance(other, (KeiInt, int)):
            n = other.value if isinstance(other, KeiInt) else other
            return KeiList(self.items * n)
        return undefined

    def __rmul__(self, other):
        return self.__mul__(other)

    def __sub__(self, other):
        method = self._get_method('__sub__')
        if method:
            return method(other)
        if isinstance(other, KeiList):
            result = [x for x in self.items if x not in other.items]
            return KeiList(result)
        return KeiList([x for x in self.items if x != other])

    def __rsub__(self, other):
        method = self._get_method('__rsub__')
        if method:
            return method(other)
        return KeiList([x for x in [other] if x not in self.items])

    def __or__(self, other):
        method = self._get_method('__or__')
        if method:
            return method(other)
        if isinstance(other, KeiList):
            result = []
            for item in self.items + other.items:
                result.append(item)
            return KeiList(result)
        return undefined

    def __ror__(self, other):
        return self.__or__(other)

    def __eq__(self, other):
        method = self._get_method('__eq__')
        if method:
            return method(other)
        if isinstance(other, KeiList):
            if len(self.items) != len(other.items):
                return false
            for i, j in zip(self.items, other.items):
                if i != j:
                    return false
            return true
        return false

    def __ne__(self, other):
        method = self._get_method('__ne__')
        if method:
            return method(other)
        if isinstance(other, KeiList):
            return true if not self.__eq__(other) else false
        return true

    def __lt__(self, other):
        method = self._get_method('__lt__')
        if method:
            return method(other)
        if isinstance(other, KeiList):
            return true if len(self.items) < len(other.items) else false
        return false

    def __gt__(self, other):
        method = self._get_method('__gt__')
        if method:
            return method(other)
        if isinstance(other, KeiList):
            return true if len(self.items) > len(other.items) else false
        return false

    def __le__(self, other):
        method = self._get_method('__le__')
        if method:
            return method(other)
        if isinstance(other, KeiList):
            return true if len(self.items) <= len(other.items) else false
        return false

    def __ge__(self, other):
        method = self._get_method('__ge__')
        if method:
            return method(other)
        if isinstance(other, KeiList):
            return true if len(self.items) >= len(other.items) else false
        return false

    def __repr__(self):
        method = self._get_method('__repr__')
        if method:
            return method()
        items = ", ".join(repr(i) for i in self.items)
        return f"[{items}]"

    def __dir__(self):
        return list(self._methods.keys()) + ['items']

# ========== 字典类型 ==========

class KeiDict(KeiBase):
    def __init__(self, pairs=None):
        super().__init__("dict")
        self.items = pairs if pairs is not None else {}

        self._methods = {
            "keys": self._keys,
            "values": self._values,
            "get": self._get,
            "set": self._set,
            "has": self._has,
            "delete": self._delete,
            "clear": self._clear,
            "length": self._length,
            "update": self._update,
            "map": self._map,
            "items": self._items,
        }

    def _items(self):
        return KeiList([KeiList([KeiString(k), v]) for k, v in self.items.items()])
    def items(self):
        return self._items()

    def __len__(self):
        method = self._get_method('__len__')
        if method:
            return method()
        return len(self.items)

    def _keys(self):
        return KeiList([KeiString(k) for k in self.items.keys()])
    def keys(self):
        return self._keys()

    def _values(self):
        return KeiList(list(self.items.values()))
    def values(self):
        return self._values()

    def _get(self, key, default=undefined):
        if isinstance(key, KeiString):
            k = key.value
        elif isinstance(key, (KeiInt, KeiFloat, KeiBool)):
            k = to_python(key)
        else:
            k = key
        return self.items.get(k, default)
    def get(self, key, default=undefined):
        return self._get(key, default)

    def _set(self, key, _value):
        if isinstance(key, KeiString):
            k = key.value
        elif isinstance(key, (KeiInt, KeiFloat, KeiBool)):
            k = to_python(key)
        else:
            k = key
        self.items[k] = _value
        return _value
    def set(self, key, _value):
        return self._set(key, _value)

    def _has(self, key):
        if isinstance(key, KeiString):
            k = key.value
        elif isinstance(key, (KeiInt, KeiFloat, KeiBool)):
            k = to_python(key)
        else:
            k = key
        return true if k in self.items else false
    def has(self, key):
        return self._has(key)

    def _delete(self, key):
        if isinstance(key, KeiString):
            k = key.value
        elif isinstance(key, (KeiInt, KeiFloat, KeiBool)):
            k = to_python(key)
        else:
            k = key
        if k in self.items:
            del self.items[k]
            return true
        return false
    def delete(self, key):
        return self._delete(key)

    def _clear(self):
        self.items.clear()
        return null
    def clear(self):
        return self._clear()

    def _length(self):
        return KeiInt(len(self.items))
    def length(self):
        return self._length()

    def _update(self, other):
        if isinstance(other, KeiDict):
            self.items.update(other.items)
        elif isinstance(other, dict):
            self.items.update(other)
        return self
    def update(self, other):
        return self._update(other)

    def _map(self, func):
        for k in self.items:
            self.items[k] = func(self.items[k])
        return self
    def map(self, func):
        return self._map(func)

    def _default_getitem(self, key):
        """覆盖基类的 _default_getitem"""
        if isinstance(key, str):
            if key in self._methods:
                method = self._methods[key]
                if hasattr(method, '__self__'):
                    return method
                return self._wrap_method(method)
            if key in self._props:
                return self._props[key]
            return undefined

        if isinstance(key, KeiString):
            k = key.value
        elif isinstance(key, (KeiInt, KeiFloat, KeiBool)):
            k = to_python(key)
        else:
            k = key

        if k in self.items:
            return self.items[k]
        return undefined

    def _default_setitem(self, key, value):
        """覆盖基类的 _default_setitem"""
        if isinstance(key, str):
            if key in self._methods:
                raise KeiError("TypeError", f"不能修改方法 {key}")
            self._props[key] = value
            return

        if isinstance(key, KeiString):
            k = key.value
        elif isinstance(key, (KeiInt, KeiFloat, KeiBool)):
            k = to_python(key)
        else:
            k = key
        self.items[k] = value

    def __getitem__(self, key):
        method = self._get_method('__getitem__')
        if method:
            return method(key)
        return self._default_getitem(key)

    def __setitem__(self, key, value):
        method = self._get_method('__setitem__')
        if method:
            method(key, value)
            return
        self._default_setitem(key, value)

    def __contains__(self, key):
        method = self._get_method('__contains__')
        if method:
            return method(key)
        if isinstance(key, KeiString):
            k = key.value
        elif isinstance(key, (KeiInt, KeiFloat, KeiBool)):
            k = to_python(key)
        else:
            k = key
        return k in self.items

    def __add__(self, other):
        method = self._get_method('__add__')
        if method:
            return method(other)
        if isinstance(other, KeiDict):
            new_dict = self.items.copy()
            new_dict.update(other.items)
            return KeiDict(new_dict)
        return undefined

    def __radd__(self, other):
        return self.__add__(other)

    def __or__(self, other):
        method = self._get_method('__or__')
        if method:
            return method(other)
        if isinstance(other, KeiDict):
            new_dict = self.items.copy()
            new_dict.update(other.items)
            return KeiDict(new_dict)
        return undefined

    def __ror__(self, other):
        return self.__or__(other)

    def __eq__(self, other):
        method = self._get_method('__eq__')
        if method:
            return method(other)
        if isinstance(other, KeiDict):
            if len(self.items) != len(other.items):
                return false
            for k, v in self.items.items():
                if k not in other.items or other.items[k] != v:
                    return false
            return true
        return false

    def __ne__(self, other):
        method = self._get_method('__ne__')
        if method:
            return method(other)
        if isinstance(other, KeiDict):
            return true if not self.__eq__(other) else false
        return true

    def __bool__(self):
        return len(self.items) > 0

    def __repr__(self):
        method = self._get_method('__repr__')
        if method:
            return method()
        items = ", ".join(f"{k}: {repr(v)}" for k, v in self.items.items())
        return f"{{{items}}}"

    def __dir__(self):
        return list(self._methods.keys()) + ['items']

# ========== 函数类型 ==========

class KeiFunction(KeiBase):
    def __init__(self, func_obj: dict, env: dict):
        super().__init__("function")
        self.func_obj = func_obj
        self.env = env
        self.__name__ = func_obj['name'] if func_obj['name'] else "lambda"
        self.__env__ = func_obj.get('closure', env)

    def __call__(self, *args, linecode=None, name=None, **kwargs):
        from kei import runtoken, get_from_env, __kei__

        pushed = False
        if linecode is not None:
            if name is None:
                name = self.__name__
            __kei__.stack.append((name, linecode))
            pushed = True

        params = self.func_obj['params']
        typeassert = self.func_obj.get('typeassert', None)

        star_pos = -1
        star_param_name = None
        starstar_param_name = None

        for i, p in enumerate(params):
            if p.startswith('**'):
                starstar_param_name = p[2:]
                star_pos = i
            elif p.startswith('*') and star_pos == -1:
                star_param_name = p[1:]
                star_pos = i
                break

        if star_pos == -1:
            before_star = params
            after_star = []
        else:
            before_star = params[:star_pos]
            after_star = params[star_pos + 1:]

        all_args = list(args)
        remaining_kwargs = kwargs.copy()

        new_env = {'__parent__': self.__env__, '__caller__': self.__name__}

        for i, param_name in enumerate(before_star):
            if i < len(all_args):
                new_env[param_name] = all_args[i]
            elif param_name in remaining_kwargs:
                new_env[param_name] = remaining_kwargs.pop(param_name)
            elif param_name in self.func_obj.get('defaults', {}):
                default_val_node = self.func_obj['defaults'][param_name]
                default_val, _ = runtoken(default_val_node, self.__env__)
                new_env[param_name] = default_val
            else:
                new_env[param_name] = undefined

        if star_param_name:
            star_args = all_args[len(before_star):]
            new_env[star_param_name] = KeiList(star_args)

        for param_name in after_star:
            if param_name.startswith('**'):
                starstar_param_name = param_name[2:]
                new_env[starstar_param_name] = KeiDict(remaining_kwargs)
                remaining_kwargs = {}
            elif param_name in remaining_kwargs:
                new_env[param_name] = remaining_kwargs.pop(param_name)
            elif param_name in self.func_obj.get('defaults', {}):
                default_val_node = self.func_obj['defaults'][param_name]
                default_val, _ = runtoken(default_val_node, self.__env__)
                new_env[param_name] = default_val
            else:
                new_env[param_name] = undefined

        if remaining_kwargs and not starstar_param_name:
            raise KeiError("SyntaxError", f"函数 {self.__name__} 收到未预料的关键字参数: {list(remaining_kwargs.keys())}")

        type_hints = self.func_obj.get('typehints', {})

        for param_name, type_node in type_hints.items():
            if param_name in new_env:
                val = new_env[param_name]
                # 计算期望的类型
                expected_type, _ = runtoken(type_node, self.__env__)

                # 检查类型
                if not isinstance(val, expected_type):
                    # 抛出错误，指向调用点
                    raise KeiError("TypeError",
                        f"参数 '{param_name}' 期望 {content(expected_type)}, 得到 {content(type(val))}")

        try:
            result = null
            for stmt in self.func_obj['body']:
                val, is_return = runtoken(stmt, new_env)
                if is_return:
                    result = val
                    break

            from kei import runtoken

            if typeassert is not None:
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

            return result
        except:
            raise
        finally:
            if pushed:
                __kei__.stack.pop()

    def __repr__(self) -> str:
        return f"<function {self.__name__}>"

    def __dir__(self):
        return ['__name__']


# ========== 类类型 ==========

class KeiClass(KeiBase):
    def __init__(self, class_obj: dict, env: dict):
        super().__init__("class")
        self.class_obj = class_obj
        self.env = env
        self.value = class_obj
        self.__name__ = class_obj['name']
        self._class_attrs = class_obj.get('attrs', {})
        self._methods_map = class_obj.get('methods_map', {})

    def _get_method(self, name: str) -> Optional[Callable]:
        """获取类方法"""
        if name in self._class_attrs:
            return self._class_attrs[name]
        if name in self._methods_map:
            method_obj = self._methods_map[name]
            if method_obj.get('is_property'):
                return KeiProperty(method_obj)
            return KeiMethod(method_obj, self)
        return None

    def __call__(self, *args: Any, **kwargs: Any) -> 'KeiInstance':
        instance = KeiInstance(self)
        instance._class = self

        init_method = self._methods_map.get('__init__')
        if init_method:
            try:
                new_env = copy.deepcopy(init_method['closure'])
            except:
                try:
                    new_env = copy.copy(init_method['closure'])
                except:
                    new_env = init_method['closure']

            new_env['self'] = instance
            params = init_method['params'][1:]

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

            from kei import runtoken
            for stmt in init_method['body']:
                val, is_return = runtoken(stmt, new_env)
                if is_return and val is not None:
                    break

        return instance

    def __getitem__(self, key):
        method = self._get_method('__getitem__')
        if method:
            return method(key)
        if key in self._class_attrs:
            return self._class_attrs[key]
        if key in self._methods_map:
            method_obj = self._methods_map[key]
            if method_obj.get('is_property'):
                return KeiProperty(method_obj)
            return KeiMethod(method_obj, self)
        return undefined

    def __setitem__(self, key, value):
        method = self._get_method('__setitem__')
        if method:
            method(key, value)
            return
        self._class_attrs[key] = value

    def __repr__(self) -> str:
        return f"<class {self.__name__}>"

    def __dir__(self):
        return list(self._class_attrs.keys()) + list(self._methods_map.keys())


class KeiProperty(KeiBase):
    def __init__(self, method_obj: dict):
        super().__init__("property")
        self.method_obj = method_obj
        self.__name__ = method_obj['name']

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        bound = KeiBoundMethod(self.method_obj, obj)
        return bound()

    def __repr__(self):
        return f"<property {self.__name__}>"


# ========== 实例类型 ==========

class KeiInstance(KeiBase):
    def __init__(self, klass: KeiClass):
        super().__init__("instance")
        self._class = klass
        self._attrs = {}

    def _get_method(self, name: str) -> Optional[Callable]:
        """获取方法：先查实例属性，再查类方法"""
        if name in self._attrs:
            return self._attrs[name]
        if self._class is not None:
            return self._class._get_method(name)
        return None

    def __getitem__(self, key):
        method = self._get_method('__getitem__')
        if method:
            return method(key)
        if key in self._attrs:
            return self._attrs[key]
        if self._class is not None:
            return self._class[key]
        return undefined

    def __setitem__(self, key, _value):
        method = self._get_method('__setitem__')
        if method:
            method(key, _value)
            return
        self._attrs[key] = _value

    def __delitem__(self, key):
        method = self._get_method('__delitem__')
        if method:
            method(key)
            return
        if key in self._attrs:
            del self._attrs[key]

    def __repr__(self):
        return f"<instance {self._class.__name__}>"

    def __dir__(self):
        return list(self._attrs.keys())


# ========== 方法类型 ==========

class KeiMethod(KeiBase):
    def __init__(self, method_obj: dict, klass: KeiClass):
        super().__init__("method")
        self.method_obj = method_obj
        self.klass = klass
        self.__name__ = method_obj['name']
        self.is_static = False
        self.is_property = method_obj.get('is_property', False)
        if 'decorators' in method_obj:
            for dec in method_obj['decorators']:
                if dec['value'] == 'static':
                    self.is_static = True
                    break

    def bind(self, instance: KeiInstance) -> 'KeiBoundMethod':
        return KeiBoundMethod(self.method_obj, instance)

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if self.is_property:
            bound = KeiBoundMethod(self.method_obj, obj)
            return bound()
        return self.bind(obj)

    def __call__(self, *args, **kwargs):
        if self.is_static:
            bound = KeiBoundMethod(self.method_obj, None)
            return bound(*args, **kwargs)
        else:
            if not args or not isinstance(args[0], KeiInstance):
                raise KeiError("NameError", f"未绑定方法 {self.__name__} 需要 self 参数")
            instance = args[0]
            bound = self.bind(instance)
            return bound(*args[1:], **kwargs)

    def __repr__(self):
        return f"<method {self.__name__}>"


class KeiBoundMethod(KeiBase):
    def __init__(self, method_obj: dict, instance: KeiInstance | None):
        super().__init__("bound_method")
        self.method_obj = method_obj
        self.instance = instance
        self.__name__ = method_obj['name']

    def __call__(self, *args, **kwargs):
        new_env = {}
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

        if self.instance is not None:
            new_env['self'] = self.instance

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
        if key in self.env:
            return self.env[key]
        return undefined

    def __getitem__(self, key):
        result = self.env.get(key, undefined)
        return result

    def __setitem__(self, key, value):
        self.env[key] = value

    def __repr__(self):
        return f"<namespace {self.__name__}>"

    def __dir__(self):
        return list(self.env.keys()) + ['__name__']

    def __add__(self, other):
        """namespace + namespace = 合并，后者覆盖前者"""
        if isinstance(other, KeiNamespace):
            # 合并两个命名空间的环境
            new_env = self.env.copy()
            new_env.update(other.env)
            # 生成新名字
            new_name = f"{self.name}+{other.name}"
            return KeiNamespace(new_name, new_env)
        return undefined

# ========== 工厂函数 ==========

def content(obj, _seen=None, _depth=0, _in_container=False):
    if _seen is None:
        _seen = set()

    if _depth > 100:
        return "..."

    obj_id = id(obj)
    if obj_id in _seen:
        if isinstance(obj, dict):
            return "{...}"
        if isinstance(obj, list):
            return "[...]"
        if isinstance(obj, KeiDict):
            return "{...}"
        if isinstance(obj, KeiList):
            return "[...]"
        return "<circular>"

    _seen.add(obj_id)

    try:
        if obj is undefined: return "undefined"
        if obj is null: return "null"
        if obj is true: return "true"
        if obj is false: return "false"
        if obj is omit: return "..."

        if isinstance(obj, KeiInt): return f"{obj.value}"
        if isinstance(obj, KeiFloat): return f"{obj.value}"
        if isinstance(obj, KeiString):
            if _in_container:
                value = repr(obj.value)
                return f"{value}".replace('\\\\', '\\')
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
        if isinstance(obj, KeiError): return f"{obj.value}"

        if isinstance(obj, type):
            if obj == KeiBase: return "<class any>"
            elif obj == KeiInt: return "<class int>"
            elif obj == KeiFloat: return "<class float>"
            elif obj == KeiString: return "<class string>"
            elif obj == KeiBool: return "<class bool>"
            elif obj == KeiList: return "<class list>"
            elif obj == KeiDict: return "<class dict>"
            elif obj == KeiFunction: return "<class function>"
            elif obj == KeiClass: return "<class class>"
            elif obj == KeiInstance: return "<class instance>"
            elif obj == KeiNamespace: return "<class namespace>"
            elif obj == _undefined: return "<class undefined>"
            elif obj == _null: return "<class null>"
            else: return f"<class {obj.__name__}>" if hasattr(obj, '__name__') else "<class>"

        if isinstance(obj, type(__import__('sys'))):
            name = getattr(obj, '__name__', 'unknown')
            return f"<module {name}>"

        if isinstance(obj, type):
            return f"<type {obj.__name__}>"

        if isinstance(obj, list):
            items = [content(item, _seen, _depth + 1, True) for item in obj]
            return "[" + ", ".join(items) + "]"

        if isinstance(obj, dict):
            items = []
            for k, v in obj.items():
                k_str = content(k, _seen, _depth + 1, True)
                v_str = content(v, _seen, _depth + 1, True)
                items.append(f"{k_str}: {v_str}")
            return "{" + ", ".join(items) + "}"

        if isinstance(obj, tuple):
            items = [content(item, _seen, _depth + 1, True) for item in obj]
            if len(items) == 1:
                return "(" + items[0] + ",)"
            return "(" + ", ".join(items) + ")"

        if isinstance(obj, set):
            items = [content(item, _seen, _depth + 1, True) for item in obj]
            return "{" + ", ".join(items) + "}"

        if isinstance(obj, str):
            if _in_container:
                value = repr(obj)
                return f"{value}".replace('\\\\', '\\')
            return obj

        if obj is None:
            return "null"
        if isinstance(obj, bool):
            return "true" if obj else "false"
        if isinstance(obj, (int, float)):
            return str(obj)

        if callable(obj):
            if hasattr(obj, '__name__'):
                return f"<function {obj.__name__}>"
            return "<function>"

        if hasattr(obj, '__name__'):
            return f"<object {obj.__name__}>"
        else:
            return "<object>"

    finally:
        _seen.remove(obj_id)

# ========== 常量 ==========

HASVALUE = (
    KeiInt,
    KeiFloat,
    KeiString,
    KeiBool
)

HASITMES = (
    KeiList,
    KeiDict
)

# ========== 导出 ==========

__all__ = [
    'undefined', 'null', 'true', 'false', 'omit',
    'KeiBase', 'KeiInt', 'KeiFloat', 'KeiString',
    'KeiList', 'KeiDict', 'KeiBool',
    'KeiFunction', 'KeiClass', 'KeiNamespace',
    'KeiInstance', 'KeiMethod', 'KeiBoundMethod',
    'content',
    '_undefined', '_null',
    'KeiException', 'KeiError',
    'HASVALUE', 'HASITMES'
]
from lib.object import *

def topy(value):
    """KeiLang → Python 递归转换"""
    if value is None:
        return None
    if value is undefined:
        return None
    if value is null:
        return None

    # 基础类型
    if isinstance(value, KeiInt):
        return value.value
    if isinstance(value, KeiFloat):
        return value.value
    if isinstance(value, KeiString):
        return value.value
    if isinstance(value, KeiBool):
        return value.value

    # 列表
    if isinstance(value, KeiList):
        return [topy(item) for item in value.items]

    # 字典
    if isinstance(value, KeiDict):
        return {topy(k): topy(v) for k, v in value.items.items()}

    # 命名空间
    if isinstance(value, KeiNamespace):
        return {k: topy(v) for k, v in value.env.items()}

    # 函数/方法（返回函数本身，调用时再转换参数）
    if callable(value):
        return value

    # 其他 Kei 对象
    if hasattr(value, '_props'):
        return {k: topy(v) for k, v in value._props.items()}

    # 默认返回原值
    return value

def tokei(value):
    """Python → KeiLang 递归转换"""
    if value is None:
        return null

    # 基础类型
    if isinstance(value, bool):
        return true if value else false
    if isinstance(value, int):
        return KeiInt(value)
    if isinstance(value, float):
        return KeiFloat(value)
    if isinstance(value, str):
        return KeiString(value)

    # 列表
    if isinstance(value, (list, tuple)):
        return KeiList([tokei(item) for item in value])

    # 字典
    if isinstance(value, dict):
        return KeiDict({tokei(k): tokei(v) for k, v in value.items()})

    # 类（Python 类）→ 直接返回，不包装
    if isinstance(value, type):
        return value

    # 函数/方法（包装成可调用的 Kei 对象）
    if callable(value):
        return module(value)

    # 模块
    if hasattr(value, '__name__') and hasattr(value, '__dict__'):
        return module(value)

    # 其他类型，尝试转字符串
    try:
        return KeiString(str(value))
    except:
        return value

def pyimport(module_name):
    """导入 Python 模块"""
    if isinstance(module_name, KeiString):
        module_name = module_name.value

    # 用 Python 的 __import__
    try:
        m = __import__(module_name)
    except ImportError:
        raise KeiError("ImportError", f"没有模块{module_name}")

    # 包装成 Kei 对象
    return module(m)

class module(KeiBase):
    """包装 Python 模块，自动转换 KeiLang ↔ Python 类型"""

    def __init__(self, py_module):
        super().__init__("module")
        self._py_module = py_module
        self.__name__ = getattr(py_module, '__name__', 'unknown')

        # 缓存包装后的方法
        self._methods = {}

    def __getattr__(self, name):
        """获取模块属性，自动包装函数"""
        attr = getattr(self._py_module, name)
        return tokei(attr)

    def __getitem__(self, key):
        """支持 dict 风格访问"""
        return self.__getattr__(key)

    def __dir__(self):
        """返回模块的所有公开属性"""
        return [d for d in dir(self._py_module) if not d.startswith('_')]

    def __repr__(self):
        return f"<python_module {self.__name__}>"

    def __call__(self, *args, **kwargs):
        """如果 module 实例被调用，尝试调用它包装的 Python 对象"""
        # 转换 Kei 参数为 Python 原生类型
        py_args = [topy(arg) for arg in args]
        py_kwargs = {k: topy(v) for k, v in kwargs.items()}

        # 如果 self._py_module 是类，就实例化
        if isinstance(self._py_module, type):
            instance = self._py_module(*py_args, **py_kwargs)
            return tokei(instance)
        # 如果是函数，就调用
        if callable(self._py_module):
            result = self._py_module(*py_args, **py_kwargs)
            return tokei(result)
        raise KeiError("TypeError", f"{self._py_module} 不可调用")

def iskei(value):
    """检测值是否是 KeiLang 对象"""
    # KeiLang 的基本类型
    if isinstance(value, (KeiInt, KeiFloat, KeiString, KeiBool, KeiList, KeiDict, KeiFunction, KeiClass, KeiInstance, KeiNamespace, KeiError)):
        return true
    # KeiLang 的特殊值
    if value in (undefined, null, true, false, omit):
        return true
    # 其他 KeiBase 子类
    if isinstance(value, KeiBase):
        return true
    return false

def ispy(value):
    """检测值是否是 Python 原生对象"""
    # Python 原生类型
    if isinstance(value, (int, float, str, bool, list, dict, tuple, set)):
        return true
    # Python 特殊值
    if value is None:
        return true
    # 不是 KeiLang 对象
    return not iskei(value)

__all__ = ['tokei', 'topy', 'pyimport', 'module', 'iskei', 'ispy']

#!/usr/bin/env python

from lib.object import *
from lib.kei2py import *

env = {}

class kei:
    s = staticmethod

    @s
    def timer(f):
        def wrapper(*args, **kwargs):
            import time
            start = time.time()
            result = f(*args, **kwargs)
            end = time.time()
            # 返回普通 Python 元组
            return (result, f"{end - start:.3f}")
        return wrapper

    @s
    def setenv(envs):
        global env
        env = envs

    @s
    def getenv():
        global env
        return env

    @s
    def _assert(x, y=None):
        kei.check(x, KeiBool, name='assert')
        x = x.value

        if not x:
            if y is not None:
                kei.print(y)
            raise KeiError('AssertError', f'断言失败')

    @s
    def factorial(n):
        n = to_int(n)

        if n <= 1:
            return 1
        return n * kei.factorial(n - 1)

    class open(KeiBase):
        """KeiLang open 函数类"""
        def __init__(self, file, mode='r', encoding='utf-8'):
            super().__init__("file")

            # 转换参数
            if isinstance(file, KeiString):
                file = file.value
            if isinstance(mode, KeiString):
                mode = mode.value
            if isinstance(encoding, KeiString):
                encoding = encoding.value

            self._file = open(file, mode, encoding=encoding)

            self._methods = {
                "read": self.read,
                "readline": self.readline,
                "readlines": self.readlines,
                "write": self.write,
                "writelines": self.writelines,
                "close": self.close,
                "flush": self.flush,
                "seek": self.seek,
                "tell": self.tell,
                "remove": self.remove,
            }

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.close()
            return False

        def remove(self):
            import os
            os.remove(self._file.name)

        def read(self, size=-1):
            if isinstance(size, KeiInt):
                size = size.value
            return KeiString(self._file.read(size))

        def readline(self, size=-1):
            if isinstance(size, KeiInt):
                size = size.value
            return KeiString(self._file.readline(size))

        def readlines(self, hint=-1):
            if isinstance(hint, KeiInt):
                hint = hint.value
            lines = self._file.readlines(hint)
            return KeiList([KeiString(line) for line in lines])

        def write(self, text):
            if isinstance(text, KeiString):
                text = text.value
            return KeiInt(self._file.write(text))

        def writelines(self, lines):
            if isinstance(lines, KeiList):
                lines = [line.value if isinstance(line, KeiString) else str(line) for line in lines.items]
            self._file.writelines(lines)
            return null

        def close(self):
            self._file.close()
            return null

        def flush(self):
            self._file.flush()
            return null

        def seek(self, offset, whence=0):
            if isinstance(offset, KeiInt):
                offset = offset.value
            if isinstance(whence, KeiInt):
                whence = whence.value
            return KeiInt(self._file.seek(offset, whence))

        def tell(self):
            return KeiInt(self._file.tell())

    @s
    def system(command, verbose=True):
        kei.check(command, KeiString, name="system")
        command = to_str(command)
        import subprocess
        process = subprocess.Popen(command,
                                   shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   text=True)

        assert process.stdout is not None

        while True:
            value = process.poll()
            if value is None:
                line = process.stdout.readline()
                if not line:
                    continue
                if verbose:
                    print(line, end='', flush=True)
            else:
                return value

    @s
    def cnlen(text):
        kei.check(text, KeiString, str, name='cnlen')
        text = kei.topy(text)
        """计算字符串的显示长度
        规则：
        - 中文字符：2
        - 中文标点：2
        - 英文标点：1
        - 数字：1
        - 英文字母：1
        - 空格：1
        - 其他Unicode字符根据实际情况判断
        """
        length = 0
        for char in str(text):
            code = ord(char)

            # 中文标点符号（全角）
            chinese_punctuation = {
                '，', '。', '！', '？', '；', '：', '“', '”', '‘', '’',
                '（', '）', '【', '】', '《', '》', '—', '…', '·', '、',
                '～', '　', '〃', '〈', '〉', '「', '」', '『', '』', '〖',
                '〗', '〔', '〕', '｛', '｝', '﹙', '﹚', '﹛', '﹜', '﹝',
                '﹞', '（', '）', '［', '］', '｡', '｢', '｣', '､', '･',
                '＾', '￣', '＿', '＆', '＊', '＠', '＃', '％', '＋', '－',
                '＝', '＜', '＞', '｜', '～', '＼', '＄', '￡', '￥'
            }

            # 英文标点符号（半角）
            english_punctuation = {
                ',', '.', '!', '?', ';', ':', '"', "'", '(', ')', '[', ']',
                '{', '}', '<', '>', '-', '=', '+', '*', '/', '\\', '|', '`',
                '~', '@', '#', '$', '%', '^', '&', '_'
            }

            # 中文字符范围（包括扩展汉字）
            if (0x4E00 <= code <= 0x9FFF or    # 常用汉字
                0x3400 <= code <= 0x4DBF or    # 扩展A
                0x20000 <= code <= 0x2A6DF or   # 扩展B
                0x2A700 <= code <= 0x2B73F or   # 扩展C
                0x2B740 <= code <= 0x2B81F or   # 扩展D
                0x2B820 <= code <= 0x2CEAF or   # 扩展E
                0x2CEB0 <= code <= 0x2EBEF or   # 扩展F
                0x30000 <= code <= 0x3134F or   # 扩展G
                0xF900 <= code <= 0xFAFF or     # 兼容汉字
                0x2F800 <= code <= 0x2FA1F):    # 兼容扩展
                length += 2

            # 中文标点符号（全角）
            elif char in chinese_punctuation:
                length += 2

            # 全角英文字母、数字（FF00-FFEF）
            elif 0xFF00 <= code <= 0xFFEF:
                # 全角字母和数字也按2计算
                length += 2

            # 英文标点符号（半角）
            elif char in english_punctuation:
                length += 1

            # 数字
            elif '0' <= char <= '9':
                length += 1

            # 英文字母
            elif ('a' <= char <= 'z') or ('A' <= char <= 'Z'):
                length += 1

            # 空格
            elif char == ' ':
                length += 1

            # 其他字符（如emoji等）
            else:
                # Emoji 范围（粗略判断）
                if 0x1F300 <= code <= 0x1F9FF:  # Emoji 范围
                    length += 2  # Emoji 一般占2个字符宽度
                elif code > 0xFFFF:  # 其他Unicode字符
                    length += 2
                else:
                    length += 1

        return length

    @s
    def exit(code=KeiInt(0)):
        kei.check(code, KeiString, KeiInt, KeiFloat, KeiBool, name='exit')
        code = code.value
        import sys
        sys.exit(code)

    @s
    def print(*text, end=KeiString('\n'), sep=KeiString(' '), just=KeiInt(0), color=KeiString("null"), flush=KeiBool(True)):
        kei.check(end, KeiString, name='print')
        kei.check(sep, KeiString, name='print')
        kei.check(just, KeiInt, name='print')
        kei.check(color, KeiString, name='print')
        kei.check(flush, KeiBool, name='print')

        assert isinstance(end, KeiString)
        assert isinstance(sep, KeiString)
        assert isinstance(just, KeiInt)
        assert isinstance(color, KeiString)
        assert isinstance(flush, KeiBool)

        end     = end.value
        sep     = sep.value
        just    = just.value
        try:
            spaces = abs(just) - kei.cnlen(sep.join(content(t) for t in text))
        except:
            spaces = 0
        color   = color.value
        flush   = flush.value

        rainbow = False

        colors  = {
            'null': '0',
            'black': '30',
            'red': '31',
            'green': '32',
            'yellow': '33',
            'blue': '34',
            'purple': '35',
            'cyan': '36',
            'white': '37',
            'rainbow': 'rainbow',

            'black+': '90',
            'red+': '91',
            'green+': '92',
            'yellow+': '93',
            'blue+': '94',
            'purple+': '95',
            'cyan+': '96',
            'white+': '97',
            'rainbow+': 'rainbow+',
        }

        if colors[color] not in {"rainbow", "rainbow+"}:
            print(f"\033[{colors[color] if color in colors else '0'}m", end='')
        else:
            rainbow = "+" if colors[color] == "rainbow+" else "-"

        text = sep.join(content(t) for t in text)

        # 定义渐变颜色范围 (0-255 RGB)
        # 这里用 ANSI 256色
        def rgb_to_ansi(r, g, b):
            # 简单的 RGB 到 256色转换
            return 16 + (36 * (r // 51)) + (6 * (g // 51)) + (b // 51)

        # 生成彩虹渐变 (红->黄->绿->青->蓝->紫)
        gradient = []
        for i in range(len(text)):
            # 计算颜色位置 (0-5 循环，但平滑过渡)
            pos = (i / max(1, len(text) - 1)) * 5
            segment = int(pos)
            frac = pos - segment

            # 相邻两个颜色的混合
            colors_rgb = ([
                (255, 0, 0),      # 红
                (255, 255, 0),    # 黄
                (0, 255, 0),      # 绿
                (0, 255, 255),    # 青
                (0, 0, 255),      # 蓝
                (255, 0, 255),    # 紫
            ] if rainbow != "+" else [
                (255, 128, 128),  # 亮红
                (255, 255, 128),  # 亮黄
                (128, 255, 128),  # 亮绿
                (128, 255, 255),  # 亮青
                (128, 128, 255),  # 亮蓝
                (255, 128, 255),  # 亮紫
            ])

            if segment >= 5:
                r, g, b = colors_rgb[5]
            else:
                r1, g1, b1 = colors_rgb[segment]
                r2, g2, b2 = colors_rgb[segment + 1]

                r = int(r1 * (1 - frac) + r2 * frac)
                g = int(g1 * (1 - frac) + g2 * frac)
                b = int(b1 * (1 - frac) + b2 * frac)

            gradient.append(rgb_to_ansi(r, g, b))

        # 打印渐变文本
        if just > 0:
            print(" " * spaces, end='', flush=flush)

        for i, ch in enumerate(text):
            if rainbow:
                print(f"\033[38;5;{gradient[i]}m{ch}\033[0m", end='', flush=flush)
            else:
                print(f"{ch}", end='', flush=flush)

        if just < 0:
            print(" " * spaces, end='', flush=flush)

        print("\033[0m", end='', flush=flush)

        print(end=end, flush=flush)

        return KeiString(text)

    @s
    def println(*text):
        print(' '.join(content(t) for t in text), end='\n')
        return KeiString(' '.join(content(t) for t in text))

    @s
    def sleep(second: KeiFloat):
        import time
        time.sleep(to_float(second))
        return KeiFloat(second)

    @s
    def gettime():
        import time
        return KeiFloat(time.time()) if isinstance(time.time(), float) else KeiInt(time.time())

    @s
    def clear():
        import subprocess
        import os

        subprocess.run('clear' if os.name == 'posix' else 'cls', shell=True)

    @s
    def range(*args):
        # 转换参数
        py_args = []
        for a in args:
            kei.check(a, KeiFloat, name='range')
            py_args.append(a.value)

        # 调用 Python 内置 range
        if len(py_args) == 1:
            return KeiList(range(py_args[0]))
        elif len(py_args) == 2:
            return KeiList(range(py_args[0], py_args[1]))
        elif len(py_args) == 3:
            return KeiList(range(py_args[0], py_args[1], py_args[2]))
        else:
            raise Exception("range 需要 1~3 个参数")

    @s
    def type(obj):
        """返回对象的类型（类本身）"""
        # 处理 Kei 对象实例 → 返回对应的类
        if isinstance(obj, KeiInt): return KeiInt
        if isinstance(obj, KeiFloat): return KeiFloat
        if isinstance(obj, KeiString): return KeiString
        if isinstance(obj, KeiBool): return KeiBool
        if isinstance(obj, KeiList): return KeiList
        if isinstance(obj, KeiDict): return KeiDict
        if isinstance(obj, KeiFunction): return KeiFunction
        if isinstance(obj, KeiClass): return KeiClass
        if isinstance(obj, KeiInstance): return KeiInstance
        if isinstance(obj, KeiNamespace): return KeiNamespace

        # 处理类型本身 → 返回自身（已经是类了）
        if obj in {KeiInt, KeiFloat, KeiString, KeiBool,
                   KeiList, KeiDict, KeiFunction, KeiClass,
                   KeiInstance, KeiNamespace}:
            return obj

        # 处理单例 → 返回对应的类
        if obj is undefined: return type(undefined)  # _undefined 类
        if obj is null: return type(null)            # _null 类
        if obj is true: return type(true)            # _true 类
        if obj is false: return type(false)          # _false 类
        if obj is omit: return type(omit)            # _omit 类

        return undefined

    @s
    def random(x=KeiInt(0), y=KeiInt(9)):
        kei.check(x, KeiInt, name='random')
        kei.check(y, KeiInt, name='random')

        x = to_int(x)
        y = to_int(y)

        return KeiInt(__import__('random').randint(x, y))

    @s
    def len(string):
        if type(string) is KeiString:
            return KeiInt(len(string.value))
        elif type(string) is KeiList:
            return KeiInt(len(string.items))
        else:
            raise KeiError("TypeError", "len 需要字符串/列表/字典")

    @s
    def check(text, *obj, name=''):
        for t in obj:
            if isinstance(text, t):
                return

        if len(obj) == 1:
            expected = obj[0].__name__
        else:
            expected = ' 或 '.join(t.__name__ for t in obj)

        actual = type(text).__name__
        raise KeiError("TypeError", f"{(name + ' ') if name else ''}需要 {expected}，得到 {actual}")

    @s
    def input(ps):
        kei.check(ps, KeiString, KeiFloat, name='input')
        kei.print(ps, end=KeiString(''))
        return KeiString(input())

    @s
    def abs(x):
        kei.check(x, KeiFloat, name='abs')  # 检查类型

        if x.value < 0:
            if isinstance(x, KeiInt):
                return KeiInt(-x.value)
            else:
                return KeiFloat(-x.value)
        else:
            return x  # 直接返回原值

    @s
    def max(*args, key=None):
        """返回最大值，支持多个参数或列表，支持 key 函数"""
        if len(args) == 0:
            raise Exception("max 需要至少一个参数")

        # 处理 key 参数
        if key is not None:
            # key 是 Kei 函数，需要转换
            if isinstance(key, KeiFunction):
                key_func = lambda x: kei.topy(key(x))
            else:
                key_func = key
        else:
            key_func = lambda x: x

        # 如果只有一个参数且是列表
        if len(args) == 1 and isinstance(args[0], KeiList):
            items = args[0].items
            if not items:
                raise Exception("max 的列表不能为空")

            # 用 key 找最大值
            max_item = items[0]
            max_key = key_func(max_item)
            for item in items[1:]:
                k = key_func(item)
                if k > max_key:
                    max_item = item
                    max_key = k
            return max_item

        # 多个参数
        max_item = args[0]
        max_key = key_func(max_item)
        for arg in args[1:]:
            k = key_func(arg)
            if k > max_key:
                max_item = arg
                max_key = k
        return max_item

    @s
    def breakpoint():
        from kei import __kei__

        if __kei__.step is None:
            __kei__.step = "breakpoint"

        return __kei__.step

    @s
    def step(value=None):
        from kei import __kei__

        if value is not None:
            if isinstance(value, KeiBool):
                value = value.value
            elif type(value) is null:
                value = None
            else:
                raise KeiError("TypeError", "step需要bool或null")

            __kei__.step = value

        return __kei__.step

    @s
    def min(*args):
        """返回最小值，支持多个参数或列表"""
        if len(args) == 0:
            raise Exception("min 需要至少一个参数")

        # 如果只有一个参数且是列表，取列表最小值
        if len(args) == 1 and isinstance(args[0], KeiList):
            items = args[0].items
            if not items:
                raise Exception("min 的列表不能为空")

            # 找到最小值
            min_item = items[0]
            for item in items[1:]:
                if item < min_item:  # Kei 对象支持 < 比较
                    min_item = item
            return min_item

        # 多个参数直接比较
        min_item = args[0]
        for arg in args[1:]:
            if arg < min_item:
                min_item = arg
        return min_item

    @s
    def zip(*iterables):
        # 如果没有参数，返回空列表
        if not iterables:
            return KeiList([])

        # 将所有输入转换为可迭代的 Python 列表
        py_iterables = []
        for it in iterables:
            if isinstance(it, KeiList):
                py_iterables.append(it.items)  # KeiList 的 _items 是 Python 列表
            elif isinstance(it, KeiString):
                py_iterables.append(list(it.value))  # 字符串转字符列表
            elif isinstance(it, (list, tuple)):
                py_iterables.append(list(it))  # Python 列表/元组
            else:
                # 尝试转换为列表
                try:
                    py_iterables.append(list(it))
                except:
                    raise Exception(f"zip 不支持 {type(it)} 类型")

        # 找到最短的长度
        min_length = min(len(lst) for lst in py_iterables)

        # 打包
        result = []
        for i in range(min_length):
            # 从每个列表中取第 i 个元素
            items = []
            for lst in py_iterables:
                items.append(lst[i])
            # 转换成 KeiList（作为元组使用）
            result.append(KeiList(items))

        return KeiList(result)

    @s
    def loop():
        while True: pass

    @s
    def sort(obj):
        """递归排序所有类型，但类型必须全部相同"""

        # 基本类型直接返回
        if isinstance(obj, (KeiInt, KeiFloat, KeiString, KeiBool)):
            return obj

        # 列表：递归排序每个元素
        elif isinstance(obj, KeiList):
            if not obj.items:
                return KeiList([])

            # 检查所有元素类型是否一致
            first_type = type(obj.items[0])
            for item in obj.items[1:]:
                if type(item) is not first_type:
                    raise KeiError("TypeError", f"列表元素类型不一致: 有 {first_type.__name__} 和 {type(item).__name__}")

            # 递归排序每个元素
            sorted_items = [kei.sort(item) for item in obj.items]

            # 对列表本身排序（根据元素值）
            sorted_items.sort(key=lambda x: x.value if hasattr(x, 'value') else x)

            return KeiList(sorted_items)

        # 字典：递归排序键值对
        elif isinstance(obj, KeiDict):
            if not obj.items:
                return KeiDict({})

            # 检查所有键的类型是否一致
            if obj.items:
                keys = list(obj.items.keys())
                first_key_type = type(keys[0])
                for key in keys[1:]:
                    if type(key) is not first_key_type:
                        raise KeiError("TypeError", f"字典键类型不一致: 有 {first_key_type.__name__} 和 {type(key).__name__}")

                # 检查所有值的类型是否一致
                values = list(obj.items.values())
                if values:
                    first_val_type = type(values[0])
                    for val in values[1:]:
                        if type(val) is not first_val_type:
                            raise KeiError("TypeError", f"字典值类型不一致: 有 {first_val_type.__name__} 和 {type(val).__name__}")

            # 按键排序（递归处理值）
            sorted_dict = {}
            for key in sorted(keys, key=lambda k: k.value if hasattr(k, 'value') else k):
                sorted_dict[key] = kei.sort(obj.items[key])

            return KeiDict(sorted_dict)

        # 其他类型
        else:
            return obj

    @s
    def exec(codes):
        from kei import exec as keiexec
        new_env = keiexec(codes, kei.getenv())[0]

        return KeiNamespace("__exec__", new_env)

    @s
    def eval(codes):
        from kei import exec as keiexec
        ret = keiexec(codes, kei.getenv())[1]

        return ret

    @s
    def python(module_name):
        """导入 Python 模块"""
        if isinstance(module_name, KeiString):
            module_name = module_name.value

        # 用 Python 的 __import__
        try:
            module = __import__(module_name)
        except ImportError:
            raise KeiError("ImportError", f"没有模块{module_name}")

        # 包装成 Kei 对象
        return kei._wrap_module(module)

    @s
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
            return [kei.topy(item) for item in value.items]

        # 字典
        if isinstance(value, KeiDict):
            return {kei.topy(k): kei.topy(v) for k, v in value.items.items()}

        # 命名空间
        if isinstance(value, KeiNamespace):
            return {k: kei.topy(v) for k, v in value.env.items()}

        # 函数/方法（返回函数本身，调用时再转换参数）
        if callable(value):
            return value

        # 其他 Kei 对象
        if hasattr(value, '_props'):
            return {k: kei.topy(v) for k, v in value._props.items()}

        # 默认返回原值
        return value

    @s
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
            return KeiList([kei.tokei(item) for item in value])

        # 字典
        if isinstance(value, dict):
            return KeiDict({kei.tokei(k): kei.tokei(v) for k, v in value.items()})

        # 函数（包装成可调用的 Kei 对象）
        if callable(value):
            return kei._wrap_module(value)

        # 模块
        if hasattr(value, '__name__') and hasattr(value, '__dict__'):
            return kei._wrap_module(value)

        # 其他类型，尝试转字符串
        try:
            return KeiString(str(value))
        except:
            return value

    @s
    def read(filename, encoding='utf-8'):
        kei.check(filename, KeiString, name='read')
        assert isinstance(filename, KeiString)
        filename = filename.value

        try:
            with open(filename, 'r', encoding=encoding) as f:
                return KeiString(f.read())

        except FileNotFoundError:
            raise KeiError("NotFoundError", f"未找到文件{filename}")
        except IsADirectoryError:
            raise KeiError("IsDirError", f"{filename}期望文件但得到文件夹")

    @s
    def write(filename, content, encoding='utf-8', append=KeiBool(False)):
        kei.check(filename, KeiString, name='write')
        kei.check(content, KeiString, KeiFloat, KeiBool, KeiList, KeiDict, name='write')
        kei.check(append, KeiBool, name='write')
        assert isinstance(filename, KeiString)
        assert isinstance(content, (KeiString, KeiFloat, KeiBool, KeiList, KeiDict))
        assert isinstance(append, KeiBool)

        mode = 'a' if append.value else 'w'
        filename = filename.value

        if isinstance(content, (KeiList, KeiDict)):
            content = content.items
        else:
            content = content.value

        try:
            with open(filename, mode, encoding=encoding) as f:
                if type(content) is list or type(content) is dict:
                    import json
                    json.dump(content, f, indent=4, ensure_ascii=False)
                else:
                    f.write(str(content))

        except FileNotFoundError:
            raise KeiError("NotFoundError", f"未找到文件{filename}")
        except IsADirectoryError:
            raise KeiError("IsDirError", f"{filename}期望文件但得到文件夹")

        return null

    @s
    def repr(value):
        return KeiString(content(value, _in_container=True))

    @s
    def _wrap_module(module):
        """把 Python 模块包装成 KeiDict"""
        result = {}
        for name in dir(module):
            if not name.startswith('_'):
                attr = getattr(module, name)
                if callable(attr):
                    result[name] = attr  # 函数直接暴露
                else:
                    result[name] = attr
        return KeiNamespace(module.__name__, result)

func = {
    "factorial": kei.factorial,
    "assert": kei._assert,
    "print": kei.print,
    "println": kei.println,
    "input": kei.input,
    "type": kei.type,
    "len": kei.len,
    "abs": kei.abs,
    "sleep": kei.sleep,
    "gettime": kei.gettime,
    "max": kei.max,
    "min": kei.min,
    "zip": kei.zip,
    "range": kei.range,
    "system": kei.system,
    "random": kei.random,
    "timer": kei.timer,
    "cnlen": kei.cnlen,
    "exit": kei.exit,
    "loop": kei.loop,
    "sort": kei.sort,
    "exec": kei.exec,
    "clear": kei.clear,
    "python": kei.python,
    "topy": kei.topy,
    "tokei": kei.tokei,
    "eval": kei.eval,
    "read": kei.read,
    "write": kei.write,
    "breakpoint": kei.breakpoint,
    "repr": kei.repr,
    "step": kei.step,
    "open": kei.open,
    "any": KeiBase,
    "int": KeiInt,
    "float": KeiFloat,
    "string": KeiString,
    "bool": KeiBool,
    "list": KeiList,
    "dict": KeiDict,
    "true": true,
    "false": false,
    "null": null,
    "undefined": undefined,
    "...": omit,
}

__all__ = ["kei", "func"]

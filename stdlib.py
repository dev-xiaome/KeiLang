#!/usr/bin/env python

from object import *
from lib.kei2py import *
import lib.python as python

env = KeiDict({}.copy())

class kei:
    s = staticmethod

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
    def cnlen(text) -> KeiInt:
        kei.check(text, KeiString, str, name='cnlen')
        text = python.topy(text)
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

        return KeiInt(length)

    @s
    def exit(code=KeiInt(0)):
        kei.check(code, KeiString, KeiInt, KeiFloat, KeiBool, name='exit')
        code = code.value
        import sys
        sys.exit(code)

    @s
    def print(*text, sep=KeiString(' '), just=KeiInt(0), color=null, flush=KeiBool(True)):
        kei.check(sep, KeiString, name='print')
        kei.check(just, KeiInt, name='print')
        kei.check(flush, KeiBool, name='print')

        assert isinstance(sep, KeiString)
        assert isinstance(just, KeiInt)
        assert isinstance(flush, KeiBool)

        sep_str = sep.value
        just_val = just.value
        flush_val = flush.value

        # 构建文本
        text_str = sep_str.join(content(t) for t in text)

        # 处理对齐
        try:
            spaces = abs(just_val) - kei.cnlen(text_str)
        except:
            spaces = 0

        if just_val > 0:
            text_str = " " * spaces + text_str
        elif just_val < 0:
            text_str = text_str + " " * spaces

        # 处理颜色
        color_str = "null"
        if isinstance(color, KeiString):
            color_str = color.value
        elif color is not null:
            color_str = str(color)

        colors = {
            'null': '',
            'black': '30',
            'red': '31',
            'green': '32',
            'yellow': '33',
            'blue': '34',
            'purple': '35',
            'cyan': '36',
            'white': '37',
            'black+': '90',
            'red+': '91',
            'green+': '92',
            'yellow+': '93',
            'blue+': '94',
            'purple+': '95',
            'cyan+': '96',
            'white+': '97',
        }

        # 彩虹模式
        if color_str in ('rainbow', 'rainbow+'):
            # 生成彩虹渐变
            gradient = []
            for i in range(len(text_str)):
                pos = (i / max(1, len(text_str) - 1)) * 5
                segment = int(pos)
                frac = pos - segment

                if color_str == 'rainbow':
                    colors_rgb = [
                        (255, 0, 0),
                        (255, 255, 0),
                        (0, 255, 0),
                        (0, 255, 255),
                        (0, 0, 255),
                        (255, 0, 255)
                    ]

                elif color_str == 'rainbow+':
                    colors_rgb = [
                        (255, 128, 128),
                        (255, 255, 128),
                        (128, 255, 128),
                        (128, 255, 255),
                        (128, 128, 255),
                        (255, 128, 255),
                    ]

                if segment >= 5:
                    r, g, b = colors_rgb[5]
                else:
                    r1, g1, b1 = colors_rgb[segment]
                    r2, g2, b2 = colors_rgb[segment + 1]
                    r = int(r1 * (1 - frac) + r2 * frac)
                    g = int(g1 * (1 - frac) + g2 * frac)
                    b = int(b1 * (1 - frac) + b2 * frac)

                ansi = 16 + (36 * (r // 51)) + (6 * (g // 51)) + (b // 51)
                gradient.append(f"\033[38;5;{ansi}m")

            # 输出彩虹文本
            result = []
            for i, ch in enumerate(text_str):
                result.append(f"{gradient[i]}{ch}\033[0m")
            output = ''.join(result)
        else:
            # 普通颜色
            color_code = colors.get(color_str, '')
            if color_code:
                output = f"\033[{color_code}m{text_str}\033[0m"
            else:
                output = text_str

        # 输出
        print(output, end='', flush=flush_val)
        return KeiString(text_str)

    @s
    def println(*args, **kwargs):
        """超级阉割版print"""
        result = kei.print(*args, **kwargs)
        print()
        return result

    @s
    def sleep(second: KeiFloat):
        import time
        time.sleep(to_float(second))
        return KeiFloat(second)

    @s
    def gettime():
        import time
        t = time.time()  # 只调用一次
        return KeiFloat(t) if isinstance(t, float) else KeiInt(t)

    @s
    def clear():
        import subprocess
        import os

        subprocess.run('clear' if os.name == 'posix' else 'cls', shell=True)

    @s
    def range(*args):
        py_args = []
        for a in args:
            kei.check(a, KeiFloat, name='range')
            py_args.append(a.value)

        if len(py_args) == 1:
            return KeiList([KeiInt(i) for i in range(py_args[0])])
        elif len(py_args) == 2:
            return KeiList([KeiInt(i) for i in range(py_args[0], py_args[1])])
        elif len(py_args) == 3:
            return KeiList([KeiInt(i) for i in range(py_args[0], py_args[1], py_args[2])])
        else:
            raise Exception("range 需要 1~3 个参数")

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
        elif type(string) is KeiDict:
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
    def input(ps=KeiString('')):
        return KeiString(input(content(ps)))

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
            raise KeiError("ValueError", "max 需要至少一个参数")

        # 处理 key 参数
        if key is not None:
            if isinstance(key, KeiFunction):
                def key_wrapper(x):
                    k = key(x)
                    # 获取原始值用于二级比较
                    if hasattr(x, 'value'):
                        raw_x = x.value
                    else:
                        raw_x = x
                    return (k, raw_x)
                key_func = key_wrapper
            else:
                key_func = key
        else:
            # 自动检测类型
            if len(args) == 1 and isinstance(args[0], KeiList):
                items = args[0].items
            else:
                items = list(args)

            if not items:
                raise KeiError("ValueError", "max 的参数列表不能为空")

            # 检查所有元素类型
            all_string = True
            all_number = True
            all_bool = True

            for item in items:
                if not isinstance(item, KeiString):
                    all_string = False
                if not isinstance(item, (KeiInt, KeiFloat)):
                    all_number = False
                if not isinstance(item, KeiBool):
                    all_bool = False

            if all_string:
                # 字符串：只按长度比较
                def str_key_func(x):
                    if isinstance(x, KeiString):
                        return len(x.value)
                    return 0
                key_func = str_key_func

            elif all_number:
                # 数字：直接比较值
                key_func = lambda x: x.value if isinstance(x, (KeiInt, KeiFloat)) else x
            elif all_bool:
                # 布尔值：有 true 就返回 true，否则 false
                for item in items:
                    if item.value:
                        return true
                return false
            else:
                # 混合类型，用默认比较
                key_func = lambda x: x

        # 如果只有一个参数且是列表
        if len(args) == 1 and isinstance(args[0], KeiList):
            items = args[0].items
            if not items:
                raise KeiError("ValueError", "max 的列表不能为空")

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
    def breakpoint(value=None):
        from kei import __kei__

        if __kei__.step is None:
            return __kei__.step

        if value is None:
            __kei__.step = kei.breakpoint
        else:
            value = to_str(value)
            if __kei__.step == value:
                __kei__.step = kei.breakpoint

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
    def min(*args, key=None):
        """返回最小值，支持多个参数或列表，支持 key 函数"""
        if len(args) == 0:
            raise KeiError("ValueError", "min 需要至少一个参数")

        # 处理 key 参数
        if key is not None:
            if isinstance(key, KeiFunction):
                def key_wrapper(x):
                    k = key(x)
                    # 获取原始值用于二级比较
                    if hasattr(x, 'value'):
                        raw_x = x.value
                    else:
                        raw_x = x
                    return (k, raw_x)
                key_func = key_wrapper
            else:
                key_func = key
        else:
            # 自动检测类型
            if len(args) == 1 and isinstance(args[0], KeiList):
                items = args[0].items
            else:
                items = list(args)

            if not items:
                raise KeiError("ValueError", "min 的参数列表不能为空")

            # 检查所有元素类型
            all_string = True
            all_number = True
            all_bool = True

            for item in items:
                if not isinstance(item, KeiString):
                    all_string = False
                if not isinstance(item, (KeiInt, KeiFloat)):
                    all_number = False
                if not isinstance(item, KeiBool):
                    all_bool = False

            if all_string:
                # 字符串：只按长度比较
                def str_key_func(x):
                    if isinstance(x, KeiString):
                        return len(x.value)
                    return 0
                key_func = str_key_func

            elif all_number:
                # 数字：直接比较值
                key_func = lambda x: x.value if isinstance(x, (KeiInt, KeiFloat)) else x
            elif all_bool:
                # 布尔值：有 false 就返回 false，否则 true
                for item in items:
                    if not item.value:
                        return false
                return true
            else:
                # 混合类型，用默认比较
                key_func = lambda x: x

        # 如果只有一个参数且是列表
        if len(args) == 1 and isinstance(args[0], KeiList):
            items = args[0].items
            if not items:
                raise KeiError("ValueError", "min 的列表不能为空")

            min_item = items[0]
            min_key = key_func(min_item)
            for item in items[1:]:
                k = key_func(item)
                if k < min_key:
                    min_item = item
                    min_key = k
            return min_item

        # 多个参数
        min_item = args[0]
        min_key = key_func(min_item)
        for arg in args[1:]:
            k = key_func(arg)
            if k < min_key:
                min_item = arg
                min_key = k
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
    def copy(obj):
        import copy

        try:
            if hasattr(obj, "__deepcopy__"):
                return obj.__deepcopy__()

            return copy.deepcopy(obj)
        except:
            try:
                if hasattr(obj, "__copy__"):
                    return obj.__copy__()

                return copy.copy(obj)
            except:
                raise KeiError("CopyError", "深复制和浅复制失败")

    @s
    def exec(codes, env=None, copy=KeiBool(False)):
        from kei import exec as keiexec

        copy = to_bool(copy)

        temp_env = kei.getenv() if env is None else env
        if copy:
            temp_env = kei.copy(temp_env)

        new_env = keiexec(codes, temp_env)[0]

        return KeiNamespace("__exec__", new_env)

    @s
    def eval(codes, env=None, copy=KeiBool(False)):
        from kei import exec as keiexec

        temp_env = kei.getenv() if env is None else env
        if copy:
            temp_env = kei.copy(temp_env)

        ret = keiexec(codes, temp_env)[1]

        return ret

    @s
    def read(filename, encoding='utf-8'):
        kei.check(filename, KeiString, name='read')
        assert isinstance(filename, KeiString)
        filename = filename.value

        try:
            with open(filename, 'r', encoding=encoding) as f:
                return KeiString(f.read())

        except FileNotFoundError:
            raise KeiError("FileNotFoundError", f"未找到文件{filename}")
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
            raise KeiError("FileNotFoundError", f"未找到文件{filename}")
        except IsADirectoryError:
            raise KeiError("IsDirError", f"{filename}期望文件但得到文件夹")

        return null

    @s
    def recursion(c=None):
        from kei import __kei__

        if c is None:
            return KeiInt(__kei__.maxrecursion)

        if type(c) is KeiInt:
            c = c.value

            if c > 0:
                __kei__.maxrecursion = c
            elif c == 0:
                __kei__.maxrecursion = 1024
            else:
                raise KeiError("ValueError", "最大递归次数不能是负数")
        else:
            raise KeiError("ValueError", "最大递归次数必须是整数")

    @s
    def precision(c=None):
        from decimal import getcontext

        if c is None:
            return KeiInt(getcontext().prec)

        if type(c) is KeiInt:
            c = c.value

            if c > 0:
                getcontext().prec = c
            elif c == 0:
                getcontext().prec = 28
            else:
                raise KeiError("ValueError", "精度不能是负数")
        else:
            raise KeiError("TypeError", "精度必须是整数")

    @s
    def dir(*args, **kwargs):
        return KeiList(dir(*args, **kwargs))

    @s
    def importlib(modulename):
        import kei as _kei

        source = _kei.__dict__.get('source', None)
        linenum = _kei.__dict__.get('linenum', None)

        _kei.__kei__.error = False

        try:
            return kei.exec(KeiString(f"import {modulename};"), copy=KeiBool(True))[modulename]
        finally:
            _kei.__kei__.error = True

            if source is not None:
                _kei.__dict__['source'] = source
            if linenum is not None:
                _kei.__dict__['linenum'] = linenum

    @s
    def hash(obj, depth=0, seen=None):
        """递归计算 KeiLang 对象的哈希值"""
        if seen is None:
            seen = set()

        # 防止无限递归
        if depth > 100:
            return hash(id(obj))

        obj_id = id(obj)
        if obj_id in seen:
            return hash(obj_id)
        seen.add(obj_id)

        # None/null/undefined
        if obj is None or obj is null or obj is undefined:
            return hash("null")

        # 基础类型
        if isinstance(obj, (KeiInt, KeiFloat)):
            return hash(obj.value)

        if isinstance(obj, KeiBool):
            return hash(obj.value)

        if isinstance(obj, KeiString):
            return hash(obj.value)

        # 列表
        if isinstance(obj, KeiList):
            h = hash("list")
            for item in obj.items:
                h ^= kei.hash(item, depth + 1, seen)
            return h

        # 字典
        if isinstance(obj, KeiDict):
            h = hash("dict")
            for k, v in sorted(obj.items.items(), key=lambda x: kei.hash(x[0], depth + 1, seen)):
                h ^= kei.hash(k, depth + 1, seen)
                h ^= kei.hash(v, depth + 1, seen)
            return h

        # 函数
        if isinstance(obj, KeiFunction):
            h = hash("function")
            h ^= hash(obj.__name__)
            if hasattr(obj, 'func_obj'):
                # 参数
                params = obj.func_obj.get('params', [])
                h ^= hash(tuple(params))
                # 函数体
                body = obj.func_obj.get('body', [])
                for stmt in body:
                    h ^= kei.hash(stmt, depth + 1, seen)
            return h

        # 类
        if isinstance(obj, KeiClass):
            h = hash("class")
            h ^= hash(obj.__name__)
            if hasattr(obj, '_methods_map'):
                for name, method in obj._methods_map.items():
                    h ^= hash(name)
                    h ^= kei.hash(method, depth + 1, seen)
            if hasattr(obj, '_class_attrs'):
                for k, v in obj._class_attrs.items():
                    h ^= hash(k)
                    h ^= kei.hash(v, depth + 1, seen)
            return h

        # 实例
        if isinstance(obj, KeiInstance):
            h = hash("instance")
            h ^= kei.hash(obj._class, depth + 1, seen)
            if hasattr(obj, '_attrs'):
                for k, v in obj._attrs.items():
                    h ^= hash(k)
                    h ^= kei.hash(v, depth + 1, seen)
            return h

        # 命名空间
        if isinstance(obj, KeiNamespace):
            h = hash("namespace")
            h ^= hash(obj.__name__)
            if hasattr(obj, 'nsenv'):
                for k, v in sorted(obj.nsenv.items()):
                    h ^= hash(k)
                    h ^= kei.hash(v, depth + 1, seen)
            return h

        # 方法
        if isinstance(obj, (KeiMethod, KeiBoundMethod)):
            h = hash("method")
            h ^= hash(obj.__name__)
            if hasattr(obj, 'method_obj'):
                h ^= kei.hash(obj.method_obj, depth + 1, seen)

            # 安全获取 instance
            instance = getattr(obj, 'instance', None)
            if instance is not None and instance:  # 先检查不为 None，再检查布尔值
                h ^= kei.hash(instance, depth + 1, seen)
            return h

        # 错误对象
        if isinstance(obj, KeiError):
            h = hash("error")
            h ^= hash(obj.types)
            h ^= hash(obj.value)
            return h

        # 有 __hash__ 方法的
        if hasattr(obj, '__hash__') and callable(obj.__hash__):
            try:
                return hash(obj)
            except:
                pass

        # 有 __dict__ 的
        if hasattr(obj, '__dict__'):
            h = hash(type(obj).__name__)
            for k, v in sorted(obj.__dict__.items()):
                h ^= hash(k)
                h ^= kei.hash(v, depth + 1, seen)
            return h

        # 最后手段：用 id
        return hash(id(obj))

    @s
    def isinstance(obj, cls):
        """检查 obj 是否是 cls 的实例，支持 KeiList 作为多个类型"""
        # 如果 cls 是 KeiList，检查是否匹配其中任意一个
        if isinstance(cls, KeiList):
            for c in cls.items:
                if kei.isinstance(obj, c):
                    return true
            return false

        # 转换 Python 类型
        if isinstance(cls, type):
            # 检查 KeiLang 类型
            if isinstance(obj, cls):
                return true
            # 检查 Python 内置类型
            if isinstance(obj, (KeiInt, KeiFloat, KeiString, KeiBool, KeiList, KeiDict)):
                if cls in (int, float, str, bool, list, dict):
                    return true
            return false

        # 如果是 KeiClass
        if isinstance(cls, KeiClass):
            # 获取 KeiClass 对应的 Python 类型
            if hasattr(cls, 'py_parent'):
                py_parent = getattr(cls, 'py_parent')
                return kei.isinstance(obj, py_parent)
            # 检查是否是 KeiClass 的实例
            if isinstance(obj, KeiInstance) and obj._class == cls:
                return true
            return false

        # 如果是 KeiString（类名）
        if isinstance(cls, KeiString):
            cls_name = cls.value
            # 检查 KeiLang 内置类型
            builtin_types = {
                'int': KeiInt,
                'float': KeiFloat,
                'string': KeiString,
                'bool': KeiBool,
                'list': KeiList,
                'dict': KeiDict,
            }
            if cls_name in builtin_types:
                return kei.isinstance(obj, builtin_types[cls_name])
            # 检查环境中的类
            from kei import __kei__
            if cls_name in __kei__.env:
                if __kei__.env is not None and cls_name in __kei__.env:
                    return kei.isinstance(obj, __kei__.env[cls_name])
            return false

        return false

    @s
    def getattr(obj, name, default=undefined):
        """获取对象的属性"""
        name = to_str(name)

        # 如果是 Kei 对象
        if isinstance(obj, KeiBase):
            try:
                return obj[name]
            except:
                if default is not undefined:
                    return default
                raise KeiError("AttributeError", f"'{type(obj).__name__}' 对象没有属性 '{name}'")

        # Python 对象
        try:
            return getattr(obj, name)
        except AttributeError:
            if default is not undefined:
                return default
            raise KeiError("AttributeError", f"'{type(obj).__name__}' 对象没有属性 '{name}'")

    @s
    def hasattr(obj, name):
        """检查对象是否有属性"""
        name = to_str(name)

        # 如果是 Kei 对象
        if isinstance(obj, KeiBase):
            try:
                obj[name]
                return true
            except:
                return false

        # Python 对象
        try:
            return true if hasattr(obj, name) else false
        except:
            return false

    @s
    def setattr(obj, name, value):
        """设置对象属性"""
        name = to_str(name)

        if isinstance(obj, KeiBase):
            obj[name] = value
        else:
            setattr(obj, name, value)
        return null

    @s
    def isclass(obj):
        return true if isinstance(obj, KeiClass) else false

    @s
    def delattr(obj, name):
        name = to_str(name)

        if hasattr(obj, "_method") and name in obj._method:
            del obj._method[name]
        elif hasattr(obj, "_prop") and name in obj._prop:
            del obj._prop[name]
        elif hasattr(obj, "_attrs") and name in obj._attrs:
            del obj._attrs[name]

    @s
    def delitem(obj, name):
        name = to_str(name)

        if hasattr(obj, "items"):
            if isinstance(obj.items, (dict, KeiDict)):
                del obj.items[name]

    @s
    def delete(obj):
        obj = undefined

    @s
    def bin(obj, bits=None):
        """将任何 KeiLang 对象转换为二进制字符串"""

        # 转换 bits 参数
        if bits is not None:
            if isinstance(bits, KeiInt):
                bits = bits.value
            else:
                bits = int(bits)

        # None / null / undefined
        if obj is None or obj is null or obj is undefined:
            return "0"

        # 整数
        if isinstance(obj, KeiInt):
            val = obj.value
            if val >= 0:
                s = bin(val)[2:]
            else:
                s = bin(val & 0xFFFFFFFFFFFFFFFF)[2:]
            if bits is not None:
                s = s.zfill(bits)
            return s

        # 浮点数
        if isinstance(obj, KeiFloat):
            import struct
            val = float(obj.value)
            packed = struct.pack('>d', val)
            i = struct.unpack('>Q', packed)[0]
            s = bin(i)[2:].zfill(64)
            if bits is not None:
                s = s[-bits:] if bits < 64 else s.zfill(bits)
            return s

        # 布尔值
        if isinstance(obj, KeiBool):
            return "1" if obj.value else "0"

        # 字符串
        if isinstance(obj, KeiString):
            result = []
            for ch in obj.value:
                code = ord(ch)
                result.append(bin(code)[2:].zfill(16))
            if bits is not None:
                full = ''.join(result)
                return full[-bits:] if bits < len(full) else full.zfill(bits)
            return ' '.join(result)

        # 列表
        if isinstance(obj, KeiList):
            result = [kei.bin(item, bits) for item in obj.items]
            return '[' + ', '.join(result) + ']'

        # 字典
        if isinstance(obj, KeiDict):
            result = []
            for k, v in obj.items.items():
                k_bin = kei.bin(k, bits)
                v_bin = kei.bin(v, bits)
                result.append(f"{k_bin}: {v_bin}")
            return '{' + ', '.join(result) + '}'

        # 其他类型
        s = str(obj)
        result = []
        for ch in s:
            result.append(bin(ord(ch))[2:].zfill(16))
        return ' '.join(result)

    @s
    def hex(obj, bits=None):
        """将任何 KeiLang 对象转换为十六进制字符串"""

        # 转换 bits 参数
        if bits is not None:
            if isinstance(bits, KeiInt):
                bits = bits.value
            else:
                bits = int(bits)

        # None / null / undefined
        if obj is None or obj is null or obj is undefined:
            return "0"

        # 整数
        if isinstance(obj, KeiInt):
            val = obj.value
            if val >= 0:
                s = hex(val)[2:]
            else:
                # 负数用补码表示
                s = hex(val & 0xFFFFFFFFFFFFFFFF)[2:]
            if bits is not None:
                # bits 是二进制位数，转成十六进制需要 (bits + 3) // 4 个字符
                hex_len = (bits + 3) // 4
                s = s.zfill(hex_len)
            return s

        # 浮点数（转 IEEE 754 双精度 64 位 → 十六进制）
        if isinstance(obj, KeiFloat):
            import struct
            val = float(obj.value)
            packed = struct.pack('>d', val)
            i = struct.unpack('>Q', packed)[0]
            s = hex(i)[2:].zfill(16)
            if bits is not None:
                hex_len = (bits + 3) // 4
                s = s[-hex_len:] if hex_len < 16 else s.zfill(hex_len)
            return s

        # 布尔值
        if isinstance(obj, KeiBool):
            return "1" if obj.value else "0"

        # 字符串（转每个字符的 Unicode 十六进制）
        if isinstance(obj, KeiString):
            result = []
            for ch in obj.value:
                code = ord(ch)
                result.append(hex(code)[2:].zfill(4))
            if bits is not None:
                # 如果指定位数，拼接后截断或填充
                full = ''.join(result)
                hex_len = (bits + 3) // 4
                return full[-hex_len:] if hex_len < len(full) else full.zfill(hex_len)
            return ' '.join(result)

        # 列表
        if isinstance(obj, KeiList):
            result = [kei.hex(item, bits) for item in obj.items]
            return '[' + ', '.join(result) + ']'

        # 字典
        if isinstance(obj, KeiDict):
            result = []
            for k, v in obj.items.items():
                k_hex = kei.hex(k, bits)
                v_hex = kei.hex(v, bits)
                result.append(f"{k_hex}: {v_hex}")
            return '{' + ', '.join(result) + '}'

        # 其他类型：先转字符串再转十六进制
        s = str(obj)
        result = []
        for ch in s:
            result.append(hex(ord(ch))[2:].zfill(4))
        return ' '.join(result)

    class File(KeiBase):
        """KeiLang 文件对象类"""

        def __init__(self, path, mode=KeiString('r'), encoding=KeiString('utf-8')):
            super().__init__("file")

            kei.check(path, KeiString, name="file")
            kei.check(mode, KeiString, name="file")
            kei.check(encoding, KeiString, name="file")

            # 转换参数
            if isinstance(path, KeiString):
                path = path.value
            if isinstance(mode, KeiString):
                mode = mode.value
            if isinstance(encoding, KeiString):
                encoding = encoding.value

            # 底层文件句柄（开发者可读，但约定为内部）
            self._handle = open(path, mode, encoding=encoding)

            # 公开属性（开发者可直接访问）
            self.path = path
            self.mode = mode
            self.encoding = encoding

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

            self._props['path']     = path
            self._props['mode']     = mode
            self._props['encoding'] = encoding
            self._props['closed']   = false

        # ========== 上下文管理器 ==========
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.close()
            return False

        def __del__(self):
            self.close()
            return False

        # ========== 文件操作 ==========
        def remove(self):
            """删除文件"""
            import os
            os.remove(self.path)

        def read(self, size=-1):
            if isinstance(size, KeiInt):
                size = size.value
            return KeiString(self._handle.read(size))

        def readline(self, size=-1):
            if isinstance(size, KeiInt):
                size = size.value
            return KeiString(self._handle.readline(size))

        def readlines(self, hint=-1):
            if isinstance(hint, KeiInt):
                hint = hint.value
            lines = self._handle.readlines(hint)
            return KeiList([KeiString(line.rstrip('\n')) for line in lines])

        def write(self, text):
            if isinstance(text, KeiString):
                text = text.value
            return KeiInt(self._handle.write(text))

        def writelines(self, lines):
            if isinstance(lines, KeiList):
                lines = [line.value if isinstance(line, KeiString) else str(line) for line in lines.items]
            self._handle.writelines(lines)
            return null

        def close(self):
            self._handle.close()
            self._props['closed'] = true
            return null

        def flush(self):
            self._handle.flush()
            return null

        def seek(self, offset, whence=0):
            if isinstance(offset, KeiInt):
                offset = offset.value
            if isinstance(whence, KeiInt):
                whence = whence.value
            return KeiInt(self._handle.seek(offset, whence))

        def tell(self):
            return KeiInt(self._handle.tell())

    class decorator:
        def __init__(self, name):
            self.name = name

        def __call__(self, func):
            return func

    static = decorator("static")
    prop = decorator("prop")
    super = decorator("super")

keistdlib = """
class gen {
    fn __init__(self, func) {
        self.func  = func;
        self.value = -1;
    };

    fn __call__(self, *args, **kwargs) {
        return self.func(yield=self.value++, *args, **kwargs);
    };

    @static
    fn yield(num, values) {
        return (values[num] ?? null);
    };
};

class funcattr {
    fn __init__(self, func) {
        self.func = func;
    };
    fn __call__(self, *args, **kwargs) {
        return self.func(*args, **kwargs);
    };
};
"""

func = {
    "type": type,
    "isinstance": kei.isinstance,
    "getattr": kei.getattr,
    "hasattr": kei.hasattr,
    "setattr": kei.setattr,
    "copy": kei.copy,
    "hash": kei.hash,
    "hasattr": kei.hasattr,
    "dir": kei.dir,
    "factorial": kei.factorial,
    "assert": kei._assert,
    "print": kei.print,
    "println": kei.println,
    "input": kei.input,
    "len": kei.len,
    "abs": kei.abs,
    "sleep": kei.sleep,
    "gettime": kei.gettime,
    "max": kei.max,
    "min": kei.min,
    "zip": kei.zip,
    "delattr": kei.delattr,
    "range": kei.range,
    "system": kei.system,
    "random": kei.random,
    "cnlen": kei.cnlen,
    "isclass": kei.isclass,
    "exit": kei.exit,
    "loop": kei.loop,
    "sort": kei.sort,
    "bin": kei.bin,
    "hex": kei.hex,
    "exec": kei.exec,
    "clear": kei.clear,
    "eval": kei.eval,
    "read": kei.read,
    "delitem": kei.delitem,
    "write": kei.write,
    "breakpoint": kei.breakpoint,
    "step": kei.step,
    "delete": kei.delete,
    "importlib": kei.importlib,
    "precision": kei.precision,
    "recursion": kei.recursion,
    "super": kei.super,
    "static": kei.static,
    "prop": kei.prop,
    "File": kei.File,
    "int": KeiInt,
    "float": KeiFloat,
    "string": KeiString,
    "bool": KeiBool,
    "list": KeiList,
    "dict": KeiDict,
    "instance": KeiInstance,
    "true": true,
    "false": false,
    "null": null,
    "undefined": undefined,
    "...": omit,
}

__all__ = ["kei", "func"]

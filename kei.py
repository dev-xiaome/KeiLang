#!/usr/bin/env python
"""KeiLang"""

from decimal import getcontext
from typing import List, Any, Optional
import platform
import inspect
import sys
import os

if __name__ == '__main__':
    sys.modules['kei'] = sys.modules['__main__']

__version__ = "1.6-7"

class KeiState:
    stack: List[Any]  # 添加类型提示
    catch: list
    code: Optional[List[str]]
    repl: bool
    file: str
    step: object
    error: bool
    var: list
    env: dict

    _instance: Optional['KeiState'] = None

    def __new__(cls) -> 'KeiState':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # 在 __new__ 中初始化属性
            cls._instance.stack = []
            cls._instance.catch = []
            cls._instance.code = None
            cls._instance.repl = False
            cls._instance.file = "未知文件"
            cls._instance.step = False
            cls._instance.error = True
            cls._instance.var = []
            cls._instance.env = {}

        return cls._instance

    def __init__(self) -> None:
        # __init__ 会被多次调用，但我们已经初始化过了
        pass

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

# 创建单例
__kei__: KeiState = KeiState()

try:
    __import__('readline')
except:
    pass

keidir = os.path.dirname(os.path.abspath(__file__))
path = os.environ.get('PATH', '')
paths = path.split(os.pathsep)

paths.append(os.path.abspath(os.path.join(keidir, 'lib')))

pkg_dir = os.path.join(keidir, 'pkg')
if os.path.isdir(pkg_dir):
    for item in os.listdir(pkg_dir):
        sub_path = os.path.join(pkg_dir, item)
        if os.path.isdir(sub_path):
            paths.append(sub_path)

__py_exec__ = exec

import lib.stdlib as stdlib
from lib.object import *

DEBUG = False

mapping = {}

keywords = [
   'class',
   'namespace',
   'if',
   'while',
   'fn',
   'return',
   'for',
   'else',
   'elif',
   'try',
   'catch',
   'with',
   'import',
   'break',
   'continue',
   'global',
   'raise',
   'case',
   'match',
   'use',
   'from'
]

sys.setrecursionlimit(1024)

def check_python_call(func, args, kwargs, func_name):
    """检查 Python 函数参数，提前抛出 KeiError"""
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        # 某些内置函数没有签名，跳过检查
        return

    # 统计必需参数
    required_params = []
    var_positional = None
    var_keyword = None

    for name, param in sig.parameters.items():
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            var_positional = name
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
            var_keyword = name
        elif param.default == inspect.Parameter.empty:
            required_params.append(name)

    # 检查位置参数数量
    pos_args_used = 0
    for i, arg in enumerate(args):
        if i < len(required_params):
            pos_args_used += 1
        elif var_positional is None:
            # 多余的位置参数且没有 *args
            break

    # 检查关键字参数
    kwargs_used = set()
    for k in kwargs.keys():
        if k in required_params:
            kwargs_used.add(k)
        elif var_keyword is None and k not in [p.name for p in sig.parameters.values() if p.kind != inspect.Parameter.VAR_KEYWORD]:
            raise KeiError("TypeError", f"{func_name}() 收到未预料的关键字参数 '{k}'")

    # 找出缺少的参数
    missing = []
    for p in required_params:
        if p not in kwargs_used and len(args) <= required_params.index(p):
            missing.append(p)

    if missing:
        if len(missing) == 1:
            raise KeiError("TypeError", f"{func_name}() 缺少参数 '{missing[0]}'")
        else:
            raise KeiError("TypeError", f"{func_name}() 缺少参数: {', '.join(missing)}")

def debug_print(*args, **kwargs):
    if DEBUG:
        print("[DEBUG]", *args, **kwargs)

def getname(node, env):
    """收集当前节点引用的变量，支持属性访问"""
    result = []
    seen = set()

    block_nodes = {
        'try', 'class', 'for', 'function', 'with', 'namespace',
        'if', 'while', 'unless', 'until', 'match'
    }

    def get_full_name(n):
        """从 attr 节点获取完整名称，如 math.pi"""
        if n.get("type") == "name":
            return n["value"]
        elif n.get("type") == "attr":
            obj_name = get_full_name(n["obj"])
            attr_name = n["attr"]
            return f"{obj_name}.{attr_name}"
        return None

    def traverse(n, current_depth):
        if current_depth > 0:
            return

        if isinstance(n, dict):
            if n.get("type") in block_nodes:
                if n.get("type") == "for" and "iterable" in n:
                    traverse(n["iterable"], current_depth)
                return

            # 处理 name 节点
            if n.get("type") == "name":
                name = n["value"]
                if name not in seen:
                    seen.add(name)
                    val = runtoken(n, env)[0]
                    result.append([name, val])

            # 处理 attr 节点（如 math.pi）
            if n.get("type") == "attr":
                full_name = get_full_name(n)
                if full_name and full_name not in seen:
                    seen.add(full_name)
                    val = runtoken(n, env)[0]
                    result.append([full_name, val])

                return result

            for v in n.values():
                traverse(v, current_depth)
        elif isinstance(n, list):
            for item in n:
                traverse(item, current_depth)

    traverse(node, 0)
    return result

def error(errtype: str | None, info: str, stack: list=[], code:str|None=None, linenum=None, filename='未知文件') -> None:
    linenum = linenum if linenum is not None else "??"
    space   = ' ' * len(str(linenum) if linenum is not None else "")

    print(f"File \033[33;1m{os.path.abspath(filename)}\033[0m")

    print(f"{space} ·")

    for s in stack:
        if type(s) is tuple and s[1].strip():
            print(f"{space} | in \033[36;1m{s[0]}: {s[1].strip()}\033[0m")
        else:
            print(f"{space} | in \033[36;1m{s}\033[0m")

    if not stack:
        print(f"{space} | in \033[36;1m<global>\033[0m")

    print(f"{space} |")

    if code is None:
        code = "未知行"

    code = code.strip()

    print(f"\033[33;1m{linenum}\033[0m | {code}")

    print(f"{space} | \033[31;1m" + ('^' * int(str(stdlib.kei.cnlen(KeiString(code)).value))) + "\033[0m")

    if errtype is not None:
        print(f"{space} | \033[36m>>>\033[0m \033[33;1m[{errtype}] {info}\033[0m")
    else:
        print(f"{space} | \033[36m>>>\033[0m \033[33;1m{info}\033[0m")

    print(f"{space} ·")

    import traceback
    traceback.print_exc()

    if not __kei__.repl:
        sys.exit(1)

def dict_diff(d1, d2, path="", seen=None):
    if seen is None:
        seen = set()

    # 跳过自引用键
    skip_keys = {'__env__', '__parent__', '__builtins__'}

    added = []
    removed = []
    changed = []

    # 处理 d1
    for key in d1.keys():
        key_str = str(key)

        # 跳过特殊键
        if key_str in skip_keys:
            continue

        full_path = f"{path}.{key_str}" if path else key_str

        # 防止循环引用
        obj_id = id(d1[key])
        if obj_id in seen:
            continue
        seen.add(obj_id)

        if key not in d2:
            removed.append(f"{full_path} = {content(d1[key], _in_container=True)}")
        else:
            v1 = d1[key]
            v2 = d2[key]

            if isinstance(v1, dict) and isinstance(v2, dict):
                sub_added, sub_removed, sub_changed = dict_diff(v1, v2, full_path, seen)
                added.extend(sub_added)
                removed.extend(sub_removed)
                changed.extend(sub_changed)
            elif v1 != v2:
                changed.append(f"{full_path}: {content(v2, _in_container=True)} -> {content(v1, _in_container=True)}")

        seen.remove(obj_id)

    # 处理 d2 新增
    for key in d2.keys():
        key_str = str(key)
        if key_str in skip_keys:
            continue

        full_path = f"{path}.{key_str}" if path else key_str

        if key not in d1:
            added.append(full_path)

    return added, removed, changed

def token(original: str) -> list:
    try:
        if __kei__.code is None:
            __kei__.code = original.splitlines()

        result = []
        lines = original.splitlines()
        i = 0
        while i < len(lines):
            codes = lines[i].rstrip()
            if not codes:
                result.append([])
                i += 1
                continue

            tokens = []
            pos = 0
            length = len(codes)

            while pos < length:
                if pos >= length:
                    break

                c = codes[pos]

                if c == '.' and pos + 2 < length and codes[pos+1] == '.' and codes[pos+2] == '.':
                    tokens.append("...")
                    pos += 3
                    continue

                # 重要：先检查 ** 操作符
                if c == '*' and pos + 1 < length and codes[pos+1] == '*':
                    tokens.append("**")
                    pos += 2
                    continue

                # 检查逗号
                if c == ',':
                    tokens.append(",")
                    pos += 1
                    continue

                if c == "?" and pos + 1 < length and codes[pos+1] == '?':
                    tokens.append("??")
                    pos += 2
                    continue

                if c == '+' and pos + 1 < length and codes[pos+1] == '+':
                    tokens.append("++")
                    pos += 2
                    continue

                if c == '-' and pos + 1 < length and codes[pos+1] == '-':
                    tokens.append("--")
                    pos += 2
                    continue

                if c == '=' and pos + 1 < length and codes[pos+1] == '>':
                    tokens.append("=>")
                    pos += 2
                    continue

                # 检查 +=
                if c == '+' and pos + 1 < length and codes[pos+1] == '=':
                    tokens.append("+=")
                    pos += 2
                    continue

                # 检查 -=
                if c == '-' and pos + 1 < length and codes[pos+1] == '=':
                    tokens.append("-=")
                    pos += 2
                    continue

                # 检查 *=
                if c == '*' and pos + 1 < length and codes[pos+1] == '=':
                    tokens.append("*=")
                    pos += 2
                    continue

                # 检查 /=
                if c == '/' and pos + 1 < length and codes[pos+1] == '=':
                    tokens.append("/=")
                    pos += 2
                    continue

                # 检查冒号
                if c == ':':
                    tokens.append(":")
                    pos += 1
                    continue

                # 检查大括号
                if c == '{':
                    tokens.append("{")
                    pos += 1
                    continue
                if c == '}':
                    tokens.append("}")
                    pos += 1
                    continue

                # 检查中括号
                if c == '[':
                    tokens.append("[")
                    pos += 1
                    continue
                if c == ']':
                    tokens.append("]")
                    pos += 1
                    continue

                # 检查小括号
                if c == '(':
                    tokens.append("(")
                    pos += 1
                    continue
                if c == ')':
                    tokens.append(")")
                    pos += 1
                    continue

                # 普通单行字符串
                if c in '"\'':
                    start = pos
                    quote = c
                    pos += 1
                    while pos < length and codes[pos] != quote:
                        if codes[pos] == '\\' and pos + 1 < length:
                            pos += 2
                        else:
                            pos += 1

                    # 检查未闭合
                    if pos >= length:
                        raise KeiError("SyntaxError", f"未闭合的字符串: {codes[start:]}")

                    pos += 1  # 跳过结束引号
                    string = codes[start:pos]
                    tokens.append(('string', escape(string)))
                    continue

                # rf-string 或 fr-string
                if (c == 'r' and pos + 1 < length and codes[pos+1] == 'f') or \
                   (c == 'f' and pos + 1 < length and codes[pos+1] == 'r'):
                    temp_pos = pos + 2
                    while temp_pos < length and codes[temp_pos] in ' \n\t':
                        temp_pos += 1

                    if temp_pos < length and codes[temp_pos] in '"\'':
                        quote = codes[temp_pos]
                        pos = temp_pos + 1
                        start = pos
                        # rf-string: 不处理转义（原始字符串特性）
                        while pos < length and codes[pos] != quote:
                            pos += 1

                        # 检查未闭合
                        if pos >= length:
                            raise KeiError("SyntaxError", f"未闭合的rf-string: {codes[start-3:]}")

                        pos += 1
                        string = codes[start-3:pos]  # 包含 rf/fr 和引号
                        # 标记为 rfstring，既是原始字符串又支持 f-string
                        tokens.append(('rfstring', string[2:]))  # 去掉 rf/fr 和引号
                        continue

                # r-string 单行
                if c == 'r':
                    temp_pos = pos + 1
                    while temp_pos < length and codes[temp_pos] in ' \n\t':
                        temp_pos += 1

                    if temp_pos < length and codes[temp_pos] in '"\'':
                        quote = codes[temp_pos]
                        pos = temp_pos + 1
                        start = pos
                        while pos < length and codes[pos] != quote:
                            pos += 1

                        # 检查未闭合
                        if pos >= length:
                            raise KeiError("SyntaxError", f"未闭合的r-string: {codes[start-2:]}")

                        pos += 1
                        string = codes[start-2:pos]  # 包含 r 和引号
                        tokens.append(('rstring', string[1:]))  # 去掉 r" 和 "
                        continue

                # f-string 单行
                if c == 'f':
                    temp_pos = pos + 1
                    while temp_pos < length and codes[temp_pos] in ' \n\t':
                        temp_pos += 1

                    if temp_pos < length and codes[temp_pos] in '"\'':
                        quote = codes[temp_pos]
                        pos = temp_pos + 1
                        start = pos
                        while pos < length and codes[pos] != quote:
                            if codes[pos] == '\\' and pos + 1 < length:
                                pos += 2
                            else:
                                pos += 1

                        # 检查未闭合
                        if pos >= length:
                            raise KeiError("SyntaxError", f"未闭合的f-string: {codes[start-2:]}")

                        pos += 1
                        string = codes[start-2:pos]
                        tokens.append(('fstring', escape(string[1:])))
                        continue

                # 检查 .. 操作符
                if c == '.' and pos + 1 < length and codes[pos+1] == '.':
                    tokens.append("..")
                    pos += 2
                    continue

                if c == ".":
                    tokens.append(".")
                    pos += 1
                    continue

                if c == '/' and pos + 1 < length and codes[pos+1] == '/':
                    tokens.append("//")
                    pos += 2
                    continue

                if c == "#":
                    tokens.append("#")
                    break

                if c == "-" and pos + 1 < length and codes[pos+1] == ">":
                    tokens.append("->")
                    pos += 2
                    continue

                # 处理数字
                if "0" <= c <= "9":
                    start = pos
                    has_dot = False
                    while pos < length:
                        if "0" <= codes[pos] <= "9" or codes[pos] == "_":
                            pos += 1
                        elif codes[pos] == "." and not has_dot:
                            if pos + 1 < length and codes[pos+1] == '.':
                                break
                            has_dot = True
                            pos += 1
                        else:
                            break
                    number = codes[start:pos]
                    tokens.append(number)
                    continue

                # 检查比较运算符
                if c in "<>!" and pos + 1 < length and codes[pos+1] == "=":
                    tokens.append(c + "=")
                    pos += 2
                    continue

                if c == "=" and pos + 1 < length and codes[pos+1] == "=":
                    tokens.append("==")
                    pos += 2
                    continue

                # 基本运算符
                if c == "+":
                    tokens.append("+")
                    pos += 1
                    continue
                if c == "-":
                    tokens.append("-")
                    pos += 1
                    continue
                if c == "*":
                    tokens.append("*")
                    pos += 1
                    continue
                if c == "/":
                    tokens.append("/")
                    pos += 1
                    continue
                if c == '%':
                    tokens.append("%")
                    pos += 1
                    continue
                if c == '=':
                    tokens.append("=")
                    pos += 1
                    continue

                # 标识符
                if c.isalpha() or c == '_':
                    start = pos
                    while pos < length and (codes[pos].isalnum() or codes[pos] == '_'):
                        pos += 1
                    word = codes[start:pos]
                    tokens.append(word)
                    continue

                # 空白字符
                if c in ' \n\t':
                    pos += 1
                    continue

                # 其他单个字符
                tokens.append(c)
                pos += 1

            if tokens:
                result.append(tokens)

            i += 1

        return result

    except KeiError as e:
        error(e.types, e.value, [], __kei__.code[i] if __kei__.code else "未知行", i, __kei__.file)
        sys.exit(1)

def ast(tokenlines: list) -> list:
    global mapping

    result     = []
    linetokens = []
    line_num   = 0

    for tok in tokenlines:
        for t in tok:
            linetokens.append((t, line_num))

        line_num += 1

    tokens = [i[0] for i in linetokens]

    pos = 0
    length = len(tokens)
    while pos < length:
        thetoken = tokens[pos]

        if isinstance(thetoken, tuple) and thetoken[0] == 'rfstring':
            result.append({"type":"str", "mark": "f", "value":thetoken[1][1:-1], 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if isinstance(thetoken, tuple) and thetoken[0] == 'fstring':
            result.append({"type":"str", "value":thetoken[1][1:-1], "mark": "f", 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if isinstance(thetoken, tuple) and thetoken[0] == 'rstring':
            result.append({"type":"str", "value":thetoken[1][1:-1], 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if isinstance(thetoken, tuple) and thetoken[0] == 'string':
            result.append({"type":"str", "value":thetoken[1][1:-1], 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken in {"++", "--"}:
            result.append({"type":"op", "value":thetoken, 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken == "!":
            result.append({"type":"op", "value":"!", 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken == "...":
            result.append({"type":"name", "value":"...", 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken == "->":
            result.append({"type":"op", "value":"->", 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken == "?":
            result.append({"type":"op", "value":"?"})
            pos += 1
            continue

        if thetoken == "??":
            result.append({"type":"op", "value":"??"})
            pos += 1
            continue

        if thetoken in {"+=", "-=", "*=", "/="}:
            result.append({"type":"op", "value":thetoken, 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken == "=":
            result.append({"type":"op", "value":"=", 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken == "**":
            result.append({"type":"op", "value":"**", 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken == "=>":
            result.append({"type":"symbol", "value":"=>", 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken == "@":
            result.append({"type":"op", "value":"@", 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken == ",":
            result.append({"type": "symbol", "value": ",", 'linenum':linetokens[pos][1]})
            pos += 1
            continue
        if thetoken == "..":
            result.append({"type":"op","value":"..", 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken in {"or", "and", "not"}:
            result.append({"type":"op","value":thetoken, 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken in {"(", ")", "[", "]", "{", "}"}:
            result.append({"type":"symbol","value":thetoken, 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken in {"<", ">", "<=", ">=", "==", "!="}:
            result.append({"type":"op","value":thetoken, 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken in {"true", "false"}:
            result.append({"type":"bool","value":thetoken, 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken in {"null"}:
            result.append({"type":"null","value":None, 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken == "is":
            result.append({"type":"op","value":"is", 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken == "in":
            result.append({"type":"op","value":"in", 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken == ":":
            result.append({"type":"symbol","value":":", 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken == ";":
            result.append({"type":"op","value":";", 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken == '.':
            result.append({"type":"symbol","value":".", 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken in {"+", "-", "*", "/", "//", "%", "|"}:
            result.append({"type":"op","value":thetoken, 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if thetoken == "#":
            pos += 1
            continue

        if thetoken == "$":
            try:
                end = tokens.index(';', pos)
                if "=" in tokens[pos+1: end]:
                    new    = ""
                    old    = ""
                    sta    = False
                    newpos = 1
                    for t in tokens[pos+1:]:
                        newpos += 1
                        if t == ";":
                            break
                        if t == "=":
                            sta = True
                            continue
                        if sta:
                            old += t
                        else:
                            new += t

                    pos += newpos

                    mapping.update({new:old})
                else:
                    newpos = 1
                    filename = ""
                    for t in tokens[pos+1:]:
                        newpos += 1
                        if t == ";":
                            break

                        filename += t

                    filename = filename.replace(".", "/")
                    filename += ".json"

                    if os.path.isfile(filename):
                        with open(filename, "r", encoding="utf-8") as f:
                            import json
                            mapping.update(json.load(f))
                    else:
                        print(f"mapping加载时未找到文件: {filename}")

                    pos += newpos

            except:
                raise KeiError("SyntaxError", "缺少分号")

            continue

        try:
            if not isinstance(thetoken, tuple):
                int(thetoken)
                intfloat = "int"
        except:
            try:
                if not isinstance(thetoken, tuple):
                    float(thetoken)
                    intfloat = "float"
            except:
                intfloat = False

        if intfloat:
            result.append({"type":intfloat,"value":thetoken, 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        result.append({"type":"name", "value":thetoken, 'linenum':linetokens[pos][1]})
        pos += 1

    new = []
    if mapping is not None:
        for i in result:
            # 复制一份，避免修改原对象
            new_token = i.copy()

            if new_token['type'] in {'name', 'op', 'symbol'}:
                if new_token['value'] in mapping:
                    map_val = mapping[new_token['value']]
                    new_token['value'] = map_val

            new.append(new_token)

        result = new

    new = [[]]
    pos = 0

    while pos < len(result):
        if result[pos]["type"] == "op" and result[pos]["value"] == ";":
            if pos < len(result)-1:
                new.append([])
            pos += 1
            continue

        new[-1].append(result[pos])
        pos += 1

    nodes = []
    linepos = 0
    while linepos < len(new):
        line = new[linepos]
        pos = 0
        while pos < len(line):
            node, new_pos, new_linepos = parse_stmt(line, pos, new, linepos)

            if node:
                nodes.append(node)
            if new_linepos > linepos and new_linepos < len(new):
                linepos = new_linepos
                line = new[linepos]
            pos = new_pos
            if new_pos == pos and pos < len(line):
                pos += 1
        linepos += 1

    nodes = [node for node in nodes if node is not None]
    return nodes

def process_fstring(template, env):
    result = []
    i = 0
    length = len(template)
    brack = 0

    while i < length:
        if template[i] == '{' and i + 1 < length:
            if template[i+1] == '{':
                result.append('{')
                i += 2
            else:
                brack += 1

                j = i + 1
                while j < length and template[j] != '}':
                    j += 1

                if j < length:
                    brack -= 1
                    expr = template[i+1:j]

                    expr_tokens = token(expr)
                    expr_ast = ast(expr_tokens)[0]
                    try: del expr_ast['source']
                    except: pass
                    try: del expr_ast['linenum']
                    except: pass

                    value, _ = runtoken(expr_ast, env)
                    result.append(content(value))

                    i = j + 1
                else:
                    result.append(template[i])
                    i += 1

        elif template[i] == '}' and i + 1 < length and template[i+1] == '}':
            result.append('}')
            i += 2
        else:
            result.append(template[i])
            i += 1

    if brack != 0:
        raise KeiError("SyntaxError", "f-string的大括号不匹配")

    return ''.join(result)

def parse_stmt(tokens: list, pos: int, all_lines: list|None=None, linepos: int=-1) -> tuple:
    """解析语句，返回 (node, new_pos, new_linepos)"""
    debug_print(f"parse_stmt: pos={pos}, linepos={linepos}, token={tokens[pos] if pos < len(tokens) else 'EOF'}")

    globals()['all_lines'] = all_lines
    globals()['pos']       = pos
    globals()['linepos']   = linepos
    globals()['source']    = __kei__.get('code', '未知行')[tokens[pos]['linenum']]
    globals()['linenum']   = tokens[pos]['linenum']

    code = __kei__.get('code', '未知行')[tokens[pos]['linenum']]

    try:
        def stmt():
            all_lines = globals()['all_lines']
            pos       = globals()['pos']
            linepos   = globals()['linepos']

            if all_lines is None:
                all_lines = [tokens]
                linepos = 0

            if pos >= len(tokens):
                return None, pos, linepos

            t = tokens[pos]

            # 如果是 }，返回 None
            if t['type'] == 'symbol' and t['value'] == '}':
                debug_print(f"parse_stmt: found '}}' at pos {pos}, returning None")
                return None, pos, linepos

            # 处理装饰器 @
            if t['type'] == 'op' and t['value'] == '@':
                decorators = []
                current_line = linepos
                current_pos = pos

                # 收集所有装饰器
                while current_line < len(all_lines) and current_pos < len(all_lines[current_line]):
                    toke = all_lines[current_line][current_pos]
                    if toke['type'] == 'op' and toke['value'] == '@':
                        current_pos += 1

                        if current_pos >= len(all_lines[current_line]):
                            current_line += 1
                            current_pos = 0
                            if current_line >= len(all_lines):
                                raise KeiError("SyntaxError", "装饰器后面缺少表达式")
                            continue

                        decorator, new_pos, new_line = parse_expr(all_lines[current_line], current_pos, all_lines=all_lines, linepos=current_line)
                        decorators.append(decorator)

                        if new_pos < len(all_lines[current_line]):
                            current_pos = new_pos
                        else:
                            current_line += 1
                            current_pos = 0

                        while current_line < len(all_lines) and current_pos < len(all_lines[current_line]) and \
                              all_lines[current_line][current_pos]['type'] == 'op' and \
                              all_lines[current_line][current_pos]['value'] == ';':
                            current_pos += 1
                            if current_pos >= len(all_lines[current_line]):
                                current_line += 1
                                current_pos = 0
                    else:
                        break

                if current_line >= len(all_lines):
                    raise KeiError("SyntaxError", "装饰器后面缺少函数定义")

                stmt_node, new_pos, new_line = parse_stmt(all_lines[current_line], current_pos, all_lines, current_line)

                if stmt_node and stmt_node['type'] == 'function':
                    stmt_node['decorators'] = decorators
                    return stmt_node, new_pos, new_line
                else:
                    raise KeiError("SyntaxError", "装饰器只能用于函数")

            # 处理 try 语句
            if t['type'] == 'name' and t['value'] == 'try':
                pos += 1

                if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != '{':
                    raise KeiError("SyntaxError", "try 后面需要 '{'")
                pos += 1

                try_body = []
                brace_count = 1
                current_line = linepos
                current_pos = pos

                while brace_count > 0:
                    if current_line >= len(all_lines):
                        break
                    if current_pos >= len(all_lines[current_line]):
                        current_line += 1
                        current_pos = 0
                        continue

                    current_tokens = all_lines[current_line]

                    if current_tokens[current_pos]["type"] == "symbol" and current_tokens[current_pos]["value"] == "}":
                        brace_count -= 1
                        current_pos += 1
                        if brace_count == 0:
                            break
                        continue

                    stmt_node, new_pos, new_line = parse_stmt(current_tokens, current_pos, all_lines, current_line)
                    if stmt_node:
                        try_body.append(stmt_node)

                    if new_line > current_line:
                        current_line = new_line
                        current_pos = new_pos
                    else:
                        current_pos = new_pos
                        if new_pos == current_pos:
                            current_pos += 1

                # 解析 catch
                var = None
                catchbody = None
                current_line = current_line
                current_pos = current_pos

                if current_line < len(all_lines) and current_pos < len(all_lines[current_line]):
                    next_token = all_lines[current_line][current_pos]
                    if next_token['type'] == 'name' and next_token['value'] == 'catch':
                        current_pos += 1

                        if current_pos < len(all_lines[current_line]) and all_lines[current_line][current_pos]['type'] == 'name':
                            var = all_lines[current_line][current_pos]['value']
                            current_pos += 1

                        if current_pos >= len(all_lines[current_line]) or all_lines[current_line][current_pos]['type'] != 'symbol' or all_lines[current_line][current_pos]['value'] != '{':
                            raise KeiError("SyntaxError", "catch 后面需要 '{'")
                        current_pos += 1

                        catchbody = []
                        brace_count = 1
                        catch_line = current_line
                        catch_pos = current_pos

                        while brace_count > 0:
                            if catch_line >= len(all_lines):
                                break
                            if catch_pos >= len(all_lines[catch_line]):
                                catch_line += 1
                                catch_pos = 0
                                continue

                            catch_tokens = all_lines[catch_line]

                            if catch_tokens[catch_pos]["type"] == "symbol" and catch_tokens[catch_pos]["value"] == "}":
                                brace_count -= 1
                                catch_pos += 1
                                if brace_count == 0:
                                    current_line = catch_line
                                    current_pos = catch_pos
                                    break
                                continue

                            stmt_node, new_pos, new_line = parse_stmt(catch_tokens, catch_pos, all_lines, catch_line)
                            if stmt_node:
                                catchbody.append(stmt_node)

                            if new_line > catch_line:
                                catch_line = new_line
                                catch_pos = new_pos
                            else:
                                catch_pos = new_pos
                                if new_pos == catch_pos:
                                    catch_pos += 1

                # 解析 finally
                finallybody = None
                if current_line < len(all_lines) and current_pos < len(all_lines[current_line]):
                    next_token = all_lines[current_line][current_pos]
                    if next_token['type'] == 'name' and next_token['value'] == 'finally':
                        current_pos += 1

                        if current_pos >= len(all_lines[current_line]) or all_lines[current_line][current_pos]['type'] != 'symbol' or all_lines[current_line][current_pos]['value'] != '{':
                            raise KeiError("SyntaxError", "finally 后面需要 '{'")
                        current_pos += 1

                        finallybody = []
                        brace_count = 1
                        finally_line = current_line
                        finally_pos = current_pos

                        while brace_count > 0:
                            if finally_line >= len(all_lines):
                                break
                            if finally_pos >= len(all_lines[finally_line]):
                                finally_line += 1
                                finally_pos = 0
                                continue

                            finally_tokens = all_lines[finally_line]

                            if finally_tokens[finally_pos]["type"] == "symbol" and finally_tokens[finally_pos]["value"] == "}":
                                brace_count -= 1
                                finally_pos += 1
                                if brace_count == 0:
                                    current_line = finally_line
                                    current_pos = finally_pos
                                    break
                                continue

                            stmt_node, new_pos, new_line = parse_stmt(finally_tokens, finally_pos, all_lines, finally_line)
                            if stmt_node:
                                finallybody.append(stmt_node)

                            if new_line > finally_line:
                                finally_line = new_line
                                finally_pos = new_pos
                            else:
                                finally_pos = new_pos
                                if new_pos == finally_pos:
                                    finally_pos += 1

                node = {
                    'type': 'try',
                    'body': try_body,
                    'var': var,
                    'catchbody': catchbody,
                    'finallybody': finallybody
                }
                return node, current_pos, current_line

            # 处理 class 语句
            if t['type'] == 'name' and t['value'] == 'class':
                pos += 1

                if pos >= len(tokens) or tokens[pos]['type'] != 'name':
                    raise KeiError("SyntaxError", "类需要名字")
                class_name = tokens[pos]['value']
                if class_name in keywords:
                    raise KeiError("SyntaxError", f"无法使用关键字 '{class_name}' 作为类名")
                pos += 1

                parent_class = None
                if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '(':
                    pos += 1
                    if pos < len(tokens) and tokens[pos]['type'] == 'name':
                        parent_class = tokens[pos]['value']
                        pos += 1
                        if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != ')':
                            raise KeiError("SyntaxError", "继承语法错误：缺少 ')'")
                        pos += 1
                    else:
                        raise KeiError("SyntaxError", "继承需要父类名")

                if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != '{':
                    raise KeiError("SyntaxError", "class 后面缺少 {")
                pos += 1

                body = []
                brace_count = 1
                current_line = linepos
                current_pos = pos

                while brace_count > 0:
                    if current_line >= len(all_lines):
                        break
                    if current_pos >= len(all_lines[current_line]):
                        current_line += 1
                        current_pos = 0
                        continue

                    current_tokens = all_lines[current_line]

                    if current_tokens[current_pos]["type"] == "symbol" and current_tokens[current_pos]["value"] == "}":
                        brace_count -= 1
                        current_pos += 1
                        if brace_count == 0:
                            break
                        continue

                    stmt_node, new_pos, new_line = parse_stmt(current_tokens, current_pos, all_lines, current_line)
                    if stmt_node:
                        body.append(stmt_node)

                    if new_line > current_line:
                        current_line = new_line
                        current_pos = new_pos
                    else:
                        current_pos = new_pos
                        if new_pos == current_pos:
                            current_pos += 1

                node = {
                    'type': 'class',
                    'name': class_name,
                    'parent': parent_class,
                    'body': body,
                }
                return node, current_pos, current_line

            # 处理 for 语句
            if t['type'] == 'name' and t['value'] == 'for':
                pos += 1

                vars = []
                if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '(':
                    pos += 1
                    while pos < len(tokens):
                        if tokens[pos]['type'] == 'name':
                            vars.append(tokens[pos]['value'])
                            pos += 1
                        if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
                            pos += 1
                            continue
                        if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ')':
                            pos += 1
                            break
                else:
                    first_var = None
                    if pos < len(tokens) and tokens[pos]['type'] == 'name':
                        first_var = tokens[pos]['value']
                        pos += 1

                    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
                        vars.append(first_var)
                        pos += 1

                        if pos < len(tokens) and tokens[pos]['type'] == 'name':
                            vars.append(tokens[pos]['value'])
                            pos += 1

                        while pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
                            pos += 1
                            if pos < len(tokens) and tokens[pos]['type'] == 'name':
                                vars.append(tokens[pos]['value'])
                                pos += 1
                            else:
                                break
                    elif first_var:
                        vars = [first_var]
                    else:
                        raise KeiError("SyntaxError", "for 循环需要变量名")

                if pos >= len(tokens) or tokens[pos]['type'] != 'op' or tokens[pos]['value'] != 'in':
                    raise KeiError("SyntaxError", "for 需要 'in'")
                pos += 1

                iterable, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)

                if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != '{':
                    raise KeiError("SyntaxError", "for 后面需要 '{'")
                pos += 1

                body = []
                brace_count = 1
                current_line = linepos
                current_pos = pos

                while brace_count > 0:
                    if current_line >= len(all_lines):
                        break
                    if current_pos >= len(all_lines[current_line]):
                        current_line += 1
                        current_pos = 0
                        continue

                    current_tokens = all_lines[current_line]

                    if current_tokens[current_pos]["type"] == "symbol" and current_tokens[current_pos]["value"] == "}":
                        brace_count -= 1
                        current_pos += 1
                        if brace_count == 0:
                            break
                        continue

                    stmt_node, new_pos, new_line = parse_stmt(current_tokens, current_pos, all_lines, current_line)
                    if stmt_node:
                        body.append(stmt_node)

                    if new_line > current_line:
                        current_line = new_line
                        current_pos = new_pos
                    else:
                        current_pos = new_pos
                        if new_pos == current_pos:
                            current_pos += 1

                node = {
                    'type': 'for',
                    'vars': vars,
                    'iterable': iterable,
                    'body': body
                }
                return node, current_pos, current_line

            # 处理 fn 语句（函数定义）
            if t['type'] == 'name' and t['value'] == 'fn':
                hint = None
                pos += 1

                if pos >= len(tokens) or tokens[pos]['type'] != 'name':
                    raise KeiError("SyntaxError", "函数定义需要名字")
                func_name = tokens[pos]['value']
                if func_name in keywords:
                    raise KeiError("SyntaxError", f"无法使用关键字 '{func_name}' 作为函数名")
                pos += 1

                __kei__.stack.append(func_name)

                try:
                    if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != '(':
                        raise KeiError("SyntaxError", "期待 (")
                    pos += 1

                    params = []
                    defaults = {}

                    while pos < len(tokens) and not (tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ')'):
                        if tokens[pos]['type'] == 'name':
                            param_name = tokens[pos]['value']
                            pos += 1

                            if pos < len(tokens) and tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '=':
                                pos += 1
                                default_val, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)
                                defaults[param_name] = default_val

                            params.append(param_name)
                            continue

                        elif tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '*':
                            pos += 1
                            if pos < len(tokens) and tokens[pos]['type'] == 'name':
                                params.append('*' + tokens[pos]['value'])
                                pos += 1
                            else:
                                params.append('*')
                            continue

                        elif tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '**':
                            pos += 1
                            if pos < len(tokens) and tokens[pos]['type'] == 'name':
                                params.append('**' + tokens[pos]['value'])
                                pos += 1
                            else:
                                params.append('**')
                            continue

                        elif tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
                            pos += 1
                            continue
                        else:
                            raise KeiError("SyntaxError", f"未知的符号: \"{tokens[pos]['value']}\"")

                    pos += 1  # 跳过 )

                    if pos < len(tokens) and tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '->':
                        pos += 1
                        expr, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)
                        hint = expr

                    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '=>':
                        pos += 1
                        expr, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)
                        body = [{'type': 'return', 'value': expr}]
                        __kei__.stack.pop()
                        node = {
                            'type': 'function',
                            'name': func_name,
                            'params': params,
                            'defaults': defaults,
                            'body': body,
                            'hint': hint
                        }
                        return node, pos, linepos

                    if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != '{':
                        raise KeiError("SyntaxError", "期待 {")

                except:
                    __kei__.stack.pop()
                    raise

                try:
                    pos += 1
                    body = []
                    brace_count = 1
                    current_line = linepos
                    current_pos = pos

                    while brace_count > 0:
                        if current_line >= len(all_lines):
                            break
                        if current_pos >= len(all_lines[current_line]):
                            current_line += 1
                            current_pos = 0
                            continue

                        current_tokens = all_lines[current_line]

                        if current_tokens[current_pos]["type"] == "symbol" and current_tokens[current_pos]["value"] == "}":
                            brace_count -= 1
                            current_pos += 1
                            if brace_count == 0:
                                break
                            continue

                        stmt_node, new_pos, new_line = parse_stmt(current_tokens, current_pos, all_lines, current_line)
                        if stmt_node:
                            body.append(stmt_node)

                        if new_line > current_line:
                            current_line = new_line
                            current_pos = new_pos
                        else:
                            current_pos = new_pos
                            if new_pos == current_pos:
                                current_pos += 1

                    __kei__.stack.pop()
                    node = {
                        'type': 'function',
                        'name': func_name,
                        'params': params,
                        'defaults': defaults,
                        'body': body,
                        'hint': hint
                    }
                    return node, current_pos, current_line
                except:
                    raise

            # 处理 import 语句
            if t['type'] == 'name' and t['value'] == 'import':
                sentencename = t['value']
                pos += 1
                modules = []

                while pos < len(tokens):
                    if tokens[pos]['type'] == 'name':
                        module_parts = [tokens[pos]['value']]
                        pos += 1

                        while (pos < len(tokens) and
                               tokens[pos].get('type') == 'symbol' and
                               tokens[pos].get('value') == '.' and
                               pos + 1 < len(tokens) and
                               tokens[pos + 1].get('type') == 'name'):
                            pos += 1
                            module_parts.append(tokens[pos]['value'])
                            pos += 1

                        module_name = '.'.join(module_parts)

                        alias = None
                        if pos < len(tokens) and tokens[pos].get('type') == 'name' and tokens[pos].get('value') == 'as':
                            pos += 1
                            if pos < len(tokens) and tokens[pos]['type'] == 'name':
                                alias = tokens[pos]['value']
                                pos += 1

                        if (pos < len(tokens) and
                            tokens[pos].get('type') == 'symbol' and tokens[pos].get('value') == '.' and
                            pos + 1 < len(tokens) and
                            tokens[pos + 1].get('type') == 'op' and tokens[pos + 1].get('value') == '*'):

                            modules.append({
                                'type': 'wildcard',
                                'module': module_name,
                                'alias': alias
                            })
                            pos += 2
                        else:
                            modules.append({
                                'type': 'normal',
                                'module': module_name,
                                'alias': alias
                            })

                    if pos < len(tokens) and tokens[pos].get('type') == 'symbol' and tokens[pos].get('value') == ',':
                        pos += 1
                    else:
                        break

                node = {'type': sentencename, 'modules': modules}
                return node, pos, linepos

            # 处理 from ... import ... 语句
            if t['type'] == 'name' and t['value'] == 'from':
                pos += 1

                if pos >= len(tokens) or tokens[pos]['type'] != 'name':
                    raise KeiError("SyntaxError", "from 后面需要模块名")

                module_parts = [tokens[pos]['value']]
                pos += 1

                while (pos < len(tokens) and
                       tokens[pos].get('type') == 'symbol' and
                       tokens[pos].get('value') == '.' and
                       pos + 1 < len(tokens) and
                       tokens[pos + 1].get('type') == 'name'):
                    pos += 1
                    module_parts.append(tokens[pos]['value'])
                    pos += 1

                module_name = '.'.join(module_parts)

                if pos >= len(tokens) or tokens[pos].get('type') != 'name' or tokens[pos].get('value') != 'import':
                    raise KeiError("SyntaxError", "from ... 后面需要 import")
                pos += 1

                imports = []

                if pos < len(tokens) and tokens[pos].get('type') == 'op' and tokens[pos].get('value') == '*':
                    imports.append({
                        'type': 'wildcard',
                        'name': None,
                        'alias': None
                    })
                    pos += 1
                else:
                    while pos < len(tokens):
                        if tokens[pos]['type'] == 'name':
                            name = tokens[pos]['value']
                            pos += 1

                            alias = None
                            if pos < len(tokens) and tokens[pos].get('type') == 'name' and tokens[pos].get('value') == 'as':
                                pos += 1
                                if pos < len(tokens) and tokens[pos]['type'] == 'name':
                                    alias = tokens[pos]['value']
                                    pos += 1

                            imports.append({
                                'type': 'normal',
                                'name': name,
                                'alias': alias
                            })

                            if pos < len(tokens) and tokens[pos].get('type') == 'symbol' and tokens[pos].get('value') == ',':
                                pos += 1
                                continue
                            else:
                                break
                        else:
                            break

                node = {'type': 'fromimport', 'module': module_name, 'imports': imports}
                return node, pos, linepos

            # 处理 break/continue
            if t['type'] == 'name' and t['value'] in {'break', 'continue'}:
                stmt_type = t['value']
                pos += 1
                if pos < len(tokens) and tokens[pos].get('type') == 'op' and tokens[pos].get('value') == ';':
                    pos += 1
                node = {'type': stmt_type}
                return node, pos, linepos

            # 处理 return 语句
            if t['type'] == 'name' and t['value'] == 'return':
                pos += 1
                if pos >= len(tokens) or (tokens[pos]['type'] == 'op' and tokens[pos]['value'] == ';'):
                    node = {'type': 'return', 'value': None}
                    return node, pos, linepos

                first, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)
                values = [first]
                while pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
                    pos += 1
                    next_val, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)
                    values.append(next_val)

                if len(values) == 1:
                    node = {'type': 'return', 'value': values[0]}
                else:
                    node = {'type': 'return', 'value': {'type': 'list', 'elements': values}}
                return node, pos, linepos

            # 处理 with 语句
            if t['type'] == 'name' and t['value'] == 'with':
                pos += 1
                expr, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)

                as_var = None
                if pos < len(tokens) and tokens[pos]['type'] == 'name' and tokens[pos]['value'] == 'as':
                    pos += 1
                    if pos >= len(tokens) or tokens[pos]['type'] != 'name':
                        raise KeiError("SyntaxError", "as 后面需要变量名")
                    as_var = tokens[pos]['value']
                    pos += 1

                if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != '{':
                    raise KeiError("SyntaxError", "with 后面需要 {")
                pos += 1

                body = []
                brace_count = 1
                current_line = linepos
                current_pos = pos

                while brace_count > 0:
                    if current_line >= len(all_lines):
                        break
                    if current_pos >= len(all_lines[current_line]):
                        current_line += 1
                        current_pos = 0
                        continue

                    current_tokens = all_lines[current_line]

                    if current_tokens[current_pos]["type"] == "symbol" and current_tokens[current_pos]["value"] == "}":
                        brace_count -= 1
                        current_pos += 1
                        if brace_count == 0:
                            break
                        continue

                    stmt_node, new_pos, new_line = parse_stmt(current_tokens, current_pos, all_lines, current_line)
                    if stmt_node:
                        body.append(stmt_node)

                    if new_line > current_line:
                        current_line = new_line
                        current_pos = new_pos
                    else:
                        current_pos = new_pos
                        if new_pos == current_pos:
                            current_pos += 1

                node = {
                    'type': 'with',
                    'expr': expr,
                    'as_var': as_var,
                    'body': body
                }
                return node, current_pos, current_line

            # 处理 namespace 语句
            if t['type'] == 'name' and t['value'] == 'namespace':
                pos += 1

                if pos >= len(tokens) or tokens[pos]['type'] != 'name':
                    raise KeiError("SyntaxError", "命名空间需要名字")
                ns_name = tokens[pos]['value']
                if ns_name in keywords:
                    raise KeiError("SyntaxError", f"无法使用关键字 '{ns_name}' 作为命名空间名")
                pos += 1

                if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != '{':
                    raise KeiError("SyntaxError", "namespace 后面缺少 {")
                pos += 1

                body = []
                brace_count = 1
                current_line = linepos
                current_pos = pos

                while brace_count > 0:
                    if current_line >= len(all_lines):
                        break
                    if current_pos >= len(all_lines[current_line]):
                        current_line += 1
                        current_pos = 0
                        continue

                    current_tokens = all_lines[current_line]

                    if current_tokens[current_pos]["type"] == "symbol" and current_tokens[current_pos]["value"] == "}":
                        brace_count -= 1
                        current_pos += 1
                        if brace_count == 0:
                            break
                        continue

                    stmt_node, new_pos, new_line = parse_stmt(current_tokens, current_pos, all_lines, current_line)
                    if stmt_node:
                        body.append(stmt_node)

                    if new_line > current_line:
                        current_line = new_line
                        current_pos = new_pos
                    else:
                        current_pos = new_pos
                        if new_pos == current_pos:
                            current_pos += 1

                node = {
                    'type': 'namespace',
                    'name': ns_name,
                    'body': body
                }
                return node, current_pos, current_line

            # 处理 global/del/raise/use
            if t['type'] == 'name' and t['value'] in {'global', 'del', 'raise', 'use'}:
                sentencename = t['value']
                pos += 1
                targets = []

                while pos < len(tokens):
                    target, new_pos, linepos = parse_expr(tokens, pos, allow_assign=True, all_lines=all_lines, linepos=linepos)
                    if target:
                        targets.append(target)
                        pos = new_pos

                    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
                        pos += 1
                        continue
                    else:
                        break

                if not targets and sentencename != "raise":
                    raise KeiError("SyntaxError", f"{sentencename} 需要至少一个参数")

                if len(targets) > 2 and sentencename == "raise":
                    raise KeiError("SyntaxError", "raise 只能抛出一个错误字符串和可选类型")

                node = {'type': sentencename, 'names': targets}
                return node, pos, linepos

            # 处理 if/while/unless/until
            if t['type'] == 'name' and t['value'] in {'if', 'while', 'unless', 'until'}:
                sentencename = t['value']
                pos += 1
                cond, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)

                if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != '{':
                    raise KeiError("SyntaxError", f"{sentencename} 后面缺少 {{")
                pos += 1

                body = []
                brace_count = 1
                current_line = linepos
                current_pos = pos

                while brace_count > 0:
                    if current_line >= len(all_lines):
                        break
                    if current_pos >= len(all_lines[current_line]):
                        current_line += 1
                        current_pos = 0
                        continue

                    current_tokens = all_lines[current_line]

                    if current_tokens[current_pos]["type"] == "symbol" and current_tokens[current_pos]["value"] == "}":
                        brace_count -= 1
                        current_pos += 1
                        if brace_count == 0:
                            break
                        continue

                    stmt_node, new_pos, new_line = parse_stmt(current_tokens, current_pos, all_lines, current_line)
                    if stmt_node:
                        body.append(stmt_node)

                    if new_line > current_line:
                        current_line = new_line
                        current_pos = new_pos
                    else:
                        current_pos = new_pos
                        if new_pos == current_pos:
                            current_pos += 1

                if sentencename in {'if', 'unless'}:
                    elif_chain = []
                    else_body = None
                    current_line = current_line
                    current_pos = current_pos

                    while current_line < len(all_lines) and current_pos < len(all_lines[current_line]):
                        while current_pos < len(all_lines[current_line]) and all_lines[current_line][current_pos]['type'] == 'op' and all_lines[current_line][current_pos]['value'] == ';':
                            current_pos += 1
                        if current_pos >= len(all_lines[current_line]):
                            current_line += 1
                            current_pos = 0
                            if current_line >= len(all_lines):
                                break
                            continue

                        next_token = all_lines[current_line][current_pos]

                        if next_token['type'] == 'name' and next_token['value'] == 'elif':
                            current_pos += 1
                            elif_cond, current_pos, linepos = parse_expr(all_lines[current_line], current_pos, all_lines=all_lines, linepos=linepos)

                            if current_pos >= len(all_lines[current_line]) or all_lines[current_line][current_pos]['type'] != 'symbol' or all_lines[current_line][current_pos]['value'] != '{':
                                raise KeiError("SyntaxError", "elif 后面缺少 {")
                            current_pos += 1

                            elif_body = []
                            elif_line = current_line
                            elif_pos = current_pos
                            elif_brace_count = 1

                            while elif_brace_count > 0:
                                if elif_line >= len(all_lines):
                                    break
                                if elif_pos >= len(all_lines[elif_line]):
                                    elif_line += 1
                                    elif_pos = 0
                                    continue

                                elif_tokens = all_lines[elif_line]

                                if elif_tokens[elif_pos]["type"] == "symbol" and elif_tokens[elif_pos]["value"] == "}":
                                    elif_brace_count -= 1
                                    elif_pos += 1
                                    if elif_brace_count == 0:
                                        current_line = elif_line
                                        current_pos = elif_pos
                                        break
                                    continue

                                stmt_node, new_pos, new_line = parse_stmt(elif_tokens, elif_pos, all_lines, elif_line)
                                if stmt_node:
                                    elif_body.append(stmt_node)

                                if new_line > elif_line:
                                    elif_line = new_line
                                    elif_pos = new_pos
                                else:
                                    elif_pos = new_pos
                                    if new_pos == elif_pos:
                                        elif_pos += 1

                            elif_chain.append({
                                'cond': elif_cond,
                                'body': elif_body
                            })

                        elif next_token['type'] == 'name' and next_token['value'] == 'else':
                            current_pos += 1

                            if current_pos >= len(all_lines[current_line]) or all_lines[current_line][current_pos]['type'] != 'symbol' or all_lines[current_line][current_pos]['value'] != '{':
                                raise KeiError("SyntaxError", "else 后面缺少 {")
                            current_pos += 1

                            else_body = []
                            else_line = current_line
                            else_pos = current_pos
                            else_brace_count = 1

                            while else_brace_count > 0:
                                if else_line >= len(all_lines):
                                    break
                                if else_pos >= len(all_lines[else_line]):
                                    else_line += 1
                                    else_pos = 0
                                    continue

                                else_tokens = all_lines[else_line]

                                if else_tokens[else_pos]["type"] == "symbol" and else_tokens[else_pos]["value"] == "}":
                                    else_brace_count -= 1
                                    else_pos += 1
                                    if else_brace_count == 0:
                                        current_line = else_line
                                        current_pos = else_pos
                                        break
                                    continue

                                stmt_node, new_pos, new_line = parse_stmt(else_tokens, else_pos, all_lines, else_line)
                                if stmt_node:
                                    else_body.append(stmt_node)

                                if new_line > else_line:
                                    else_line = new_line
                                    else_pos = new_pos
                                else:
                                    else_pos = new_pos
                                    if new_pos == else_pos:
                                        else_pos += 1
                            break

                        else:
                            break

                    node = {
                        'type': sentencename,
                        'cond': cond,
                        'body': body,
                        'elif_chain': elif_chain,
                        'else_body': else_body
                    }
                    return node, current_pos, current_line
                else:
                    node = {
                        'type': sentencename,
                        'cond': cond,
                        'body': body
                    }
                    return node, current_pos, current_line

            # 处理 match 语句
            if t['type'] == 'name' and t['value'] == 'match':
                pos += 1
                value_expr, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)

                if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != '{':
                    raise KeiError("SyntaxError", "match 后面需要 {")
                pos += 1

                arms = []
                current_line = linepos
                current_pos = pos

                while True:
                    while current_line < len(all_lines) and current_pos < len(all_lines[current_line]):
                        if all_lines[current_line][current_pos]['type'] == 'op' and all_lines[current_line][current_pos]['value'] == ';':
                            current_pos += 1
                        else:
                            break
                    if current_pos >= len(all_lines[current_line]):
                        current_line += 1
                        current_pos = 0
                        if current_line >= len(all_lines):
                            break
                        continue

                    if all_lines[current_line][current_pos]['type'] == 'name' and all_lines[current_line][current_pos]['value'] == 'case':
                        current_pos += 1
                        patterns = []
                        pattern, current_pos, linepos = parse_match_pattern(all_lines[current_line], current_pos, all_lines, linepos)
                        patterns.append(pattern)
                        while current_pos < len(all_lines[current_line]):
                            if (all_lines[current_line][current_pos]['type'] == 'op' and
                                all_lines[current_line][current_pos]['value'] == '|'):
                                current_pos += 1
                                pattern, current_pos, linepos = parse_match_pattern(all_lines[current_line], current_pos, all_lines, linepos)
                                patterns.append(pattern)
                            else:
                                break

                        if current_pos >= len(all_lines[current_line]) or all_lines[current_line][current_pos]['type'] != 'symbol' or all_lines[current_line][current_pos]['value'] != '{':
                            raise KeiError("SyntaxError", "case 后面需要 {")
                        current_pos += 1

                        body = []
                        brace_count = 1
                        case_line = current_line
                        case_pos = current_pos

                        while brace_count > 0:
                            if case_line >= len(all_lines):
                                break
                            if case_pos >= len(all_lines[case_line]):
                                case_line += 1
                                case_pos = 0
                                continue

                            case_tokens = all_lines[case_line]

                            if case_tokens[case_pos]['type'] == 'symbol' and case_tokens[case_pos]['value'] == '}':
                                brace_count -= 1
                                case_pos += 1
                                if brace_count == 0:
                                    current_line = case_line
                                    current_pos = case_pos
                                    break
                                continue

                            stmt_node, new_pos, new_line = parse_stmt(case_tokens, case_pos, all_lines, case_line)
                            if stmt_node:
                                body.append(stmt_node)

                            if new_line > case_line:
                                case_line = new_line
                                case_pos = new_pos
                            else:
                                case_pos = new_pos
                                if new_pos == case_pos:
                                    case_pos += 1

                        arms.append({
                            'patterns': patterns,
                            'body': body
                        })
                    else:
                        if all_lines[current_line][current_pos]['type'] == 'symbol' and all_lines[current_line][current_pos]['value'] == '}':
                            current_pos += 1
                            break
                        else:
                            raise KeiError("SyntaxError", "match 块内只能有 case 语句")

                node = {
                    'type': 'match',
                    'value': value_expr,
                    'arms': arms
                }
                return node, current_pos, current_line

            # 查找复合赋值
            compound_ops = {"+=", "-=", "*=", "/="}
            assig_pos = -1
            paren_count = 0
            bracket_count = 0
            brace_count = 0
            compound_op = None

            for i in range(pos, len(tokens)):
                toke = tokens[i]
                if toke['type'] == 'symbol':
                    if toke['value'] == '(':
                        paren_count += 1
                    elif toke['value'] == ')':
                        paren_count -= 1
                    elif toke['value'] == '[':
                        bracket_count += 1
                    elif toke['value'] == ']':
                        bracket_count -= 1
                    elif toke['value'] == '{':
                        brace_count += 1
                    elif toke['value'] == '}':
                        brace_count -= 1

                if (toke.get('type') == 'op' and toke.get('value') in compound_ops
                    and paren_count == 0 and bracket_count == 0 and brace_count == 0):
                    assig_pos = i
                    compound_op = toke.get('value')
                    break

            if assig_pos != -1 and assig_pos > pos:
                # 解析左边
                left_tokens = tokens[pos:assig_pos]

                left_comma_positions = []
                paren_count = bracket_count = brace_count = 0
                for i, tok in enumerate(left_tokens):
                    if tok['type'] == 'symbol':
                        if tok['value'] == '(':
                            paren_count += 1
                        elif tok['value'] == ')':
                            paren_count -= 1
                        elif tok['value'] == '[':
                            bracket_count += 1
                        elif tok['value'] == ']':
                            bracket_count -= 1
                        elif tok['value'] == '{':
                            brace_count += 1
                        elif tok['value'] == '}':
                            brace_count -= 1
                    if tok['type'] == 'symbol' and tok['value'] == ',' and paren_count == 0 and bracket_count == 0 and brace_count == 0:
                        left_comma_positions.append(i)

                if left_comma_positions:
                    vars_list = []
                    rest_var = None
                    kwargs_var = None
                    last_pos = 0
                    for comma_pos in left_comma_positions:
                        var_tokens = left_tokens[last_pos:comma_pos]
                        if len(var_tokens) == 2 and var_tokens[0]['type'] == 'op' and var_tokens[0]['value'] == '**':
                            if var_tokens[1]['type'] == 'name':
                                kwargs_var = var_tokens[1]['value']
                            else:
                                raise KeiError("SyntaxError", f"** 后面必须是变量名, 得到 {var_tokens[1]}")
                        elif len(var_tokens) == 2 and var_tokens[0]['type'] == 'op' and var_tokens[0]['value'] == '*':
                            if var_tokens[1]['type'] == 'name':
                                rest_var = var_tokens[1]['value']
                            else:
                                raise KeiError("SyntaxError", f"* 后面必须是变量名, 得到 {var_tokens[1]}")
                        elif len(var_tokens) == 1 and var_tokens[0]['type'] == 'name':
                            vars_list.append(var_tokens[0]['value'])
                        elif len(var_tokens) > 0:
                            raise KeiError("SyntaxError", f"多变量赋值左边必须是变量名、*rest 或 **kwargs, 得到 {var_tokens}")
                        last_pos = comma_pos + 1
                    var_tokens = left_tokens[last_pos:]
                    if len(var_tokens) == 2 and var_tokens[0]['type'] == 'op' and var_tokens[0]['value'] == '**':
                        if var_tokens[1]['type'] == 'name':
                            kwargs_var = var_tokens[1]['value']
                        else:
                            raise KeiError("SyntaxError", f"** 后面必须是变量名, 得到 {var_tokens[1]}")
                    elif len(var_tokens) == 2 and var_tokens[0]['type'] == 'op' and var_tokens[0]['value'] == '*':
                        if var_tokens[1]['type'] == 'name':
                            rest_var = var_tokens[1]['value']
                        else:
                            raise KeiError("SyntaxError", f"* 后面必须是变量名, 得到 {var_tokens[1]}")
                    elif len(var_tokens) == 1 and var_tokens[0]['type'] == 'name':
                        vars_list.append(var_tokens[0]['value'])
                    elif len(var_tokens) > 0:
                        raise KeiError("SyntaxError", f"多变量赋值左边必须是变量名、*rest 或 **kwargs, 得到 {var_tokens}")
                    left_node = {'type': 'multiassign', 'vars': vars_list, 'rest': rest_var, 'kwargs': kwargs_var}
                else:
                    left_node, left_new_pos, _ = parse_expr(left_tokens, 0, allow_assign=True, all_lines=all_lines, linepos=linepos)
                    if not left_node or left_new_pos != len(left_tokens):
                        raise KeiError("SyntaxError", f"无效的赋值左边: {left_tokens}")

                # 解析右边
                right_tokens = tokens[assig_pos + 1:]
                right_comma_positions = []
                paren_count = bracket_count = brace_count = 0
                for i, tok in enumerate(right_tokens):
                    if tok['type'] == 'symbol':
                        if tok['value'] == '(':
                            paren_count += 1
                        elif tok['value'] == ')':
                            paren_count -= 1
                        elif tok['value'] == '[':
                            bracket_count += 1
                        elif tok['value'] == ']':
                            bracket_count -= 1
                        elif tok['value'] == '{':
                            brace_count += 1
                        elif tok['value'] == '}':
                            brace_count -= 1
                    if tok['type'] == 'symbol' and tok['value'] == ',' and paren_count == 0 and bracket_count == 0 and brace_count == 0:
                        right_comma_positions.append(i)

                if right_comma_positions:
                    elements = []
                    last_pos = 0
                    for comma_pos in right_comma_positions:
                        value_tokens = right_tokens[last_pos:comma_pos]
                        if value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '[':
                            val_node, _, _ = parse_list(value_tokens, 0, all_lines, linepos)
                        elif value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '{':
                            val_node, _, _ = parse_dict(value_tokens, 0, all_lines, linepos)
                        else:
                            val_node, _, _ = parse_expr(value_tokens, 0, allow_assign=False, all_lines=all_lines, linepos=linepos)
                        if val_node:
                            elements.append(val_node)
                        last_pos = comma_pos + 1
                    value_tokens = right_tokens[last_pos:]
                    if value_tokens:
                        if value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '[':
                            val_node, _, _ = parse_list(value_tokens, 0, all_lines, linepos)
                        elif value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '{':
                            val_node, _, _ = parse_dict(value_tokens, 0, all_lines, linepos)
                        else:
                            val_node, _, _ = parse_expr(value_tokens, 0, allow_assign=False, all_lines=all_lines, linepos=linepos)
                        if val_node:
                            elements.append(val_node)
                    right_node = {'type': 'list', 'elements': elements}
                    final_pos = assig_pos + 1 + len(right_tokens)
                else:
                    if right_tokens and right_tokens[0]['type'] == 'symbol' and right_tokens[0]['value'] == '{':
                        right_node, right_new_pos, _ = parse_dict(right_tokens, 0, all_lines, linepos)
                    elif right_tokens and right_tokens[0]['type'] == 'symbol' and right_tokens[0]['value'] == '[':
                        right_node, right_new_pos, _ = parse_list(right_tokens, 0, all_lines, linepos)
                    else:
                        right_node, right_new_pos, _ = parse_expr(right_tokens, 0, allow_assign=False, all_lines=all_lines, linepos=linepos)
                    if not right_node:
                        raise KeiError("SyntaxError", "无效的赋值右边")
                    final_pos = assig_pos + 1 + right_new_pos

                node = {
                    'type': 'compound_assign',
                    'left': left_node,
                    'right': right_node,
                    'op': compound_op
                }
                return node, final_pos, linepos

            # 查找普通赋值 =
            assig_pos = -1
            paren_count = bracket_count = brace_count = 0
            for i in range(pos, len(tokens)):
                toke = tokens[i]
                if toke['type'] == 'symbol':
                    if toke['value'] == '(':
                        paren_count += 1
                    elif toke['value'] == ')':
                        paren_count -= 1
                    elif toke['value'] == '[':
                        bracket_count += 1
                    elif toke['value'] == ']':
                        bracket_count -= 1
                    elif toke['value'] == '{':
                        brace_count += 1
                    elif toke['value'] == '}':
                        brace_count -= 1

                if (toke.get('type') == 'op' and toke.get('value') == "="
                    and paren_count == 0 and bracket_count == 0 and brace_count == 0):
                    assig_pos = i
                    break

            if assig_pos != -1 and assig_pos > pos:
                left_tokens = tokens[pos:assig_pos]

                left_comma_positions = []
                paren_count = bracket_count = brace_count = 0
                for i, tok in enumerate(left_tokens):
                    if tok['type'] == 'symbol':
                        if tok['value'] == '(':
                            paren_count += 1
                        elif tok['value'] == ')':
                            paren_count -= 1
                        elif tok['value'] == '[':
                            bracket_count += 1
                        elif tok['value'] == ']':
                            bracket_count -= 1
                        elif tok['value'] == '{':
                            brace_count += 1
                        elif tok['value'] == '}':
                            brace_count -= 1
                    if tok['type'] == 'symbol' and tok['value'] == ',' and paren_count == 0 and bracket_count == 0 and brace_count == 0:
                        left_comma_positions.append(i)

                if left_comma_positions:
                    vars_list = []
                    rest_var = None
                    kwargs_var = None
                    last_pos = 0
                    for comma_pos in left_comma_positions:
                        var_tokens = left_tokens[last_pos:comma_pos]
                        if len(var_tokens) == 2 and var_tokens[0]['type'] == 'op' and var_tokens[0]['value'] == '**':
                            if var_tokens[1]['type'] == 'name':
                                kwargs_var = var_tokens[1]['value']
                            else:
                                raise KeiError("SyntaxError", f"** 后面必须是变量名, 得到 {var_tokens[1]}")
                        elif len(var_tokens) == 2 and var_tokens[0]['type'] == 'op' and var_tokens[0]['value'] == '*':
                            if var_tokens[1]['type'] == 'name':
                                rest_var = var_tokens[1]['value']
                            else:
                                raise KeiError("SyntaxError", f"* 后面必须是变量名, 得到 {var_tokens[1]}")
                        elif len(var_tokens) == 1 and var_tokens[0]['type'] == 'name':
                            vars_list.append(var_tokens[0]['value'])
                        elif len(var_tokens) > 0:
                            raise KeiError("SyntaxError", f"多变量赋值左边必须是变量名、*rest 或 **kwargs, 得到 {var_tokens}")
                        last_pos = comma_pos + 1
                    var_tokens = left_tokens[last_pos:]
                    if len(var_tokens) == 2 and var_tokens[0]['type'] == 'op' and var_tokens[0]['value'] == '**':
                        if var_tokens[1]['type'] == 'name':
                            kwargs_var = var_tokens[1]['value']
                        else:
                            raise KeiError("SyntaxError", f"** 后面必须是变量名, 得到 {var_tokens[1]}")
                    elif len(var_tokens) == 2 and var_tokens[0]['type'] == 'op' and var_tokens[0]['value'] == '*':
                        if var_tokens[1]['type'] == 'name':
                            rest_var = var_tokens[1]['value']
                        else:
                            raise KeiError("SyntaxError", f"* 后面必须是变量名, 得到 {var_tokens[1]}")
                    elif len(var_tokens) == 1 and var_tokens[0]['type'] == 'name':
                        vars_list.append(var_tokens[0]['value'])
                    elif len(var_tokens) > 0:
                        raise KeiError("SyntaxError", f"多变量赋值左边必须是变量名、*rest 或 **kwargs, 得到 {var_tokens}")
                    left_node = {'type': 'multiassign', 'vars': vars_list, 'rest': rest_var, 'kwargs': kwargs_var}
                else:
                    left_node, left_new_pos, _ = parse_expr(left_tokens, 0, allow_assign=True, all_lines=all_lines, linepos=linepos)
                    if not left_node or left_new_pos != len(left_tokens):
                        raise KeiError("SyntaxError", f"无效的赋值左边: {left_tokens}")

                right_tokens = tokens[assig_pos + 1:]
                right_comma_positions = []
                paren_count = bracket_count = brace_count = 0
                for i, tok in enumerate(right_tokens):
                    if tok['type'] == 'symbol':
                        if tok['value'] == '(':
                            paren_count += 1
                        elif tok['value'] == ')':
                            paren_count -= 1
                        elif tok['value'] == '[':
                            bracket_count += 1
                        elif tok['value'] == ']':
                            bracket_count -= 1
                        elif tok['value'] == '{':
                            brace_count += 1
                        elif tok['value'] == '}':
                            brace_count -= 1
                    if tok['type'] == 'symbol' and tok['value'] == ',' and paren_count == 0 and bracket_count == 0 and brace_count == 0:
                        right_comma_positions.append(i)

                if right_comma_positions:
                    elements = []
                    last_pos = 0
                    for comma_pos in right_comma_positions:
                        value_tokens = right_tokens[last_pos:comma_pos]
                        if value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '[':
                            val_node, _, _ = parse_list(value_tokens, 0, all_lines, linepos)
                        elif value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '{':
                            val_node, _, _ = parse_dict(value_tokens, 0, all_lines, linepos)
                        else:
                            val_node, _, _ = parse_expr(value_tokens, 0, allow_assign=False, all_lines=all_lines, linepos=linepos)
                        if val_node:
                            elements.append(val_node)
                        last_pos = comma_pos + 1
                    value_tokens = right_tokens[last_pos:]
                    if value_tokens:
                        if value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '[':
                            val_node, _, _ = parse_list(value_tokens, 0, all_lines, linepos)
                        elif value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '{':
                            val_node, _, _ = parse_dict(value_tokens, 0, all_lines, linepos)
                        else:
                            val_node, _, _ = parse_expr(value_tokens, 0, allow_assign=False, all_lines=all_lines, linepos=linepos)
                        if val_node:
                            elements.append(val_node)
                    right_node = {'type': 'list', 'elements': elements}
                    final_pos = assig_pos + 1 + len(right_tokens)
                else:
                    if right_tokens and right_tokens[0]['type'] == 'symbol' and right_tokens[0]['value'] == '{':
                        right_node, right_new_pos, _ = parse_dict(right_tokens, 0, all_lines, linepos)
                    elif right_tokens and right_tokens[0]['type'] == 'symbol' and right_tokens[0]['value'] == '[':
                        right_node, right_new_pos, _ = parse_list(right_tokens, 0, all_lines, linepos)
                    else:
                        right_node, right_new_pos, _ = parse_expr(right_tokens, 0, allow_assign=False, all_lines=all_lines, linepos=linepos)
                    if not right_node:
                        raise KeiError("SyntaxError", "无效的赋值右边")
                    final_pos = assig_pos + 1 + right_new_pos

                node = {'type': 'assign', 'left': left_node, 'right': right_node}
                return node, final_pos, linepos

            # 不是赋值语句，作为表达式解析
            node, new_pos, linepos = parse_expr(tokens, pos, allow_assign=False, all_lines=all_lines, linepos=linepos)
            if node is None:
                if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '}':
                    return None, pos, linepos
                raise KeiError("SyntaxError", f"无效的语法: {tokens[pos]['value'] if pos < len(tokens) else 'EOF'}")
            return node, new_pos, linepos

        node, new_pos, new_line = stmt()
        if node is not None:
            return node | {'source': code, 'linenum': tokens[pos]['linenum']}, new_pos, new_line
        else:
            return None, new_pos, new_line

    except Exception as e:
        # 错误处理保持不变
        error_config = {
            ZeroDivisionError: ("ZeroDivisionError", "无法对 0 进行除法"),
            OverflowError: ("OverflowError", f"数值过大, 无法处理: {e}"),
            FloatingPointError: ("FloatingPointError", f"浮点运算错误: {e}"),
            ArithmeticError: ("ArithmeticError", f"运算错误: {e}"),
            IndexError: ("IndexError", f"索引超出范围: {e}"),
            KeyError: ("KeyError", f"键不存在: {e}"),
            LookupError: ("LookupError", f"查找错误: {e}"),
            TypeError: ("TypeError", f"类型错误: {e}"),
            ValueError: ("ValueError", f"值错误: {e}"),
            AttributeError: ("AttributeError", f"属性不存在: {e}"),
            UnboundLocalError: ("UnboundLocalError", f"局部变量未绑定: {e}"),
            NameError: ("NameError", f"名称未定义: {e}"),
            FileNotFoundError: ("NotFoundError", f"文件未找到: {e}"),
            PermissionError: ("PermissionError", f"权限不足无法访问文件: {e}"),
            IsADirectoryError: ("IsDirError", f"预期文件但得到目录: {e}"),
            NotADirectoryError: ("NotDirError", f"预期目录但得到文件: {e}"),
            FileExistsError: ("FileExistsError", f"文件已存在: {e}"),
            TimeoutError: ("TimeoutError", f"操作超时: {e}"),
            OSError: ("OSError", f"操作系统错误: {e}"),
            RecursionError: ("RecursionError", f"递归深度超过限制"),
            KeiError: (e.types, e.value) if isinstance(e, KeiError) else ()
        }

        for exc_type, (err_name, err_msg) in error_config.items():
            if isinstance(e, exc_type):
                error(
                    err_name if err_name is not err_msg else None,
                    err_msg,
                    __kei__.stack.copy(),
                    globals()['source'],
                    globals()['linenum']+1,
                    __kei__.get('file', '未知文件')
                )
                if not __kei__.repl:
                    sys.exit(1)
                else:
                    raise
        else:
            error(
                type(e).__name__,
                str(e),
                __kei__.stack.copy(),
                globals()['source'],
                globals()['linenum']+1,
                __kei__.get('file', '未知文件')
            )
            if not __kei__.repl:
                sys.exit(1)
            else:
                raise

def parse_call(name, tokens, pos, is_attr=False, all_lines=None, linepos=0):
    """解析函数调用，返回 (node, new_pos, new_linepos)"""
    pos += 1  # 跳过 '('
    arguments = []

    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ')':
        pos += 1
        node = {
            'type': 'methodcall' if is_attr else 'call',
            'obj' if is_attr else 'name': name,
            'arguments': arguments,
        }
        return node, pos, linepos

    while True:
        # 处理 **kwargs
        if (pos < len(tokens) and tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '**' and
              pos + 1 < len(tokens)):
            pos += 1
            val, pos, linepos = parse_expr(tokens, pos, in_call=True, all_lines=all_lines, linepos=linepos)
            arguments.append({'type': 'starkwargs', 'value': val})

        # 处理 *args
        elif (pos < len(tokens) and tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '*' and
              pos + 1 < len(tokens)):
            pos += 1
            val, pos, linepos = parse_expr(tokens, pos, in_call=True, all_lines=all_lines, linepos=linepos)
            arguments.append({'type': 'starargs', 'value': val})

        # 关键字参数 name=value
        elif (pos < len(tokens) and tokens[pos]['type'] == 'name' and
              pos + 1 < len(tokens) and tokens[pos+1]['type'] == 'op' and
              tokens[pos+1]['value'] == "="):
            kwarg_name = tokens[pos]['value']
            pos += 2
            kwarg_value, pos, linepos = parse_expr(tokens, pos, in_call=True, all_lines=all_lines, linepos=linepos)
            arguments.append({'type': 'keyword', 'name': kwarg_name, 'value': kwarg_value})

        else:
            arg, pos, linepos = parse_expr(tokens, pos, in_call=True, all_lines=all_lines, linepos=linepos)
            arguments.append({'type': 'positional', 'value': arg})

        # 检查逗号或结束
        if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
            pos += 1
            continue
        elif pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ')':
            pos += 1
            break
        elif pos < len(tokens) and tokens[pos]['type'] == 'name':
            raise KeiError("SyntaxError", f"非预期的名称: {tokens[pos]['value']}")
        elif pos >= len(tokens):
            raise KeiError("SyntaxError", "缺少右括号 ')'")
        else:
            break

    node = {
        'type': 'methodcall' if is_attr else 'call',
        'obj' if is_attr else 'name': name,
        'arguments': arguments,
    }
    return node, pos, linepos

def parse_call_attr(obj_node, tokens, pos, in_call=False, all_lines=None, linepos=0):
    """解析方法调用，直接调用 parse_call"""
    return parse_call(obj_node, tokens, pos, is_attr=True, all_lines=all_lines, linepos=linepos)

def parse_atom(tokens: list, pos: int, in_call=False, all_lines=None, linepos=0) -> tuple:
    debug_print(f"parse_atom: pos={pos}, token={tokens[pos] if pos < len(tokens) else 'EOF'}")
    if pos >= len(tokens):
        return None, pos, linepos
    t = tokens[pos]

    if t["type"] == "symbol" and t["value"] == "}":
        return None, pos, linepos

    # lambda 函数
    if t['type'] == 'name' and t['value'] == 'fn':
        pos += 1
        params = []
        while pos < len(tokens):
            if tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '=>':
                pos += 1
                break
            elif tokens[pos]['type'] == 'name':
                params.append(tokens[pos]['value'])
                pos += 1
                if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
                    pos += 1
            else:
                break
        expr, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)
        node = {'type': 'lambda', 'params': params, 'body': expr}
        return node, pos, linepos

    # 关键字直接返回 None，让上层 parse_stmt 处理
    if t["type"] == "name" and t["value"] in keywords:
        return None, pos, linepos

    # 字面量
    if t["type"] in {"int", "float", "str", "bool", "null", "list", "dict"}:
        node = t
        pos += 1
        # 处理后缀操作
        while pos < len(tokens):
            current = tokens[pos]
            if current['type'] == 'symbol' and current['value'] == '.':
                pos += 1
                if pos >= len(tokens) or tokens[pos]['type'] != 'name':
                    raise KeiError("SyntaxError", "属性访问语法错误")
                node = {'type': 'attr', 'obj': node, 'attr': tokens[pos]['value']}
                pos += 1
                if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '(':
                    node, pos, linepos = parse_call_attr(node, tokens, pos, in_call, all_lines, linepos)
            elif current['type'] == 'symbol' and current['value'] == '[':
                node, pos, linepos = parse_index_with_obj(node, tokens, pos, all_lines, linepos)
            elif current['type'] == 'symbol' and current['value'] == '(':
                node, pos, linepos = parse_call_attr(node, tokens, pos, in_call, all_lines, linepos)
            else:
                break
        return node, pos, linepos

    # 名字（标识符）
    if t["type"] == "name":
        name = t["value"]
        pos += 1
        # 检查是否是 key=value 形式（在字典或参数列表中）
        if pos < len(tokens) and tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '=':
            if {'type': 'name', 'value': 'type'} not in tokens:
                pos -= 1
                return None, pos, linepos

        node = {'type': 'name', 'value': name}
        # 处理属性链和方法调用
        while pos < len(tokens):
            if tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '.':
                if pos + 1 < len(tokens) and tokens[pos+1]['type'] == 'symbol' and tokens[pos+1]['value'] == '.':
                    break
                pos += 1
                if pos >= len(tokens) or tokens[pos]['type'] != 'name':
                    raise KeiError("SyntaxError", "属性访问语法错误：'.' 后面缺少属性名")
                attr_name = tokens[pos]['value']
                pos += 1
                node = {'type': 'attr', 'obj': node, 'attr': attr_name}
                if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '(':
                    node, pos, linepos = parse_call_attr(node, tokens, pos, in_call, all_lines, linepos)
            elif tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '(':
                node, pos, linepos = parse_call(name, tokens, pos, all_lines=all_lines, linepos=linepos)
            elif tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '[':
                node, pos, linepos = parse_index_with_obj(node, tokens, pos, all_lines, linepos)
            else:
                break
        return node, pos, linepos

    # 括号表达式
    if t["type"] == "symbol" and t["value"] == "(":
        pos += 1
        expr, pos, linepos = parse_expr(tokens, pos, in_call, all_lines=all_lines, linepos=linepos)
        if pos >= len(tokens) or tokens[pos]["type"] != "symbol" or tokens[pos]["value"] != ")":
            raise KeiError("SyntaxError", "缺少右括号")
        pos += 1
        node = expr
        while pos < len(tokens):
            if tokens[pos]["type"] == "symbol" and tokens[pos]["value"] == ".":
                pos += 1
                if pos >= len(tokens) or tokens[pos]["type"] != "name":
                    raise KeiError("SyntaxError", "属性访问语法错误")
                attr = tokens[pos]["value"]
                pos += 1
                if pos < len(tokens) and tokens[pos]["type"] == "symbol" and tokens[pos]["value"] == "(":
                    node = {'type': 'attr', 'obj': node, 'attr': attr}
                    node, pos, linepos = parse_call_attr(node, tokens, pos, in_call, all_lines, linepos)
                else:
                    node = {"type": "attr", "obj": node, "attr": attr}
            elif tokens[pos]["type"] == "symbol" and tokens[pos]["value"] == "(":
                node, pos, linepos = parse_call_attr(node, tokens, pos, in_call, all_lines, linepos)
            elif tokens[pos]["type"] == "symbol" and tokens[pos]["value"] == "[":
                node, pos, linepos = parse_index_with_obj(node, tokens, pos, all_lines, linepos)
            else:
                break
        return node, pos, linepos

    # 列表
    if t["type"] == "symbol" and t["value"] == "[":
        node, pos, linepos = parse_list(tokens, pos, all_lines, linepos)
        # 处理后缀属性/调用
        while pos < len(tokens):
            if tokens[pos]["type"] == "symbol" and tokens[pos]["value"] == ".":
                pos += 1
                if pos >= len(tokens) or tokens[pos]["type"] != "name":
                    raise KeiError("SyntaxError", "属性访问语法错误")
                attr = tokens[pos]["value"]
                pos += 1
                node = {'type': 'attr', 'obj': node, 'attr': attr}
                if pos < len(tokens) and tokens[pos]["type"] == "symbol" and tokens[pos]["value"] == "(":
                    node, pos, linepos = parse_call_attr(node, tokens, pos, all_lines=all_lines, linepos=linepos)
            else:
                break
        return node, pos, linepos

    # 字典
    if t["type"] == "symbol" and t["value"] == "{":
        if pos + 1 < len(tokens) and tokens[pos+1]["type"] == "name" and tokens[pos+1]["value"] in keywords:
            return None, pos, linepos
        node, pos, linepos = parse_dict(tokens, pos, all_lines, linepos)
        return node, pos, linepos

    return None, pos, linepos

def parse_index_with_obj(obj_node, tokens, pos, all_lines=None, linepos=0):
    """解析索引访问，返回 (node, new_pos, new_linepos)"""
    pos += 1  # 跳过 '['
    bracket_count = 1
    end_pos = pos
    while end_pos < len(tokens):
        current = tokens[end_pos]
        if current == '[' or (isinstance(current, dict) and current.get('value') == '['):
            bracket_count += 1
        elif current == ']' or (isinstance(current, dict) and current.get('value') == ']'):
            bracket_count -= 1
            if bracket_count == 0:
                break
        end_pos += 1
    if end_pos >= len(tokens) or bracket_count != 0:
        raise KeiError("SyntaxError", "缺少 ]")
    inner_tokens = tokens[pos:end_pos]

    # 按顶层 ':' 分割（忽略嵌套括号内的冒号）
    parts = []
    current = []
    colon_count = 0
    paren_count = 0
    bracket_count = 0
    brace_count = 0

    for toke in inner_tokens:
        # 检查是否是顶层的冒号
        is_colon = (token == ':' or (isinstance(token, dict) and token.get('value') == ':'))
        if is_colon and paren_count == 0 and bracket_count == 0 and brace_count == 0:
            parts.append(current)
            current = []
            colon_count += 1
        else:
            # 更新括号计数
            if isinstance(toke, dict) and toke['type'] == 'symbol':
                if toke['value'] == '(':
                    paren_count += 1
                elif toke['value'] == ')':
                    paren_count -= 1
                elif toke['value'] == '[':
                    bracket_count += 1
                elif toke['value'] == ']':
                    bracket_count -= 1
                elif toke['value'] == '{':
                    brace_count += 1
                elif toke['value'] == '}':
                    brace_count -= 1
            current.append(toke)
    parts.append(current)

    start = None
    end = None
    step = None
    if len(parts) >= 1 and parts[0]:
        start, _, _ = parse_expr(parts[0], 0, all_lines=all_lines, linepos=linepos)
    if len(parts) >= 2 and parts[1]:
        end, _, _ = parse_expr(parts[1], 0, all_lines=all_lines, linepos=linepos)
    if len(parts) >= 3 and parts[2]:
        step, _, _ = parse_expr(parts[2], 0, all_lines=all_lines, linepos=linepos)

    is_slice = colon_count > 0
    if is_slice:
        node = {'type': 'slice', 'obj': obj_node, 'start': start, 'end': end, 'step': step}
    else:
        node = {'type': 'index', 'obj': obj_node, 'index': start}
    new_pos = end_pos + 1
    return node, new_pos, linepos

def parse_assign(tokens: list, pos: int, all_lines=None, linepos=0) -> tuple:
    # 检查 ** 赋值
    if (pos + 1 < len(tokens) and
        tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '*' and
        tokens[pos + 1]['type'] == 'op' and tokens[pos + 1]['value'] == '*'):
        if pos + 2 >= len(tokens) or tokens[pos + 2]['type'] != 'name':
            raise KeiError("SyntaxError", "** 后面必须是变量名")
        left = {'type': 'starstarassign', 'name': tokens[pos + 2]['value']}
        pos += 3
    elif tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '*':
        if pos + 1 >= len(tokens) or tokens[pos + 1]['type'] != 'name':
            raise KeiError("SyntaxError", "* 后面必须是变量名")
        left = {'type': 'starassign', 'name': tokens[pos + 1]['value']}
        pos += 2
    else:
        left = tokens[pos]
        pos += 1

    if pos >= len(tokens) or tokens[pos].get('type') != 'op' or tokens[pos].get('value') != '=':
        raise KeiError("SyntaxError", "需要 =")
    pos += 1

    right, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)
    node = {'type': 'assign', 'left': left, 'right': right}
    return node, pos, linepos

def parse_term(tokens, pos, in_call=False, all_lines=None, linepos=0):
    left, pos, linepos = parse_pow(tokens, pos, in_call, all_lines, linepos)
    while pos < len(tokens):
        t = tokens[pos]
        if t["type"] != "op":
            break
        if t["value"] in {"*", "/", "//", "%", "|"}:
            op = t["value"]
            pos += 1
            right, new_pos, linepos = parse_pow(tokens, pos, all_lines=all_lines, linepos=linepos)
            if right is None:
                raise KeiError("SyntaxError", f"运算符 '{op}' 后面缺少表达式")
            left = {"type": "binop", "op": op, "left": left, "right": right}
            pos = new_pos
        else:
            break
    return left, pos, linepos

def parse_pow(tokens, pos, in_call=False, all_lines=None, linepos=0):
    left, pos, linepos = parse_unary(tokens, pos, in_call, all_lines, linepos)
    while pos < len(tokens):
        t = tokens[pos]
        if t["type"] != "op":
            break
        if t["value"] == "**":
            op = t["value"]
            pos += 1
            right, new_pos, linepos = parse_unary(tokens, pos, all_lines=all_lines, linepos=linepos)
            if right is None:
                raise KeiError("SyntaxError", f"运算符 '{op}' 后面缺少表达式")
            left = {"type": "binop", "op": op, "left": left, "right": right}
            pos = new_pos
        else:
            break
    return left, pos, linepos

def parse_expr(tokens: list, pos: int, in_call=False, allow_assign=False, in_comp=False, all_lines=None, linepos=0) -> tuple:
    left, pos, linepos = parse_logic(tokens, pos, in_call, allow_assign, in_comp, all_lines, linepos)

    # 三目 if/unless
    while pos < len(tokens):
        t = tokens[pos]
        if t['value'] == 'if' and not in_comp:
            true_val = left
            pos += 1
            cond, pos, linepos = parse_expr(tokens, pos, in_call, allow_assign, in_comp, all_lines, linepos)
            if pos >= len(tokens) or tokens[pos].get('value') != 'else':
                raise KeiError("SyntaxError", "三目运算符需要 else 分支")
            pos += 1
            false_val, pos, linepos = parse_expr(tokens, pos, in_call, allow_assign, in_comp, all_lines, linepos)
            node = {'type': 'ternary', 'cond': cond, 'true_val': true_val, 'false_val': false_val}
            return node, pos, linepos
        if t['value'] == 'unless' and not in_comp:
            true_val = left
            pos += 1
            cond, pos, linepos = parse_expr(tokens, pos, in_call, allow_assign, in_comp, all_lines, linepos)
            if pos >= len(tokens) or tokens[pos].get('value') != 'else':
                raise KeiError("SyntaxError", "三目运算符需要 else 分支")
            pos += 1
            false_val, pos, linepos = parse_expr(tokens, pos, in_call, allow_assign, in_comp, all_lines, linepos)
            node = {'type': 'unternary', 'cond': cond, 'true_val': true_val, 'false_val': false_val}
            return node, pos, linepos
        break

    # ? 和 ! 后缀
    if pos < len(tokens) and tokens[pos].get('type') == 'op' and tokens[pos].get('value') == '?':
        pos += 1
        node = {'type': 'trysingle', 'expr': left}
        return node, pos, linepos
    if pos < len(tokens) and tokens[pos].get('type') == 'op' and tokens[pos].get('value') == '!':
        pos += 1
        node = {'type': 'notnullassert', 'expr': left}
        return node, pos, linepos

    return left, pos, linepos

def parse_logic(tokens, pos, in_call=False, allow_assign=False, in_comp=False, all_lines=None, linepos=0):
    left, pos, linepos = parse_compare(tokens, pos, in_call, allow_assign, in_comp, all_lines, linepos)
    while pos < len(tokens):
        t = tokens[pos]
        if t["type"] != "op":
            break
        if t["value"] in {"and", "or"}:
            op = t["value"]
            pos += 1
            right, new_pos, linepos = parse_compare(tokens, pos, in_call, allow_assign, in_comp, all_lines, linepos)
            if right is None:
                raise KeiError("SyntaxError", f"运算符 '{op}' 后面缺少表达式")
            left = {"type": "binop", "op": op, "left": left, "right": right}
            pos = new_pos
        else:
            break
    return left, pos, linepos

def parse_compare(tokens, pos, in_call=False, allow_assign=False, in_comp=False, all_lines=None, linepos=0):
    left, pos, linepos = parse_addsub(tokens, pos, in_call, allow_assign, in_comp, all_lines, linepos)
    while pos < len(tokens):
        t = tokens[pos]
        if t["type"] != "op":
            break
        if t["value"] in {"==", "!=", "<", ">", "<=", ">=", "in", "is"}:
            op = t["value"]
            pos += 1
            right, new_pos, linepos = parse_addsub(tokens, pos, in_call, allow_assign, in_comp, all_lines, linepos)
            if right is None:
                raise KeiError("SyntaxError", f"运算符 '{op}' 后面缺少表达式")
            left = {"type": "binop", "op": op, "left": left, "right": right}
            pos = new_pos
        else:
            break
    return left, pos, linepos

def parse_addsub(tokens, pos, in_call=False, allow_assign=False, in_comp=False, all_lines=None, linepos=0):
    left, pos, linepos = parse_term(tokens, pos, in_call, all_lines, linepos)
    while pos < len(tokens):
        t = tokens[pos]
        if t["type"] != "op":
            break
        if t["value"] in {"+", "-"}:
            op = t["value"]
            pos += 1
            right, new_pos, linepos = parse_term(tokens, pos, in_call, all_lines, linepos)
            if right is None:
                raise KeiError("SyntaxError", f"运算符 '{op}' 后面缺少表达式")
            left = {"type": "binop", "op": op, "left": left, "right": right}
            pos = new_pos
        elif t["value"] == "..":
            pos += 1
            right, new_pos, linepos = parse_addsub(tokens, pos, in_call, allow_assign, in_comp, all_lines, linepos)
            if right is None:
                raise KeiError("SyntaxError", f"运算符 '..' 后面缺少表达式")
            left = {'type': 'listscope', 'start': left, 'end': right}
            pos = new_pos
        elif t["value"] == "=" and allow_assign:
            break
        else:
            break
    return left, pos, linepos

def parse_match_pattern(tokens: list, pos: int, all_lines=None, linepos=0) -> tuple:
    if pos >= len(tokens):
        raise KeiError("SyntaxError", "case 后面缺少 pattern")
    t = tokens[pos]
    if t['type'] == 'name' and t['value'] == '_':
        return {'type': 'wildcard'}, pos + 1, linepos

    # 按 | 分割 pattern 块
    pattern_blocks = []
    current_block = []
    i = pos
    while i < len(tokens):
        toke = tokens[i]
        if toke['type'] == 'op' and toke['value'] == '|':
            if current_block:
                pattern_blocks.append(current_block)
                current_block = []
            i += 1
            continue
        if toke['type'] == 'symbol' and toke['value'] == '{':
            break
        current_block.append(toke)
        i += 1
    if current_block:
        pattern_blocks.append(current_block)
    if not pattern_blocks:
        raise KeiError("SyntaxError", "case 后面缺少 pattern")

    patterns = []
    for block in pattern_blocks:
        if not block:
            raise KeiError("SyntaxError", "| 之间不能为空")
        expr, _, _ = parse_expr(block, 0, all_lines=all_lines, linepos=linepos)
        if expr is None:
            raise KeiError("SyntaxError", f"无效的 pattern: {block}")
        patterns.append(expr)

    if len(patterns) == 1:
        node = {'type': 'expr', 'value': patterns[0]}
    else:
        node = {'type': 'or_pattern', 'patterns': patterns}
    return node, i, linepos

def parse_index(tokens: list, pos: int, all_lines=None, linepos=0) -> tuple:
    obj_node, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)
    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '[':
        pos += 1
        index, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)
        if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != ']':
            raise KeiError("SyntaxError", "缺少 ]")
        pos += 1
        node = {'type': 'index', 'obj': obj_node, 'index': index}
        while pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '[':
            pos += 1
            index, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)
            if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != ']':
                raise KeiError("SyntaxError", "缺少 ]")
            pos += 1
            node = {'type': 'index', 'obj': node, 'index': index}
        return node, pos, linepos
    return obj_node, pos, linepos

def parse_dictcomp(tokens, pos, all_lines=None, linepos=0):
    ifunless = None
    pos += 1  # 跳过 '{'
    # 找到 'for' 的位置
    for_pos = -1
    paren_count = 0
    bracket_count = 0
    brace_count = 1
    for i in range(pos, len(tokens)):
        toke = tokens[i]
        if toke.get('value') == 'for' and paren_count == 0 and bracket_count == 0 and brace_count == 1:
            for_pos = i
            break
        if toke['type'] == 'symbol':
            if toke['value'] == '(':
                paren_count += 1
            elif toke['value'] == ')':
                paren_count -= 1
            elif toke['value'] == '[':
                bracket_count += 1
            elif toke['value'] == ']':
                bracket_count -= 1
            elif toke['value'] == '{':
                brace_count += 1
            elif toke['value'] == '}':
                brace_count -= 1
    if for_pos == -1:
        raise KeiError("SyntaxError", "字典生成式需要 'for'")

    pairs_tokens = tokens[pos:for_pos]
    if not pairs_tokens:
        raise KeiError("SyntaxError", "字典生成式需要键值对")

    # 分割键值对
    pairs = []
    current_pair = []
    paren_count = bracket_count = brace_count = 0
    for toke in pairs_tokens:
        if (toke['type'] == 'symbol' and toke['value'] == ',' and
            paren_count == 0 and bracket_count == 0 and brace_count == 0):
            if current_pair:
                pairs.append(current_pair)
                current_pair = []
            continue
        if toke['type'] == 'symbol':
            if toke['value'] == '(':
                paren_count += 1
            elif toke['value'] == ')':
                paren_count -= 1
            elif toke['value'] == '[':
                bracket_count += 1
            elif toke['value'] == ']':
                bracket_count -= 1
            elif toke['value'] == '{':
                brace_count += 1
            elif toke['value'] == '}':
                brace_count -= 1
        current_pair.append(toke)
    if current_pair:
        pairs.append(current_pair)

    kv_pairs = []
    for pair_tokens in pairs:
        colon_pos = -1
        for i, t in enumerate(pair_tokens):
            if t['type'] == 'symbol' and t['value'] == ':':
                colon_pos = i
                break
        if colon_pos == -1:
            raise KeiError("SyntaxError", "字典生成式需要 ':'")
        key_tokens = pair_tokens[:colon_pos]
        value_tokens = pair_tokens[colon_pos+1:]
        key, _, _ = parse_expr(key_tokens, 0, in_comp=True, all_lines=all_lines, linepos=linepos)
        value, _, _ = parse_expr(value_tokens, 0, in_comp=True, all_lines=all_lines, linepos=linepos)
        kv_pairs.append({'key': key, 'value': value})

    pos = for_pos
    if pos >= len(tokens) or tokens[pos].get('value') != 'for':
        raise KeiError("SyntaxError", "字典生成式需要 'for'")
    pos += 1

    vars = []
    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '(':
        pos += 1
        while pos < len(tokens):
            if tokens[pos]['type'] == 'name':
                vars.append(tokens[pos]['value'])
                pos += 1
                if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
                    pos += 1
                    continue
                elif pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ')':
                    pos += 1
                    break
                else:
                    raise KeiError("SyntaxError", "解包语法错误，需要 )")
            else:
                raise KeiError("SyntaxError", f"解包需要变量名，得到 {tokens[pos]}")
    else:
        while pos < len(tokens):
            if tokens[pos]['type'] == 'name':
                vars.append(tokens[pos]['value'])
                pos += 1
                if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
                    pos += 1
                    continue
                else:
                    break
            else:
                break
    if not vars:
        raise KeiError("SyntaxError", "字典生成式需要变量名")
    if pos >= len(tokens) or tokens[pos].get('value') != 'in':
        raise KeiError("SyntaxError", "字典生成式需要 'in'")
    pos += 1
    iterable, pos, linepos = parse_expr(tokens, pos, in_comp=True, all_lines=all_lines, linepos=linepos)
    cond = None
    if pos < len(tokens) and tokens[pos].get('value') == 'if':
        ifunless = tokens[pos]['value']
        pos += 1
        cond, pos, linepos = parse_expr(tokens, pos, in_comp=True, all_lines=all_lines, linepos=linepos)
    if pos < len(tokens) and tokens[pos].get('value') == '}':
        pos += 1
    else:
        while pos < len(tokens) and tokens[pos].get('value') != '}':
            pos += 1
        if pos < len(tokens):
            pos += 1
    rettype = 'dictcomp' if ifunless != "unless" else 'undictcomp'
    node = {'type': rettype, 'pairs': kv_pairs, 'vars': vars, 'iterable': iterable, 'cond': cond}
    return node, pos, linepos

def parse_dict(tokens: list, pos: int, all_lines=None, linepos=0) -> tuple:
    start_pos = pos
    pos += 1  # 跳过 '{'

    # 如果是空字典
    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '}':
        pos += 1
        return {'type': 'dict', 'pairs': []}, pos, linepos

    # 向前查看，判断是否是字典生成式
    temp_pos = pos
    bracket_count = 1
    paren_count = 0
    square_count = 0

    while temp_pos < len(tokens):
        tok = tokens[temp_pos]
        if tok['type'] == 'symbol':
            if tok['value'] == '{':
                bracket_count += 1
            elif tok['value'] == '}':
                bracket_count -= 1
                if bracket_count == 0:
                    break
            elif tok['value'] == '(':
                paren_count += 1
            elif tok['value'] == ')':
                paren_count -= 1
            elif tok['value'] == '[':
                square_count += 1
            elif tok['value'] == ']':
                square_count -= 1

        # 如果在顶层遇到 for，且不在其他括号内，就是字典生成式
        if (tok.get('value') == 'for' and
            bracket_count == 1 and
            paren_count == 0 and
            square_count == 0):
            return parse_dictcomp(tokens, start_pos, all_lines, linepos)

        temp_pos += 1

    # 不是生成式，正常解析字典
    pairs = []

    while pos < len(tokens):
        if tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '}':
            pos += 1
            break

        # 解析键
        if tokens[pos]['type'] == 'str':
            key = tokens[pos]['value']
        elif tokens[pos]['type'] == 'int':
            key = int(tokens[pos]['value'])
        elif tokens[pos]['type'] == 'float':
            key = float(tokens[pos]['value'])
        else:
            raise KeiError("SyntaxError", f"字典键必须是字符串或数字, 得到 {tokens[pos]['value']}")
        pos += 1

        if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != ':':
            raise KeiError("SyntaxError", "字典键值对缺少 :")
        pos += 1

        value, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)
        if value is None:
            raise KeiError("SyntaxError", "字典值不能为空")
        pairs.append({'key': key, 'value': value})

        if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
            pos += 1
            continue

    return {'type': 'dict', 'pairs': pairs}, pos, linepos

def parse_unary(tokens: list, pos: int, in_call=False, all_lines=None, linepos=0) -> tuple:
    left, pos, linepos = parse_unary_prefix(tokens, pos, in_call, all_lines, linepos)
    while pos < len(tokens):
        t = tokens[pos]
        if t.get('type') == 'symbol' and t.get('value') == '(':
            left, pos, linepos = parse_call_attr(left, tokens, pos, in_call, all_lines, linepos)
        elif t.get('type') == 'op' and t.get('value') == '->':
            pos += 1
            type_node, pos, linepos = parse_atom(tokens, pos, in_call, all_lines, linepos)
            left = {'type': 'typeassert', 'expr': left, 'hint': type_node}
        elif t.get('type') == 'op' and t.get('value') == '??':
            pos += 1
            right, pos, linepos = parse_atom(tokens, pos, in_call, all_lines, linepos)
            left = {'type': 'coalesce', 'left': left, 'right': right}
        else:
            break
    return left, pos, linepos

def parse_unary_prefix(tokens, pos, in_call=False, all_lines=None, linepos=0):
    if pos >= len(tokens):
        return None, pos, linepos
    t = tokens[pos]
    if t["type"] == "op" and t["value"] == "not":
        pos += 1
        expr, pos, linepos = parse_unary_prefix(tokens, pos, in_call, all_lines, linepos)
        return {"type": "unary", "op": "not", "expr": expr}, pos, linepos
    if t["type"] == "op" and t["value"] == "-":
        pos += 1
        expr, pos, linepos = parse_unary_prefix(tokens, pos, in_call, all_lines, linepos)
        if expr and expr.get('type') in ('int', 'float'):
            if expr['type'] == 'int':
                expr['value'] = str(-int(expr['value']))
            else:
                expr['value'] = str(-float(expr['value']))
            return expr, pos, linepos
        return {"type": "unary", "op": "-", "expr": expr}, pos, linepos
    if t["type"] == "op" and t["value"] == "+":
        pos += 1
        expr, pos, linepos = parse_unary_prefix(tokens, pos, in_call, all_lines, linepos)
        return expr, pos, linepos

    expr, pos, linepos = parse_atom(tokens, pos, in_call, all_lines, linepos)
    # 处理后缀运算符
    while pos < len(tokens):
        t = tokens[pos]
        if t.get('type') == 'op' and t.get('value') in {"++", "--"}:
            op = t['value']
            pos += 1
            expr = {"type": "postfix", "op": op, "expr": expr}
        elif t.get('type') == 'op' and t.get('value') == '!':
            pos += 1
            expr = {"type": "notnullassert", "expr": expr}
        elif t.get('type') == 'symbol' and t.get('value') == '.':
            pos += 1
            if pos >= len(tokens) or tokens[pos]['type'] != 'name':
                raise KeiError("SyntaxError", "属性访问语法错误")
            attr = tokens[pos]['value']
            pos += 1
            if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '(':
                expr = {'type': 'attr', 'obj': expr, 'attr': attr}
                expr, pos, linepos = parse_call_attr(expr, tokens, pos, in_call, all_lines, linepos)
            else:
                expr = {'type': 'attr', 'obj': expr, 'attr': attr}
        elif t.get('type') == 'symbol' and t.get('value') == '(':
            expr, pos, linepos = parse_call_attr(expr, tokens, pos, in_call, all_lines, linepos)
        elif t.get('type') == 'symbol' and t.get('value') == '[':
            expr, pos, linepos = parse_index_with_obj(expr, tokens, pos, all_lines, linepos)
        else:
            break
    return expr, pos, linepos

def parse_methodcall(parts: list, tokens: list, pos: int, all_lines=None, linepos=0) -> tuple:
    method_name = parts[-1] if isinstance(parts[-1], str) else parts[-1].get('method')
    pos += 1
    args = []
    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ')':
        pos += 1
        node = {'type': 'methodcall', 'obj_parts': parts[:-1], 'method': method_name, 'args': args}
        return node, pos, linepos
    arg, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)
    if arg:
        args.append(arg)
    while pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
        pos += 1
        arg, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)
        if arg:
            args.append(arg)
    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ')':
        pos += 1
    node = {'type': 'methodcall', 'obj_parts': parts[:-1], 'method': method_name, 'args': args}
    return node, pos, linepos

def parse_listcomp(tokens, pos, all_lines=None, linepos=0):
    """解析列表生成式 [expr for var in iterable if cond]"""
    ifunless = None
    start_pos = pos
    pos += 1  # 跳过 '['

    # 收集表达式部分（直到遇到 'for'）
    expr_tokens = []
    paren_count = 0
    bracket_count = 0
    brace_count = 0
    temp_pos = pos

    while temp_pos < len(tokens):
        toke = tokens[temp_pos]

        # 更新括号计数
        if toke['type'] == 'symbol':
            if toke['value'] == '(':
                paren_count += 1
            elif toke['value'] == ')':
                paren_count -= 1
            elif toke['value'] == '[':
                bracket_count += 1
            elif toke['value'] == ']':
                bracket_count -= 1
            elif toke['value'] == '{':
                brace_count += 1
            elif toke['value'] == '}':
                brace_count -= 1

        # 找到顶层的 'for' 时停止
        if (toke.get('value') == 'for' and
            paren_count == 0 and
            bracket_count == 0 and
            brace_count == 0):
            break

        expr_tokens.append(toke)
        temp_pos += 1

    if not expr_tokens:
        raise KeiError("SyntaxError", "列表生成式需要表达式")

    # 解析表达式（可能包含多个用逗号分隔的表达式）
    has_comma = False
    comma_positions = []
    paren_count = bracket_count = brace_count = 0

    for i, tok in enumerate(expr_tokens):
        if tok['type'] == 'symbol':
            if tok['value'] == '(':
                paren_count += 1
            elif tok['value'] == ')':
                paren_count -= 1
            elif tok['value'] == '[':
                bracket_count += 1
            elif tok['value'] == ']':
                bracket_count -= 1
            elif tok['value'] == '{':
                brace_count += 1
            elif tok['value'] == '}':
                brace_count -= 1
            elif tok['value'] == ',' and paren_count == 0 and bracket_count == 0 and brace_count == 0:
                has_comma = True
                comma_positions.append(i)

    if has_comma:
        exprs = []
        start = 0
        for cp in comma_positions:
            sub = expr_tokens[start:cp]
            if sub:
                e, _, _ = parse_expr(sub, 0, in_comp=True, all_lines=all_lines, linepos=linepos)
                exprs.append(e)
            start = cp + 1
        if start < len(expr_tokens):
            e, _, _ = parse_expr(expr_tokens[start:], 0, in_comp=True, all_lines=all_lines, linepos=linepos)
            exprs.append(e)
        expr_node = exprs
    else:
        expr_node, _, _ = parse_expr(expr_tokens, 0, in_comp=True, all_lines=all_lines, linepos=linepos)

    pos = temp_pos
    if pos >= len(tokens) or tokens[pos].get('value') != 'for':
        raise KeiError("SyntaxError", "列表生成式需要 'for'")
    pos += 1

    # 解析变量名（支持解包）
    vars = []
    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '(':
        pos += 1
        while pos < len(tokens):
            if tokens[pos]['type'] == 'name':
                vars.append(tokens[pos]['value'])
                pos += 1
                if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
                    pos += 1
                    continue
                elif pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ')':
                    pos += 1
                    break
                else:
                    raise KeiError("SyntaxError", "解包语法错误，需要 )")
            else:
                raise KeiError("SyntaxError", f"解包需要变量名，得到 {tokens[pos]}")
    else:
        while pos < len(tokens):
            if tokens[pos]['type'] == 'name':
                vars.append(tokens[pos]['value'])
                pos += 1
                if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
                    pos += 1
                    continue
                else:
                    break
            else:
                break

    if not vars:
        raise KeiError("SyntaxError", "列表生成式需要变量名")

    if pos >= len(tokens) or tokens[pos].get('value') != 'in':
        raise KeiError("SyntaxError", "列表生成式需要 'in'")
    pos += 1

    # 解析可迭代对象
    iterable, pos, linepos = parse_expr(tokens, pos, in_comp=True, all_lines=all_lines, linepos=linepos)

    # 解析可选的条件
    cond = None
    if pos < len(tokens) and tokens[pos].get('value') == 'if':
        ifunless = tokens[pos]['value']
        pos += 1
        cond, pos, linepos = parse_expr(tokens, pos, in_comp=True, all_lines=all_lines, linepos=linepos)

    # 跳过可能的空格或分号直到 ']'
    while pos < len(tokens):
        if tokens[pos].get('value') == ']':
            pos += 1
            break
        pos += 1
    else:
        raise KeiError("SyntaxError", "列表生成式缺少 ']'")

    rettype = 'listcomp' if ifunless != "unless" else 'unlistcomp'
    node = {'type': rettype, 'expr': expr_node, 'vars': vars, 'iterable': iterable, 'cond': cond}
    return node, pos, linepos

def parse_list(tokens: list, pos: int, all_lines=None, linepos=0) -> tuple:
    start_pos = pos
    pos += 1  # 跳过 '['

    # 如果是空列表
    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ']':
        pos += 1
        return {'type': 'list', 'elements': []}, pos, linepos

    # 向前查看，判断是否是列表生成式
    temp_pos = pos
    bracket_count = 1
    paren_count = 0
    brace_count = 0

    while temp_pos < len(tokens):
        tok = tokens[temp_pos]
        if tok['type'] == 'symbol':
            if tok['value'] == '[':
                bracket_count += 1
            elif tok['value'] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    break
            elif tok['value'] == '(':
                paren_count += 1
            elif tok['value'] == ')':
                paren_count -= 1
            elif tok['value'] == '{':
                brace_count += 1
            elif tok['value'] == '}':
                brace_count -= 1

        # 如果在顶层遇到 for，且不在其他括号内，就是列表生成式
        if (tok.get('value') == 'for' and
            bracket_count == 1 and
            paren_count == 0 and
            brace_count == 0):
            return parse_listcomp(tokens, start_pos, all_lines, linepos)

        temp_pos += 1

    # 不是生成式，正常解析列表
    elements = []

    while True:
        elem, new_pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)
        if elem:
            elements.append(elem)
            pos = new_pos
        else:
            # 如果解析失败，可能是遇到 ] 或 , 等
            if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ']':
                pos += 1
                break
            pos += 1

        if pos >= len(tokens):
            break

        if tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
            pos += 1
            continue

        if tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ']':
            pos += 1
            break

    return {'type': 'list', 'elements': elements}, pos, linepos

def escape(s):
    """手动处理常见的转义序列, 其他原样保留"""
    result = []
    i = 0
    length = len(s)
    while i < length:
        if s[i] == '\\' and i + 1 < length:
            if s[i+1] == 'n':
                result.append('\n')
                i += 2
            elif s[i+1] == 't':
                result.append('\t')
                i += 2
            elif s[i+1] == 'r':
                result.append('\r')
                i += 2
            elif s[i+1] == '\\':
                result.append('\\')
                i += 2
            elif s[i+1] == '"':
                result.append('"')
                i += 2
            elif s[i+1] == "'":
                result.append("'")
                i += 2
            elif s[i+1] == '0' and i + 3 < length and s[i+2].isdigit() and s[i+3].isdigit():
                # 八进制 \xxx
                try:
                    result.append(chr(int(s[i+1:i+4], 8)))
                    i += 4
                except:
                    result.append(s[i])
                    i += 1
            elif s[i+1] == 'x' and i + 3 < length:
                # 十六进制 \xhh
                try:
                    result.append(chr(int(s[i+2:i+4], 16)))
                    i += 4
                except:
                    result.append(s[i])
                    i += 1
            elif s[i+1] == 'u' and i + 5 < length:
                # Unicode \uhhhh
                try:
                    result.append(chr(int(s[i+2:i+6], 16)))
                    i += 6
                except:
                    result.append(s[i])
                    i += 1
            elif s[i+1] == 'U' and i + 9 < length:
                # Unicode \Uhhhhhhhh
                try:
                    result.append(chr(int(s[i+2:i+10], 16)))
                    i += 10
                except:
                    result.append(s[i])
                    i += 1
            else:
                raise KeiError("ValueError", f"未知的转义序列: \\{s[i+1]}")
        else:
            result.append(s[i])
            i += 1

    return ''.join(result)

def find_method(class_obj, method_name, env):
    """在类的继承链中查找方法"""
    while class_obj:
        if method_name in class_obj.get('methods_map', {}):
            return class_obj['methods_map'][method_name]
        class_obj = env.get(class_obj.get('parent')) if class_obj.get('parent') else None
    return None

def runtoken(node, env) -> tuple:
    env["__env__"] = KeiDict(env)

    __kei__.env = env

    if 'source' not in globals():
        globals()['source'] = None
    if 'linenum' not in globals():
        globals()['linenum'] = None

    if node.get('source', None) is not None:
        globals()['source']  = node.get('source')

    if node.get('linenum', None) is not None:
        globals()['linenum'] = node.get('linenum')

    def runtokentemp() -> tuple:
        if env.get("__maxrecursion__"):
            if type(env["__maxrecursion__"]) is KeiInt:
                __maxrecursion__ = env["__maxrecursion__"].value
                if __maxrecursion__ > 0:
                    sys.setrecursionlimit(__maxrecursion__)
                elif __maxrecursion__ == 0:
                    sys.setrecursionlimit(1024)
                else:
                    raise KeiError("ValueError", "__maxrecursion__ 不能是负数")
            else:
                raise KeiError("ValueError", "__maxrecursion__ 必须是整数")

        if env.get("__precision__"):
            if type(env["__precision__"]) is KeiInt:
                __precision__ = env["__precision__"].value

                if __precision__ > 0:
                    getcontext().prec = __precision__
                elif __precision__ == 0:
                    getcontext().prec = 28
                else:
                    raise KeiError("ValueError", "__precision__ 不能是负数")
            else:
                raise KeiError("ValueError", "__precision__ 必须是整数")

        if node is None:
            raise KeiError("RuntimeError", "出现了未意料的None节点")

        # ========== 字面量 - 返回 Kei 对象 ==========
        if node['type'] in {'null', 'int', 'float', 'str', 'bool', 'list', 'dict'}:
            def temp() -> tuple:
                if node['type'] == 'null':
                    return null, False

                if node['type'] == 'int':
                    return KeiInt(int(node['value'])), False

                if node['type'] == 'float':
                    return KeiFloat(node['value']), False

                if node['type'] == 'str':
                    if node.get('mark') == 'f':
                        result = process_fstring(node['value'], env)
                        return KeiString(result), False
                    else:
                        return KeiString(node['value']), False

                if node['type'] == 'bool':
                    return KeiBool(node['value'] == 'true'), False

                if node['type'] == 'list':
                    elements = []
                    for elem in node['elements']:
                        val, _ = runtoken(elem, env)
                        elements.append(val)
                    return KeiList(elements), False

                if node['type'] == 'dict':
                    pairs = {}
                    for pair in node['pairs']:
                        val, _ = runtoken(pair['value'], env)
                        pairs[pair['key']] = val
                    return KeiDict(pairs), False

                return None, False

            return temp()

        # ========== match/case 语句 ==========
        if node['type'] == 'match':
            value, _ = runtoken(node['value'], env)

            for arm in node['arms']:
                matched = False

                for pattern_node in arm['patterns']:
                    if pattern_node['type'] == 'wildcard':
                        matched = True
                        break

                    elif pattern_node['type'] == 'expr':
                        # 单个表达式
                        pattern_val, _ = runtoken(pattern_node['value'], env)
                        if value.__eq__(pattern_val):
                            matched = True
                            break

                    elif pattern_node['type'] == 'or_pattern':
                        # 多个模式：每个 pattern 都是 AST 节点
                        for sub_pattern in pattern_node['patterns']:
                            # 统一用 runtoken 计算！
                            pattern_val, _ = runtoken(sub_pattern, env)
                            if value.__eq__(pattern_val):
                                matched = True
                                break
                        if matched:
                            break

                if matched:
                    for stmt in arm['body']:
                        val, is_return = runtoken(stmt, env)
                        if is_return:
                            return val, True
                    return None, False

            return None, False

        # ========== 变量访问 ==========
        if node['type'] == 'name':
            # 直接取 node['value']，但确保它是字符串
            name_value = node['value']

            # 如果 name_value 是字典（比如 {'type': 'name', 'value': 'arr'}），递归取值
            while isinstance(name_value, dict) and 'value' in name_value:
                name_value = name_value['value']

            if name_value == "..." and "..." in env:
                return env["..."], False

            # 统一处理：按 '.' 分割
            assert type(name_value) is str, "变量名称不是字符串"
            parts = name_value.split('.') if '.' in name_value else [name_value]

            # 查找第一个部分（变量名）
            obj = None
            current = env
            while current is not None:
                if parts[0] in current:
                    obj = current[parts[0]]
                    break
                current = current.get('__parent__')

            if obj is None:
                return undefined, False

            # 如果有更多部分，继续查找属性
            for part in parts[1:]:
                if isinstance(obj, KeiBase):
                    obj = obj[part]
                elif isinstance(obj, dict):
                    if part in obj:
                        obj = obj[part]
                    else:
                        return undefined, False
                else:
                    try:
                        obj = getattr(obj, part)
                    except AttributeError:
                        return undefined, False

                if obj is undefined:
                    return undefined, False

            return obj, False

        if node['type'] == 'coalesce':
            left_val, left_flag = runtoken(node['left'], env)

            if left_flag:
                return left_val, True

            if not (left_val is undefined or left_val is null):
                return left_val, left_flag

            right_val, right_flag = runtoken(node['right'], env)
            return right_val, right_flag

        if node['type'] == 'notnullassert':
            val, flag = runtoken(node['expr'], env)

            if flag:
                return val, True

            if val is undefined or val is null:
                raise KeiError("TypeError", f"非空断言失败: {val} 是空的")

            return val, flag

        # ========== 索引访问 ==========
        if node['type'] == 'index':
            obj, _ = runtoken(node['obj'], env)
            index, _ = runtoken(node['index'], env)

            if isinstance(obj, KeiBase):
                if isinstance(index, KeiInt):
                    result = obj[index.value]
                else:
                    result = obj[index]
            elif isinstance(obj, (list, dict, str)):
                if env.get("__compat_mode__"):
                    try:
                        if isinstance(index, KeiInt):
                            result = obj[index.value]
                        elif isinstance(index, KeiString):
                            result = obj[index.value]
                        else:
                            result = obj[index]
                    except (IndexError, KeyError):
                        result = undefined
                else:
                    raise KeiError("TypeError", f"无法对非Kei对象进行索引: {type(obj)}")
            else:
                result = undefined

            return result, False

        if node['type'] == 'trysingle':
            try:
                __kei__.catch.append(True)
                val, flag = runtoken(node['expr'], env)
                return val, flag
            except:
                return null, False
            finally:
                __kei__.catch.pop()

        # ========== 切片访问 ==========
        if node['type'] == 'slice':
            # 获取对象
            obj, _ = runtoken(node['obj'], env)

            # 解析 start, end, step
            start = None
            end = None
            step = 1  # 默认步长1

            if node['start'] is not None:
                start_val, _ = runtoken(node['start'], env)
                if isinstance(start_val, KeiInt):
                    start = start_val.value

            if node['end'] is not None:
                end_val, _ = runtoken(node['end'], env)
                if isinstance(end_val, KeiInt):
                    end = end_val.value

            if node['step'] is not None:
                step_val, _ = runtoken(node['step'], env)
                if isinstance(step_val, KeiInt):
                    step = step_val.value

            # 调用对象的 __getitem__ 并传入切片
            if hasattr(obj, '__getitem__'):
                # 创建 Python 切片对象
                py_slice = slice(start, end, step)
                return obj[py_slice], False

        # ========== 属性访问 ==========
        if node['type'] == 'attr':
            obj, _ = runtoken(node['obj'], env)
            attr = node['attr']

            if isinstance(obj, KeiBase):
                return obj[attr], False
            elif isinstance(obj, dict):
                return obj.get(attr, undefined), False
            else:
                try:
                    return getattr(obj, attr), False
                except AttributeError:
                    return undefined, False

        # ========== 后缀运算 ++/-- ==========
        if node['type'] == 'postfix':
            val, flag = runtoken(node['expr'], env)
            if flag:
                return val, True

            if node['op'] == '++':
                if isinstance(val, (KeiInt, KeiFloat)):
                    new_val = val.value + 1

                    if node['expr']['type'] == 'name':
                        if isinstance(val, KeiInt):
                            env[node['expr']['value']] = KeiInt(new_val)
                        else:
                            env[node['expr']['value']] = KeiFloat(new_val)
                    elif node['expr']['type'] == 'attr':
                        obj, _ = runtoken(node['expr']['obj'], env)
                        attr = node['expr']['attr']
                        if isinstance(obj, KeiInstance):
                            if isinstance(val, KeiInt):
                                obj[attr] = KeiInt(new_val)
                            else:
                                obj[attr] = KeiFloat(new_val)

                    # 返回新值！
                    if isinstance(val, KeiInt):
                        return KeiInt(new_val), flag
                    else:
                        return KeiFloat(new_val), flag
                else:
                    raise KeiError("TypeError", f"无法对 {val} 进行 ++ 运算")

            elif node['op'] == '--':
                if isinstance(val, (KeiInt, KeiFloat)):
                    new_val = val.value - 1

                    if node['expr']['type'] == 'name':
                        if isinstance(val, KeiInt):
                            env[node['expr']['value']] = KeiInt(new_val)
                        else:
                            env[node['expr']['value']] = KeiFloat(new_val)
                    elif node['expr']['type'] == 'attr':
                        obj, _ = runtoken(node['expr']['obj'], env)
                        attr = node['expr']['attr']
                        if isinstance(obj, KeiInstance):
                            if isinstance(val, KeiInt):
                                obj[attr] = KeiInt(new_val)
                            else:
                                obj[attr] = KeiFloat(new_val)

                    # 返回新值！
                    if isinstance(val, KeiInt):
                        return KeiInt(new_val), flag
                    else:
                        return KeiFloat(new_val), flag
                else:
                    raise KeiError("TypeError", f"无法对 {type(val)} 进行 -- 运算")

        # ========== 复合赋值处理 ==========
        if node['type'] == 'compound_assign':
            def compound_assign():
                # 傻逼Pylance偷懒给我搞个
                # "代码太复杂，无法分析；通过重构为子例程或减少条件代码路径来降低复杂性"
                # 还好我聪明

                right_val, flag = runtoken(node['right'], env)
                left = node['left']
                op = node['op']

                # ===== 多变量复合赋值 (a, b += 1, 2) =====
                if left['type'] == 'multiassign':
                    vars_list = left['vars']
                    rest_var = left.get('rest')
                    kwargs_var = left.get('kwargs')

                    # 处理右边的值
                    if isinstance(right_val, KeiList):
                        right_items = right_val.items
                    elif isinstance(right_val, (list, tuple)):
                        right_items = list(right_val)
                    else:
                        right_items = [right_val]

                    # 处理普通变量
                    new_values = []
                    for i, var in enumerate(vars_list):
                        if var == '_':
                            continue
                        current = env.get(var, undefined)

                        if op == '+=':
                            new_val = current + (right_items[i] if i < len(right_items) else undefined)
                        elif op == '-=':
                            new_val = current - (right_items[i] if i < len(right_items) else undefined)
                        elif op == '*=':
                            new_val = current * (right_items[i] if i < len(right_items) else undefined)
                        elif op == '/=':
                            r = right_items[i] if i < len(right_items) else undefined
                            if r == 0:
                                raise KeiError("ZeroDivisionError", "除数不能为零")
                            new_val = current / r
                        else:
                            raise KeiError("SyntaxError", f"不支持的操作符: {op}")

                        env[var] = new_val
                        new_values.append(new_val)

                    # 处理 *rest 变量
                    if rest_var:
                        rest_items = right_items[len(vars_list):]
                        current = env.get(rest_var, KeiList([]))

                        if op == '+=':
                            if isinstance(current, KeiList):
                                new_val = KeiList(current.items + rest_items)
                            else:
                                new_val = KeiList([current] + rest_items)
                        elif op == '-=':
                            # 列表减法：移除出现在 rest_items 中的元素
                            if isinstance(current, KeiList):
                                new_items = [x for x in current.items if x not in rest_items]
                            else:
                                new_items = [current] if current not in rest_items else []
                            new_val = KeiList(new_items)
                        elif op == '*=':
                            # 列表乘法
                            if rest_items and isinstance(rest_items[0], (int, KeiInt)):
                                times = rest_items[0].value if isinstance(rest_items[0], KeiInt) else rest_items[0]
                                if isinstance(current, KeiList):
                                    new_val = KeiList(current.items * times)
                                else:
                                    new_val = KeiList([current] * times)
                            else:
                                raise KeiError("ValueError", f"*= 需要整数乘数")
                        elif op == '/=':
                            raise KeiError("TypeError", f"列表不支持 /= 操作")
                        else:
                            raise KeiError("TypeError", f"*rest 变量不支持 {op} 操作")
                        env[rest_var] = new_val

                    # 处理 **kwargs 变量
                    if kwargs_var:
                        current = env.get(kwargs_var, KeiDict({}))

                        # 把右边转成字典
                        if isinstance(right_val, KeiDict):
                            right_dict = right_val.items
                        elif isinstance(right_val, dict):
                            right_dict = right_val
                        else:
                            raise KeiError("TypeError", f"**kwargs 赋值右边必须是字典，得到 {type(right_val)}")

                        if op == '+=':
                            # 合并字典
                            if isinstance(current, KeiDict):
                                new_dict = current.items.copy()
                            elif isinstance(current, dict):
                                new_dict = current.copy()
                            else:
                                new_dict = {}
                            new_dict.update(right_dict)
                            new_val = KeiDict(new_dict)

                        elif op == '-=':
                            # 删除键
                            if isinstance(current, KeiDict):
                                new_dict = current.items.copy()
                            elif isinstance(current, dict):
                                new_dict = current.copy()
                            else:
                                new_dict = {}
                            for key in right_dict.keys():
                                if key in new_dict:
                                    del new_dict[key]
                            new_val = KeiDict(new_dict)

                        elif op == '*=':
                            # 字典乘法？保留键值对重复 times 次？这啥语义？
                            raise KeiError("TypeError", f"字典不支持 *= 操作")

                        elif op == '/=':
                            raise KeiError("TypeError", f"字典不支持 /= 操作")

                        else:
                            raise KeiError("TypeError", f"**kwargs 变量不支持 {op} 操作")

                        env[kwargs_var] = new_val

                    return KeiList(new_values), flag

                # ===== 单变量赋值 =====
                elif left['type'] == 'name':
                    name = left['value']
                    current = env.get(name, undefined)

                    if op == '+=':
                        new_val = current + right_val
                    elif op == '-=':
                        new_val = current - right_val
                    elif op == '*=':
                        new_val = current * right_val
                    elif op == '/=':
                        if right_val == 0:
                            raise KeiError("ZeroDivisionError", "除数不能为零")
                        new_val = current / right_val
                    else:
                        raise KeiError("SyntaxError", f"不支持的操作符: {op}")

                    env[name] = new_val
                    return new_val, flag

                # ===== 属性赋值 obj.attr += val =====
                elif left['type'] == 'attr':
                    obj, _ = runtoken(left['obj'], env)
                    attr = left['attr']

                    # 获取当前值
                    if isinstance(obj, KeiBase):
                        current = obj[attr]
                    elif isinstance(obj, dict):
                        current = obj.get(attr, undefined)
                    else:
                        current = getattr(obj, attr, undefined)

                    # 计算新值
                    if op == '+=':
                        new_val = current + right_val
                    elif op == '-=':
                        new_val = current - right_val
                    elif op == '*=':
                        new_val = current * right_val
                    elif op == '/=':
                        if right_val == 0:
                            raise KeiError("ZeroDivisionError", "除数不能为零")
                        new_val = current / right_val
                    else:
                        raise KeiError("SyntaxError", f"不支持的操作符: {op}")

                    # 赋值回去
                    if isinstance(obj, KeiBase):
                        obj[attr] = new_val
                    elif isinstance(obj, dict):
                        obj[attr] = new_val
                    else:
                        setattr(obj, attr, new_val)

                    return new_val, flag

                # ===== 索引赋值 arr[0] += val =====
                elif left['type'] == 'index':
                    obj, _ = runtoken(left['obj'], env)
                    index, _ = runtoken(left['index'], env)

                    # 获取当前值
                    current = obj[index]

                    # 计算新值
                    if op == '+=':
                        new_val = current + right_val
                    elif op == '-=':
                        new_val = current - right_val
                    elif op == '*=':
                        new_val = current * right_val
                    elif op == '/=':
                        if right_val == 0:
                            raise KeiError("ZeroDivisionError", "除数不能为零")
                        new_val = current / right_val
                    else:
                        raise KeiError("SyntaxError", f"不支持的操作符: {op}")

                    # 赋值回去
                    obj[index] = new_val
                    return new_val, flag

                # ===== * 赋值 =====
                elif left['type'] in ('star_target', 'starassign'):
                    name = left['name']
                    current = env.get(name, undefined)

                    # 把右边变成列表
                    if isinstance(right_val, KeiList):
                        right_list = right_val
                    elif isinstance(right_val, (list, tuple)):
                        right_list = KeiList(list(right_val))
                    else:
                        right_list = KeiList([right_val])

                    if op == '+=':
                        if isinstance(current, KeiList):
                            new_val = KeiList(current.items + right_list.items)
                        else:
                            new_val = KeiList([current] + right_list.items)
                    elif op == '-=':
                        if isinstance(current, KeiList):
                            new_items = [x for x in current.items if x not in right_list.items]
                        else:
                            new_items = [current] if current not in right_list.items else []
                        new_val = KeiList(new_items)
                    elif op == '*=':
                        if len(right_list.items) == 1 and isinstance(right_list.items[0], (int, KeiInt)):
                            times = right_list.items[0].value if isinstance(right_list.items[0], KeiInt) else right_list.items[0]
                            if isinstance(current, KeiList):
                                new_val = KeiList(current.items * times)
                            else:
                                new_val = KeiList([current] * times)
                        else:
                            raise KeiError("TypeError", f"*= 需要整数乘数")
                    elif op == '/=':
                        raise KeiError("TypeError", f"* 变量不支持 /= 操作")
                    else:
                        raise KeiError("TypeError", f"* 变量不支持 {op} 操作")

                    env[name] = new_val
                    return new_val, flag

                # ===== ** 赋值 =====
                elif left['type'] in ('starstar_target', 'starstarassign'):
                    name = left['name']
                    current = env.get(name, undefined)

                    if not isinstance(right_val, (KeiDict, dict)):
                        raise KeiError("TypeError", f"** 赋值右边必须是字典，得到 {type(right_val)}")

                    if op == '+=':
                        # 合并字典
                        if isinstance(current, KeiDict):
                            new_dict = current.items.copy()
                        elif isinstance(current, dict):
                            new_dict = current.copy()
                        else:
                            new_dict = {}

                        if isinstance(right_val, KeiDict):
                            new_dict.update(right_val.items)
                        else:
                            new_dict.update(right_val)

                        new_val = KeiDict(new_dict)

                    elif op == '-=':
                        # 删除键
                        if isinstance(current, KeiDict):
                            new_dict = current.items.copy()
                        elif isinstance(current, dict):
                            new_dict = current.copy()
                        else:
                            new_dict = {}

                        right_dict = right_val.items if isinstance(right_val, KeiDict) else right_val
                        for key in right_dict.keys():
                            if key in new_dict:
                                del new_dict[key]

                        new_val = KeiDict(new_dict)

                    elif op == '*=':
                        raise KeiError("TypeError", f"** 变量不支持 *= 操作")
                    elif op == '/=':
                        raise KeiError("TypeError", f"** 变量不支持 /= 操作")
                    else:
                        raise KeiError("TypeError", f"** 变量不支持 {op} 操作")

                    env[name] = new_val
                    return new_val, flag

                else:
                    raise KeiError("TypeError", f"不支持的复合赋值目标: {left}")

            return compound_assign()

        if node['type'] == 'ternary':
            cond_val, cond_flag = runtoken(node['cond'], env)
            if cond_flag:
                return cond_val, True

            if cond_val:
                return runtoken(node['true_val'], env)
            else:
                return runtoken(node['false_val'], env)

        if node['type'] == 'unternary':
            cond_val, cond_flag = runtoken(node['cond'], env)
            if cond_flag:
                return cond_val, True

            if not cond_val:  # unless 的条件为 false 时执行 true_val
                return runtoken(node['true_val'], env)
            else:
                return runtoken(node['false_val'], env)

        # ========== 列表生成式 ==========
        if node['type'] in {'listcomp', 'unlistcomp'}:
            un = True if node['type'] == "unlistcomp" else False
            result = []
            iterable_val, _ = runtoken(node['iterable'], env)
            vars_list = node['vars']
            expr_node = node['expr']
            cond = node.get('cond')

            # 获取可迭代对象
            if isinstance(iterable_val, KeiList):
                items = iterable_val.items
            elif isinstance(iterable_val, KeiString):
                items = [KeiString(c) for c in iterable_val.value]
            elif isinstance(iterable_val, KeiDict):
                items = [(KeiString(k), v) for k, v in iterable_val.items.items()]
            else:
                try:
                    items = list(iterable_val)
                except:
                    items = [iterable_val]

            # 遍历
            for item in items:
                # 设置变量
                if len(vars_list) == 1:
                    env[vars_list[0]] = item
                else:
                    # 多变量解包
                    if isinstance(item, (list, tuple, KeiList)):
                        item_list = item.items if isinstance(item, KeiList) else list(item)
                        for i, var in enumerate(vars_list):
                            if i < len(item_list):
                                env[var] = item_list[i]
                            else:
                                env[var] = undefined
                    else:
                        env[vars_list[0]] = item
                        for var in vars_list[1:]:
                            env[var] = undefined

                # 如果有条件，先判断
                if cond:
                    cond_val, _ = runtoken(cond, env)
                    if un:
                        if cond_val:
                            continue
                    else:
                        if not cond_val:
                            continue

                # 计算表达式
                if isinstance(expr_node, list):
                    # 多个表达式
                    for sub_expr in expr_node:
                        val, _ = runtoken(sub_expr, env)
                        result.append(val)
                else:
                    # 单个表达式
                    val, _ = runtoken(expr_node, env)
                    result.append(val)

            return KeiList(result), False

        # ========== 字典生成式 ==========
        if node['type'] in {'dictcomp', 'undictcomp'}:
            un = True if node['type'] == "undictcomp" else False
            result = {}
            iterable_val, _ = runtoken(node['iterable'], env)
            vars_list = node['vars']
            pairs = node['pairs']
            cond = node.get('cond')

            # 获取可迭代对象
            if isinstance(iterable_val, KeiList):
                items = iterable_val.items
            elif isinstance(iterable_val, KeiString):
                items = [KeiString(c) for c in iterable_val.value]
            elif isinstance(iterable_val, KeiDict):
                items = [(KeiString(k), v) for k, v in iterable_val.items.items()]
            else:
                try:
                    items = list(iterable_val)
                except:
                    items = [iterable_val]

            # 遍历
            for item in items:
                # 设置变量
                if len(vars_list) == 1:
                    env[vars_list[0]] = item
                else:
                    if isinstance(item, (list, tuple, KeiList)):
                        item_list = item.items if isinstance(item, KeiList) else list(item)
                        for i, var in enumerate(vars_list):
                            if i < len(item_list):
                                env[var] = item_list[i]
                            else:
                                env[var] = undefined
                    else:
                        env[vars_list[0]] = item
                        for var in vars_list[1:]:
                            env[var] = undefined

                # 如果有条件，先判断
                if cond:
                    cond_val, _ = runtoken(cond, env)
                    if un:
                        if cond_val:
                            continue
                    else:
                        if not cond_val:
                            continue

                # 计算所有键值对
                for pair in pairs:
                    key, _ = runtoken(pair['key'], env)
                    val, _ = runtoken(pair['value'], env)

                    # key 转成可哈希类型
                    if isinstance(key, KeiInt):
                        py_key = key.value
                    elif isinstance(key, KeiString):
                        py_key = key.value
                    elif isinstance(key, KeiFloat):
                        py_key = key.value
                    else:
                        py_key = key

                    result[py_key] = val

            return KeiDict(result), False

        # ========== 二元运算 ==========
        if node['type'] == 'binop':
            def binop() -> tuple:
                op = node['op']

                if op in {'and', 'or'}:
                    left, l_flag = runtoken(node['left'], env)

                    if isinstance(left, KeiBool):
                        left_bool = left.value
                    elif hasattr(left, '_value'):
                        left_bool = left.value
                    else:
                        left_bool = bool(left)

                    if op == 'and':
                        if not left_bool:
                            return false, l_flag
                    else:
                        if left_bool:
                            return true, l_flag

                    right, r_flag = runtoken(node['right'], env)

                    if isinstance(right, KeiBool):
                        right_bool = right.value
                    elif hasattr(right, '_value'):
                        right_bool = right.value
                    else:
                        right_bool = bool(right)

                    result_bool = left_bool or right_bool if op == 'or' else left_bool and right_bool

                    if result_bool:
                        return true, (l_flag or r_flag)
                    else:
                        return false, (l_flag or r_flag)

                left, l_flag = runtoken(node['left'], env)
                right, r_flag = runtoken(node['right'], env)

                try:
                    if op == '+':
                        result = left.__add__(right)
                    elif op == '-':
                        result = left.__sub__(right)
                    elif op == '*':
                        result = left.__mul__(right)
                    elif op == '/':
                        result = left.__truediv__(right)
                    elif op == '//':
                        result = left.__floordiv__(right)
                    elif op == '%':
                        result = left.__mod__(right)
                    elif op == '**':
                        result = left.__pow__(right)
                    elif op == '==':
                        result = left.__eq__(right)
                    elif op == '!=':
                        result = left.__ne__(right)
                    elif op == '<':
                        result = left.__lt__(right)
                    elif op == '>':
                        result = left.__gt__(right)
                    elif op == '<=':
                        result = left.__le__(right)
                    elif op == '>=':
                        result = left.__ge__(right)
                    elif op == 'is':
                        # 处理 is 运算符
                        left, l_flag = runtoken(node['left'], env)
                        right, r_flag = runtoken(node['right'], env)

                        # 情况1：右边是 KeiClass（类型检查）
                        if isinstance(right, KeiClass):
                            # 左边是实例，检查类型
                            if isinstance(left, KeiInstance):
                                result = true if left._class == right else false
                            # 左边是类对象
                            elif isinstance(left, KeiClass):
                                result = true if left == right else false
                            # 其他情况
                            else:
                                result = false

                        # 情况2：右边是 Python 类型（如 KeiInt, KeiFloat）
                        elif isinstance(right, type) and issubclass(right, KeiBase):
                            # 左边也是类型
                            if isinstance(left, type) and issubclass(left, KeiBase):
                                result = true if left == right else false
                            # 左边是实例
                            elif isinstance(left, KeiBase):
                                result = true if isinstance(left, right) else false
                            else:
                                result = false

                        # 情况3：特殊处理：float 包含 int
                        elif right == KeiFloat and isinstance(left, KeiInt):
                            result = true

                        # 情况4：普通对象身份比较
                        else:
                            result = true if left is right else false

                        return result, (l_flag or r_flag)

                    elif op == 'in':
                        # 处理 in 运算符

                        # 1. KeiList 特殊处理
                        if isinstance(right, KeiList):
                            # 直接遍历 items
                            found = false
                            for item in right.items:
                                if left == item:
                                    found = true
                                    break
                            result = found

                        # 2. KeiDict 特殊处理
                        elif isinstance(right, KeiDict):
                            # 检查键是否存在
                            key = left.value if hasattr(left, 'value') else left
                            result = true if key in right.items else false

                        # 3. KeiString 特殊处理
                        elif isinstance(right, KeiString):
                            val = left.value if hasattr(left, 'value') else str(left)
                            result = true if val in right.value else false

                        # 4. 有 __contains__ 的 Kei 对象
                        elif hasattr(right, '__contains__'):
                            result = right.__contains__(left)

                        # 5. Python 原生类型
                        elif isinstance(right, (list, tuple, str)):
                            val = left.value if hasattr(left, 'value') else left
                            result = true if val in right else false

                        elif isinstance(right, dict):
                            key = left.value if hasattr(left, 'value') else left
                            result = true if key in right else false

                        else:
                            result = false

                    elif op == '|':
                        result = left.__or__(right)

                    else:
                        raise KeiError("SyntaxError", f"未知运算符: {op}")

                    if result is undefined:
                        raise KeiError("TypeError", f"{left} 和 {right} 无法 {op} 运算")

                    return result, (l_flag or r_flag)

                except AttributeError:
                    raise KeiError("TypeError", f"{left} 和 {right} 无法 {op} 运算")
                except TypeError:
                    raise KeiError("TypeError", f"{left} 和 {right} 无法 {op} 运算")

            return binop()

        # ========== 一元运算 ==========
        if node['type'] == 'unary':
            if node['op'] == 'not':
                val, flag = runtoken(node['expr'], env)
                return KeiBool(not bool(val)), flag
            elif node['op'] == '-':
                val, flag = runtoken(node['expr'], env)
                if isinstance(val, KeiInt):
                    return KeiInt(-val.value), flag
                elif isinstance(val, KeiFloat):
                    return KeiFloat(-val.value), flag
                else:
                    raise KeiError("TypeError", f"无法对 {content(val)} 进行取负运算")

        # ========== 范围操作符 .. ==========
        if node['type'] == 'listscope':
            start_val, _ = runtoken(node['start'], env)
            end_val, _ = runtoken(node['end'], env)

            start = start_val.value if isinstance(start_val, KeiInt) else int(start_val)
            end = end_val.value if isinstance(end_val, KeiInt) else int(end_val)

            result = []
            if start <= end:
                # 递增
                current = start
                while current <= end:
                    result.append(KeiInt(current))
                    current += 1
            else:
                # 递减
                current = start
                while current >= end:
                    result.append(KeiInt(current))
                    current -= 1

            return KeiList(result), False

        # ========== 函数调用 ==========
        if node['type'] in {'call', 'methodcall'}:
            # ----- 1. 统一解析参数（使用新结构）-----
            args = []
            kwargs = {}

            # 获取当前行的源代码
            call_source = node.get('source')
            if call_source is None:
                call_source = globals().get('source', '')

            # 按顺序处理 arguments
            for arg_node in node.get('arguments', []):
                if arg_node['type'] == 'positional':
                    val, _ = runtoken(arg_node['value'], env)
                    args.append(val)

                elif arg_node['type'] == 'keyword':
                    val, _ = runtoken(arg_node['value'], env)
                    kwargs[arg_node['name']] = val

                elif arg_node['type'] == 'starargs':
                    star_val, _ = runtoken(arg_node['value'], env)
                    if isinstance(star_val, KeiList):
                        args.extend(star_val.items)
                    elif isinstance(star_val, (list, tuple)):
                        args.extend(star_val)
                    else:
                        args.append(star_val)

                elif arg_node['type'] == 'starkwargs':
                    star_val, _ = runtoken(arg_node['value'], env)
                    if isinstance(star_val, KeiDict):
                        for k, v in star_val.items.items():
                            key = k.value if isinstance(k, KeiString) else str(k)
                            kwargs[key] = v
                    elif isinstance(star_val, dict):
                        kwargs.update(star_val)

            # ----- 2. 处理 call -----
            if node['type'] == 'call':
                name = node['name']
                stdlib.kei.setenv(env)

                # super 特殊处理
                if name == 'super':
                    if 'self' not in env:
                        raise KeiError("NameError", "super 只能在类方法中使用")
                    instance = env['self']
                    if not isinstance(instance, KeiInstance):
                        raise KeiError("NameError", "super 需要 self 实例")

                    current_class = instance._class
                    parent_name = current_class.class_obj.get('parent')
                    if not parent_name:
                        raise KeiError("NameError", "当前类没有父类")

                    parent_class = env.get(parent_name)
                    if not parent_class:
                        raise KeiError("NameError", f"父类 {parent_name} 未找到")

                    init_method = parent_class.class_obj['methods_map'].get('__init__')
                    if init_method:
                        new_env = {k: v for k, v in init_method.get('closure', {}).items()
                                  if k not in ['__builtins__', '__env__']}
                        new_env['self'] = instance
                        for i, p in enumerate(init_method['params'][1:]):
                            if i < len(args):
                                new_env[p] = args[i]
                            elif p in kwargs:
                                new_env[p] = kwargs[p]
                        for stmt in init_method['body']:
                            val, is_return = runtoken(stmt, new_env)
                            if is_return:
                                break
                    return null, False

                # 带点的方法调用 (obj.method)
                if '.' in name:
                    parts = name.split('.')
                    current = env.get(parts[0])
                    if current is None:
                        return undefined, False

                    for part in parts[1:-1]:
                        if isinstance(current, KeiBase):
                            current = current[part]
                        elif isinstance(current, dict):
                            current = current.get(part, undefined)
                        else:
                            current = getattr(current, part, undefined)
                        if current is undefined:
                            raise KeiError("NameError", f"属性 {part} 未定义")

                    method_name = parts[-1]
                    method = current[method_name] if isinstance(current, KeiBase) else getattr(current, method_name, None)

                    if method is not None and callable(method):
                        if isinstance(method, KeiFunction):
                            result = method(linecode=call_source, *args, **kwargs)
                        else:
                            # Python 原生方法调用 - 参数检查
                            try:
                                sig = inspect.signature(method)
                                required = [p for p in sig.parameters.values() if p.default == inspect.Parameter.empty and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)]
                                if len(args) + len(kwargs) < len(required):
                                    missing = []
                                    for p in required:
                                        if p.name not in kwargs and len(args) <= required.index(p):
                                            missing.append(p.name)
                                    if missing:
                                        raise KeiError("TypeError", f"{method_name}() 缺少参数: {', '.join(missing)}")
                            except (ValueError, TypeError):
                                pass
                            result = method(*args, **kwargs)
                        return result, False
                    raise KeiError("NameError", f"对象没有方法 {method_name}")

                # 普通函数/类调用
                if name in env:
                    func_obj = env[name]

                    if isinstance(func_obj, KeiInstance) and hasattr(func_obj, '__call__'):
                        result = func_obj.__call__(*args, **kwargs)
                        return result, False

                    if isinstance(func_obj, KeiClass):
                        instance = func_obj(*args, **kwargs)
                        init_method = find_method(func_obj.class_obj, '__init__', env)
                        if init_method:
                            new_env = {'__parent__': init_method['closure'], 'self': instance}
                            new_env.update({k: v for k, v in init_method['closure'].items() if k != '__parent__'})
                            for i, p in enumerate(init_method['params'][1:]):
                                if i < len(args):
                                    new_env[p] = args[i]
                                elif p in kwargs:
                                    new_env[p] = kwargs[p]
                            for stmt in init_method['body']:
                                val, is_return = runtoken(stmt, new_env)
                                if is_return and val is not None:
                                    break
                        return instance, False

                    if isinstance(func_obj, KeiFunction):
                        return func_obj(linecode=call_source, *args, **kwargs), False

                    # Python 原生函数调用 - 参数检查
                    if callable(func_obj):
                        try:
                            sig = inspect.signature(func_obj)
                            required = [p for p in sig.parameters.values() if p.default == inspect.Parameter.empty and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)]
                            if len(args) + len(kwargs) < len(required):
                                missing = []
                                for p in required:
                                    if p.name not in kwargs and len(args) <= required.index(p):
                                        missing.append(p.name)
                                if missing:
                                    if len(missing) == 1:
                                        raise KeiError("TypeError", f"{name}() 缺少参数 '{missing[0]}'")
                                    else:
                                        raise KeiError("TypeError", f"{name}() 缺少参数: {', '.join(missing)}")
                        except (ValueError, TypeError):
                            pass
                        return func_obj(*args, **kwargs), False

                    raise KeiError("NameError", f"未知函数: {name}")

                raise KeiError("NameError", f"未知函数: {name}")

            # ----- 3. 处理 methodcall -----
            else:  # node['type'] == 'methodcall'
                obj = None
                method_name = None

                # 从新结构中获取 obj
                if 'obj' in node:
                    obj, _ = runtoken(node['obj'], env)
                    method_name = node.get('method')

                if obj is None:
                    raise KeiError("NameError", "对象未定义")
                if method_name is None:
                    if callable(obj):
                        result = obj(*args, **kwargs)
                        return result, False
                    else:
                        if obj is undefined:
                            raise KeiError("AttributeError", f"{content(type(runtoken(node['obj']['obj'], env)[0]))}对象没有属性{node['obj']['attr']}")
                        raise KeiError("TypeError", f"{obj} 不可调用")

                method = obj[method_name] if isinstance(obj, KeiBase) else getattr(obj, method_name, None)

                if method is undefined or not callable(method):
                    raise KeiError("SyntaxError", f"方法 {method_name} 调用失败")

                is_namespace_func = isinstance(obj, KeiNamespace) or (isinstance(obj, KeiDict) and method_name in obj.items)

                if isinstance(method, (KeiFunction, KeiMethod, KeiBoundMethod)):
                    if isinstance(method, KeiFunction):
                        params = method.func_obj['params']
                    else:
                        params = method.method_obj['params']

                    regular_params = []
                    star_param = starstar_param = None
                    for p in params:
                        if p.startswith('**'):
                            starstar_param = p[2:]
                        elif p.startswith('*'):
                            star_param = p[1:]
                        else:
                            regular_params.append(p)

                    if is_namespace_func:
                        if star_param:
                            result = method(linecode=call_source, *args, **kwargs)
                        elif starstar_param:
                            result = method(linecode=call_source, *args, **kwargs)
                        else:
                            call_args = []
                            remaining = kwargs.copy()
                            for i, p in enumerate(regular_params):
                                if i < len(args):
                                    call_args.append(args[i])
                                elif p in remaining:
                                    call_args.append(remaining.pop(p))
                                else:
                                    call_args.append(undefined)
                            if remaining:
                                raise KeiError("SyntaxError", f"方法 {method_name} 不接受关键字参数: {list(remaining.keys())}")
                            result = method(linecode=call_source, *call_args)
                        return result, False

                    is_bound = isinstance(method, KeiBoundMethod) or hasattr(method, '__self__')

                    if is_bound:
                        if star_param:
                            result = method(*args, **kwargs)
                        elif starstar_param:
                            result = method(*args, **kwargs)
                        else:
                            call_args = []
                            remaining = kwargs.copy()
                            for i, p in enumerate(regular_params):
                                if i < len(args):
                                    call_args.append(args[i])
                                elif p in remaining:
                                    call_args.append(remaining.pop(p))
                                else:
                                    call_args.append(undefined)
                            if remaining:
                                raise KeiError("SyntaxError", f"方法 {method_name} 不接受关键字参数: {list(remaining.keys())}")
                            result = method(*call_args)
                    else:
                        call_args = [obj]
                        remaining = kwargs.copy()
                        for i, p in enumerate(regular_params[1:]):
                            if i < len(args):
                                call_args.append(args[i])
                            elif p in remaining:
                                call_args.append(remaining.pop(p))
                            else:
                                call_args.append(undefined)
                        if remaining:
                            raise KeiError("SyntaxError", f"方法 {method_name} 不接受关键字参数: {list(remaining.keys())}")
                        result = method(*call_args)

                    return result, False

                # Python 原生方法调用 - 参数检查
                if callable(method):
                    try:
                        sig = inspect.signature(method)
                        required = [p for p in sig.parameters.values() if p.default == inspect.Parameter.empty and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)]
                        if len(args) + len(kwargs) < len(required):
                            missing = []
                            for p in required:
                                if p.name not in kwargs and len(args) <= required.index(p):
                                    missing.append(p.name)
                            if missing:
                                if len(missing) == 1:
                                    raise KeiError("TypeError", f"{method_name}() 缺少参数 '{missing[0]}'")
                                else:
                                    raise KeiError("TypeError", f"{method_name}() 缺少参数: {', '.join(missing)}")
                    except (ValueError, TypeError):
                        pass
                    return method(*args, **kwargs), False

                return method(*args, **kwargs), False

        # ========== 赋值 ==========
        if node['type'] == 'assign':
            val, flag = runtoken(node['right'], env)
            left = node['left']

            if left['type'] == 'multiassign':
                vars_list = left['vars']

                if isinstance(val, tuple):
                    for i, var in enumerate(vars_list):
                        if var == '_':
                            continue
                        if i < len(val):
                            env[var] = val[i]
                        else:
                            if not env.get("__undefined__"):
                                raise KeiError("SyntaxError", f"多变量赋值缺少值: 变量 {var} 没有对应的值")
                            env[var] = undefined

                    return KeiList([v for v in val]), flag

                elif isinstance(val, KeiList):
                    items = val.items
                    for i, var in enumerate(vars_list):
                        if var == '_':
                            continue
                        if i < len(items):
                            env[var] = items[i]
                        else:
                            if not env.get("__undefined__"):
                                raise KeiError("SyntaxError", f"多变量赋值缺少值: 变量 {var} 没有对应的值")
                            env[var] = undefined
                    return val, flag

            # 处理 * 赋值
            elif left['type'] == 'star_target' or left['type'] == 'starassign':
                name = left['name']
                # 把右边变成列表
                if isinstance(val, KeiList):
                    env[name] = val
                elif isinstance(val, (list, tuple)):
                    env[name] = KeiList(list(val))
                else:
                    env[name] = KeiList([val])
                return val, flag

            # 处理 ** 赋值
            elif left['type'] == 'starstar_target' or left['type'] == 'starstarassign':
                name = left['name']
                if isinstance(val, KeiDict):
                    env[name] = val
                elif isinstance(val, dict):
                    env[name] = KeiDict(val)
                else:
                    raise KeiError("TypeError", f"** 赋值右边必须是字典，得到 {type(val)}")
                return val, flag

            elif left['type'] == 'name':
                parts = left['value'].split('.')

                if len(parts) == 2 and parts[0] == 'self':
                    if 'self' not in env:
                        raise KeiError("NameError", "self 只能在类方法中使用")
                    instance = env['self']
                    instance[parts[1]] = val

                elif len(parts) > 1:
                    obj = env
                    for part in parts[:-1]:
                        if isinstance(obj, KeiBase):
                            obj = obj[part]
                        elif isinstance(obj, dict):
                            obj = obj.get(part)
                        else:
                            obj = getattr(obj, part)

                    if isinstance(obj, KeiBase):
                        obj[parts[-1]] = val
                    elif isinstance(obj, dict):
                        obj[parts[-1]] = val
                    else:
                        setattr(obj, parts[-1], val)

                else:
                    name = parts[0]
                    if name in env.get('__globals__', []):
                        target = env
                        while target.get('__parent__') is not None:
                            target = target['__parent__']
                        target[name] = val
                    else:
                        env[name] = val

            elif left['type'] == 'index':
                obj, _ = runtoken(left['obj'], env)
                index, _ = runtoken(left['index'], env)

                if isinstance(obj, KeiBase):
                    if isinstance(index, KeiInt):
                        obj[index.value] = val
                    else:
                        obj[index] = val
                elif isinstance(obj, (list, dict)):
                    idx = index.value if isinstance(index, KeiInt) else index
                    obj[idx] = val
                else:
                    raise KeiError("TypeError", f"无法对 {type(obj)} 进行索引赋值")

            elif left['type'] == 'attr':
                obj, _ = runtoken(left['obj'], env)
                attr = left['attr']

                if isinstance(obj, KeiBase):
                    obj[attr] = val
                elif isinstance(obj, dict):
                    obj[attr] = val
                else:
                    setattr(obj, attr, val)

            elif left['type'] == 'slice':
                obj, _ = runtoken(left['obj'], env)
                start, _ = runtoken(left['start'], env) if left['start'] else (None, False)
                end, _ = runtoken(left['end'], env) if left['end'] else (None, False)
                step, _ = runtoken(left['step'], env) if left['step'] else (None, False)

                # 转换索引为 Python 值
                if isinstance(start, KeiInt):
                    start = start.value
                if isinstance(end, KeiInt):
                    end = end.value
                if isinstance(step, KeiInt):
                    step = step.value

                # 支持负数索引
                if isinstance(obj, KeiString):
                    length = len(obj.value)
                    if start is not None and start < 0:
                        start = length + start
                    if end is not None and end < 0:
                        end = length + end

                    # 把右边转成字符串
                    if isinstance(val, KeiString):
                        new_str = val.value
                    else:
                        new_str = str(val)

                    # 执行切片替换
                    if start is None:
                        start = 0
                    if end is None:
                        end = length

                    obj.value = obj.value[:start] + new_str + obj.value[end:]

                elif isinstance(obj, KeiList):
                    # 列表切片赋值
                    if start is None:
                        start = 0
                    if end is None:
                        end = len(obj.items)

                    # 把右边转成列表
                    if isinstance(val, KeiList):
                        new_items = val.items
                    else:
                        new_items = [val]

                    obj.items = obj.items[:start] + new_items + obj.items[end:]

                else:
                    raise KeiError("TypeError", f"不支持对 {type(obj)} 进行切片赋值")

                return val, flag

            else:
                raise KeiError("TypeError", f"无效的赋值目标: {left['obj']['value']}")

            return val, flag

        # ========== return 语句 ==========
        if node['type'] == 'return':
            if node['value'] is None:
                return None, True
            val, flag = runtoken(node['value'], env)
            return val, True

        # ========== if/unless 语句 ==========
        if node['type'] in {'if', 'unless'}:
            cond_val, cond_flag = runtoken(node['cond'], env)
            if cond_flag:
                return cond_val, True

            should_execute = cond_val if node['type'] == 'if' else not cond_val

            if should_execute:
                for stmt in node['body']:
                    val, is_return = runtoken(stmt, env)
                    if is_return:
                        return val, True
            else:
                if node['type'] == 'if':
                    for elif_node in node.get('elif_chain', []):
                        elif_cond, elif_flag = runtoken(elif_node['cond'], env)
                        if elif_flag:
                            return elif_cond, True
                        if elif_cond:
                            for stmt in elif_node['body']:
                                val, is_return = runtoken(stmt, env)
                                if is_return:
                                    return val, True
                            break
                    else:
                        if node.get('else_body'):
                            for stmt in node['else_body']:
                                val, is_return = runtoken(stmt, env)
                                if is_return:
                                    return val, True
                else:
                    if node.get('else_body'):
                        for stmt in node['else_body']:
                            val, is_return = runtoken(stmt, env)
                            if is_return:
                                return val, True

            return None, False

        # ========== while/until 循环 ==========
        if node['type'] in {'while', 'until'}:
            while True:
                cond_val, cond_flag = runtoken(node['cond'], env)
                if cond_flag:
                    return cond_val, True

                should_continue = cond_val if node['type'] == 'while' else not cond_val
                if not should_continue:
                    break

                for stmt in node['body']:
                    val, is_return = runtoken(stmt, env)
                    if is_return:
                        if isinstance(val, tuple) and len(val) == 2:
                            signal, _ = val
                            if signal == 'break':
                                return None, False
                            elif signal == 'continue':
                                break
                        return val, True

            return None, False

        # ========== for 循环 ==========
        if node['type'] == 'for':
            vars_list = node['vars']
            iterable_val, _ = runtoken(node['iterable'], env)

            if iterable_val is None or iterable_val is undefined:
                return None, False

            if isinstance(iterable_val, KeiList):
                items = iterable_val.items
            elif isinstance(iterable_val, KeiString):
                items = [KeiString(c) for c in iterable_val.value]
            elif isinstance(iterable_val, KeiDict):
                items = []
                for k, v in iterable_val.items.items():
                    items.append(KeiList([KeiString(k), v]))
            elif isinstance(iterable_val, (list, tuple)):
                items = iterable_val
            else:
                try:
                    items = list(iterable_val)
                except:
                    items = [iterable_val]

            if len(vars_list) == 1:
                for item in items:
                    env[vars_list[0]] = item
                    for stmt in node['body']:
                        val, is_return = runtoken(stmt, env)
                        if is_return:
                            if isinstance(val, tuple) and len(val) == 2:
                                signal, _ = val
                                if signal == 'break':
                                    return None, False
                                elif signal == 'continue':
                                    break
                            return val, True
            else:
                for i, item in enumerate(items):
                    if len(vars_list) >= 1:
                        env[vars_list[0]] = KeiInt(i)

                    if len(vars_list) >= 2:
                        env[vars_list[1]] = item

                    if len(vars_list) > 2:
                        if isinstance(item, (list, tuple, KeiList)):
                            item_list = item.items if isinstance(item, KeiList) else item
                            for j in range(2, len(vars_list)):
                                if j-2 < len(item_list):
                                    env[vars_list[j]] = item_list[j-2]
                                else:
                                    env[vars_list[j]] = undefined
                        else:
                            for j in range(2, len(vars_list)):
                                env[vars_list[j]] = undefined

                    for stmt in node['body']:
                        val, is_return = runtoken(stmt, env)
                        if is_return:
                            if isinstance(val, tuple) and len(val) == 2:
                                signal, _ = val
                                if signal == 'break':
                                    return None, False
                                elif signal == 'continue':
                                    break
                            return val, True

            return None, False

        # ========== break/continue ==========
        if node['type'] in {'break', 'continue'}:
            return (node['type'], None), True

        # ========== 函数定义 ==========
        if node['type'] == 'function':
            global_names = []
            for stmt in node['body']:
                if stmt['type'] == 'global':
                    global_names.extend(stmt['names'])

            node.get('hint', None)

            func_obj = {
                'type': 'user_function',
                'name': node['name'],
                'params': node['params'],
                'defaults': node.get('defaults', {}),
                'body': node['body'],
                'globals': global_names,
                'closure': env,
                'typeassert': node.get('hint', None)
            }

            kei_func = KeiFunction(func_obj, env)

            if node.get('decorators'):
                for decorator_node in reversed(node['decorators']):
                    decorator, _ = runtoken(decorator_node, env)
                    if callable(decorator):
                        kei_func = decorator(kei_func)

            if node['name']:
                env[node['name']] = kei_func
            else:
                return kei_func, False

            return None, False

        # ========== 类定义 ==========
        if node['type'] == 'class':
            class_obj = {
                'type': 'class',
                'name': node['name'],
                'parent': node.get('parent'),
                'body': node['body'],  # 存储原始语句列表
                'methods': [],
                'attrs': {},  # 类属性
                'methods_map': {}
            }

            if class_obj['parent']:
                parent = env.get(class_obj['parent'])
                if parent is None or parent is undefined:
                    raise KeiError("NameError", f"父类 '{class_obj['parent']}' 未定义")
                if not isinstance(parent, KeiClass):
                    raise KeiError("TypeError", f"'{class_obj['parent']}' 不是类")
                # 继承父类的属性和方法
                class_obj['attrs'] = parent._class_attrs.copy()
                class_obj['methods_map'] = parent.class_obj['methods_map'].copy()

            # 遍历 body，根据语句类型分类
            for stmt in node['body']:
                if stmt['type'] == 'function':
                    # 是方法
                    method_obj = {
                        'type': 'user_function',
                        'name': stmt['name'],
                        'params': stmt['params'],
                        'body': stmt['body'],
                        'defaults': stmt.get('defaults', {}),
                        'decorators': stmt.get('decorators', []),
                        'is_property': False,
                        'is_method': True,
                        'closure': env
                    }
                    # 检查装饰器
                    if 'decorators' in stmt:
                        for dec in stmt['decorators']:
                            if dec['value'] == 'prop':
                                method_obj['is_property'] = True

                    class_obj['methods'].append(method_obj)
                    class_obj['methods_map'][stmt['name']] = method_obj

                elif stmt['type'] == 'assign':
                    # 是类属性赋值
                    if stmt['left']['type'] == 'name':
                        attr_name = stmt['left']['value']
                        # 计算属性值
                        attr_val, _ = runtoken(stmt['right'], env)
                        class_obj['attrs'][attr_name] = attr_val

            kei_class = KeiClass(class_obj, env)
            env[node['name']] = kei_class
            return None, False

        # ========== import 语句 ==========
        if node['type'] == 'import':
            try:
                for module_info in node['modules']:
                    full_module_name = module_info['module']
                    alias = module_info.get('alias')
                    is_wildcard = module_info.get('type') == 'wildcard'

                    assert isinstance(env.get("__path__", KeiList([])), KeiList), "__path__需要是一个列表"

                    __path__ = env.get("__path__", KeiList([])).items

                    full_module_name = full_module_name.replace('.', '/')

                    module_name = full_module_name.split("/")[-1]

                    # ==== 1. 先找 .kei 文件（KeiLang 模块）====
                    kei_files = [os.path.join(path, f"{full_module_name}.kei") for path in __path__]

                    for keifile in kei_files:
                        if os.path.isfile(keifile):
                            with open(keifile, "r", encoding="utf-8") as f:
                                code = f.read()

                            module_env = {
                                "__path__": KeiList(["."] + paths),
                                "__name__": KeiString(f"__{module_name}__"),
                                "__maxrecursion__": KeiInt(1024),
                                "__env__": KeiDict(env),
                                "__osname__": KeiString(platform.system().lower()),
                                "__precision__": KeiInt(28),
                                "__typeassert__": KeiBool(True),
                            }

                            module_env.update({
                                "__env__": module_env,
                            })

                            exec(code, module_env)  # KeiLang 的 exec

                            # 过滤掉 __ 开头的属性
                            module_dict = {}
                            for k, v in module_env.items():
                                if not k.startswith('__'):
                                    module_dict[k] = v

                            if is_wildcard:
                                for name, value in module_dict.items():
                                    env[name] = value
                            else:
                                name = alias or module_name
                                env[name] = KeiNamespace(name, module_dict)

                            return None, False

                    # ==== 2. 再找 .py 文件（Python 模块）====
                    py_files = [os.path.join(path, f"{full_module_name}.py") for path in __path__]

                    for pyfile in py_files:
                        if os.path.isfile(pyfile):
                            with open(pyfile, "r", encoding="utf-8") as f:
                                code = f.read()

                            module_env = {}
                            __py_exec__(code, module_env)  # Python 的 exec

                            # 过滤掉 __ 开头的属性
                            module_dict = {}
                            for k, v in module_env.items():
                                if not k.startswith('__'):
                                    module_dict[k] = v

                            if is_wildcard:
                                for name, value in module_dict.items():
                                    env[name] = value
                            else:
                                name = alias or full_module_name
                                env[name] = KeiNamespace(name, module_dict)

                            return None, False

                    # ==== 3. 都找不到就报错 ====
                    raise KeiError("ImportError", f"找不到模块: {full_module_name}")

                return None, False

            except Exception as e:
                raise KeiError("ImportError", f"导入模块失败: {e}")

        # ========== from ... import ... 语句 ==========
        if node['type'] == 'fromimport':
            module_name = node['module']
            imports = node['imports']

            assert isinstance(env.get("__path__", KeiList([])), KeiList), "__path__需要是一个列表"

            __path__ = env.get("__path__", KeiList([])).items

            module_path = module_name.replace('.', '/')
            module_short_name = module_path.split("/")[-1]

            module_env = None
            module_dict = None

            # ==== 1. 先找 .kei 文件（KeiLang 模块）====
            kei_files = [os.path.join(path, f"{module_path}.kei") for path in __path__]

            for keifile in kei_files:
                if os.path.isfile(keifile):
                    with open(keifile, "r", encoding="utf-8") as f:
                        code = f.read()

                    module_env = {
                        "__path__": KeiList(["."] + paths),
                        "__name__": KeiString(f"__{module_short_name}__"),
                        "__maxrecursion__": KeiInt(1024),
                        "__env__": KeiDict(env),
                        "__osname__": KeiString(platform.system().lower()),
                        "__precision__": KeiInt(28),
                        "__typeassert__": KeiBool(True),
                    }

                    module_env.update({
                        "__env__": module_env,
                    })

                    exec(code, module_env)  # KeiLang 的 exec
                    break

            # ==== 2. 再找 .py 文件（Python 模块）====
            if module_env is None:
                py_files = [os.path.join(path, f"{module_path}.py") for path in __path__]

                for pyfile in py_files:
                    if os.path.isfile(pyfile):
                        with open(pyfile, "r", encoding="utf-8") as f:
                            code = f.read()

                        module_env = {}
                        __py_exec__(code, module_env)  # Python 的 exec
                        break

            if module_env is None:
                raise KeiError("ImportError", f"找不到模块: {module_name}")

            # 过滤掉 __ 开头的属性，得到模块字典
            module_dict = {}
            for k, v in module_env.items():
                if not k.startswith('__'):
                    module_dict[k] = v
                elif k == '__all__':
                    # 保存 __all__ 供后面使用
                    module_dict['__all__'] = v

            # 获取 __all__（如果有）
            all_names = None
            if '__all__' in module_dict:
                all_val = module_dict['__all__']
                if isinstance(all_val, KeiList):
                    all_names = [item.value if isinstance(item, KeiString) else str(item) for item in all_val.items]
                elif isinstance(all_val, list):
                    all_names = [str(item) for item in all_val]
                elif isinstance(all_val, KeiString):
                    all_names = [all_val.value]
                elif isinstance(all_val, str):
                    all_names = [all_val]

            # 执行导入
            for imp in imports:
                if imp['type'] == 'wildcard':
                    # from module import *
                    if all_names is not None:
                        # 有 __all__，只导入 __all__ 中的
                        names_to_import = all_names
                    else:
                        # 没有 __all__，导入所有非私有
                        names_to_import = [k for k in module_dict.keys() if not k.startswith('__')]

                    for name in names_to_import:
                        if name in module_dict:
                            env[name] = module_dict[name]
                        elif name in module_env:
                            # 可能是在 __all__ 中但被过滤了（比如私有属性？）
                            env[name] = module_env[name]
                else:
                    # from module import name [as alias]
                    name = imp['name']
                    alias = imp['alias'] or name

                    if name in module_dict:
                        env[alias] = module_dict[name]
                    elif name in module_env:
                        env[alias] = module_env[name]
                    else:
                        raise KeiError("ImportError", f"无法从 {module_name} 导入 {name}")

            return None, False

        if node['type'] == 'del':
            for target in node['names']:  # 遍历 targets
                if target['type'] == 'name':
                    # 删除变量
                    name = target['value']
                    if name in env:
                        del env[name]
                elif target['type'] == 'index':
                    # 删除列表元素：del list[index]
                    obj, _ = runtoken(target['obj'], env)
                    index, _ = runtoken(target['index'], env)
                    if isinstance(obj, KeiList):
                        idx = index.value if isinstance(index, KeiInt) else int(index)
                        if 0 <= idx < len(obj.items):
                            del obj.items[idx]
                elif target['type'] == 'attr':
                    # 删除属性：del obj.attr
                    obj, _ = runtoken(target['obj'], env)
                    attr = target['attr']
                    if isinstance(obj, KeiBase):
                        if attr in obj._props:
                            del obj._props[attr]

            return None, False

        if node['type'] == 'raise':
            if len(node['names']) == 1:
                name = node['names'][0]
                text, _ = runtoken(name, env)

                if not isinstance(text, KeiError):
                    raise KeiError(text, text)
                else:
                    raise text

            elif len(node['names']) >= 2:
                types = runtoken(node['names'][0], env)[0]
                name = runtoken(node['names'][1], env)[0]

                if isinstance(types, KeiError):
                    types = str(types)

                if isinstance(name, KeiError):
                    name = str(name)

                raise KeiError(types, name)

            else:
                if env.get("__error__", None) is not None:
                    if isinstance(env['__error__'], (KeiList, list)):
                        err = env['__error__'][0]
                        if not isinstance(err, KeiError):
                            if isinstance(err, HASVALUE):
                                err = KeiError(err.value)
                            else:
                                raise KeiError("TypeError", f"无法使用{content(type(err))}抛出异常")

                        raise err
                    else:
                        raise KeiError("Runtime", "异常抛出失败: __error__栈不是list")

                else:
                    raise KeiError("Runtime", "没有异常可抛出")

        if node['type'] == 'use':
            if len(node['names']) >= 1:
                for name in node['names']:
                    if isinstance(env[name['value']], KeiNamespace):
                        env.update(env[name['value']].env)
                    else:
                        raise KeiError("TypeError", "use 需要 namespace")

            return None, False

        # ========== namespace 语句 ==========
        if node['type'] == 'namespace':
            ns_env = {}
            for stmt in node['body']:
                runtoken(stmt, ns_env)

            env[node['name']] = KeiNamespace(node['name'], ns_env)
            return None, False

        # ========== with 语句 ==========
        if node['type'] == 'with':
            cm, _ = runtoken(node['expr'], env)

            if hasattr(cm, '__enter__'):
                value = cm.__enter__()
            else:
                value = None

            if node['as_var']:
                env[node['as_var']] = value

            try:
                for stmt in node['body']:
                    val, is_return = runtoken(stmt, env)
                    if is_return:
                        result = val
                        break
            except KeiError as e:
                if hasattr(cm, '__exit__'):
                    exc_type, exc_value, traceback = sys.exc_info()
                    if cm.__exit__(exc_type, exc_value, traceback):
                        pass
                    else:
                        raise
                else:
                    raise
            else:
                if hasattr(cm, '__exit__'):
                    cm.__exit__(None, None, None)

            if node['as_var'] and node['as_var'] in env:
                del env[node['as_var']]

            return None, False

        if node['type'] == 'lambda':
            # 创建匿名函数对象
            func_obj = {
                'type': 'user_function',
                'name': None,  # 匿名函数没名字
                'params': node['params'],
                'defaults': {},
                'body': [{'type': 'return', 'value': node['body']}],  # 包装成 return
                'globals': [],
                'closure': env,
            }
            return KeiFunction(func_obj, env), False

        # ========== try/catch/finally 语句 ==========
        if node['type'] == 'try':
            try:
                __kei__.catch.append(True)
                for stmt in node['body']:
                    val, is_return = runtoken(stmt, env)
                    if is_return:
                        if node['finallybody']:
                            for f_stmt in node['finallybody']:
                                f_val, f_is_return = runtoken(f_stmt, env)
                                if f_is_return:
                                    return f_val, True
                        return val, True

            except Exception as e:
                try:
                    if node['catchbody'] is not None:
                        old_e = env.get(node['var']) if node['var'] else None

                        if isinstance(e, KeiError):
                            err_obj = KeiError(e.types, e.value)
                        else:
                            err_obj = KeiError(type(e).__name__, str(e))

                        if node['var']:
                            env[node['var']] = err_obj

                        env.setdefault('__error__', []).append(err_obj)

                        for stmt in node['catchbody']:
                            val, is_return = runtoken(stmt, env)
                            if env[node['var']]:
                                env['__error__'][-1] = env[node['var']]

                            if is_return:
                                if node['var']:
                                    if old_e is not None:
                                        env[node['var']] = old_e
                                    else:
                                        del env[node['var']]

                                if node['finallybody']:
                                    for f_stmt in node['finallybody']:
                                        f_val, f_is_return = runtoken(f_stmt, env)
                                        if f_is_return:
                                            return f_val, True

                                return val, True

                        env['__error__'].pop()

                        if node['var']:
                            if old_e is not None:
                                env[node['var']] = old_e
                            else:
                                del env[node['var']]

                    if node['finallybody']:
                        for f_stmt in node['finallybody']:
                            f_val, f_is_return = runtoken(f_stmt, env)
                            if f_is_return:
                                return f_val, True
                except:
                    raise

            else:
                if node['finallybody']:
                    for f_stmt in node['finallybody']:
                        f_val, f_is_return = runtoken(f_stmt, env)
                        if f_is_return:
                            return f_val, True

            finally:
                __kei__.catch.pop()

            return None, False

        # ========== global 语句 ==========
        if node['type'] == 'global':
            return None, False

        # ========== 类型断气 ==========
        if node['type'] == 'typeassert':
            val, flag = runtoken(node['expr'], env)
            hint = runtoken(node['hint'], env)[0]

            if bool(env.get("__typeassert__")):
                # 类型检查
                if isinstance(hint, KeiList):
                    for h in hint.items:
                        if type(val) is KeiInt and h is KeiFloat:
                            break

                        if not isinstance(h, type):
                            h = type(h)

                        if (isinstance(val, h) or (isinstance(val, type) and issubclass(val, h))):
                            break
                    else:
                        raise KeiError("TypeError", f"类型错误: 期望 {content(hint)}, 得到 {content(type(val))}")

                else:
                    if type(val) is KeiInt and hint is KeiFloat:
                        return val, flag

                    if not isinstance(hint, type):
                        hint = type(hint)

                    if not (isinstance(val, hint) or (isinstance(val, type) and issubclass(val, hint))):
                        raise KeiError("TypeError", f"类型错误: 期望 {content(hint)}, 得到 {content(type(val))}")

            return val, flag

        raise KeiError("RuntimeError", f"未知的节点: {node['type']}")

    try:
        if type(__kei__.step) is int:
            if __kei__.step <= (node.get('linenum', -1)+1):
                if __kei__.step != (node.get('linenum', -1)+1):
                    print(f"  % \033[31m错过断点行号{__kei__.step}继续执行\033[0m")
                else:
                    __kei__.step = True

        if __kei__.step and type(__kei__.step) not in [int, str] and node.get('source', None) is not None:
            while True:
                import copy

                try:
                    save_env = copy.deepcopy(env)
                except:
                    try:
                        save_env = copy.copy(env)
                    except:
                        save_env = env.copy()

                # 使用复制的env最大防止污染环境
                names = getname(node, save_env)

                maxline = int(str(stdlib.kei.cnlen(max([i.strip() for i in __kei__.code], key=stdlib.kei.cnlen) if __kei__.code is not None else None).value))

                first = __kei__.stack[0] if __kei__.stack else None

                prompt = f"--> \033[94m{node.get('source').strip()}\033[0m"
                prompt = (prompt +
                          ((maxline + 3) - int(str(stdlib.kei.cnlen(node.get('source').strip()).value))) * " " +
                          (f"[{node.get('linenum', -1)+1}]"
                          if type(__kei__.step) is not str and __kei__.step is not stdlib.kei.breakpoint else
                          f"{{{node.get('linenum', -1)+1}}}") +
                          (" \033[95m" + (' / '.join(__kei__.stack if type(first) is not tuple else [s[0] for s in __kei__.stack]) or '<global>') + "\033[0m") +
                          ' \033[34;2m' +
                          ('; '.join([f"{n} = {content(v, _in_container=True)}" for n, v in names])) +
                          '\033[0m' +
                          "\n:")

                if __kei__.step == "breakpoint": __kei__.step = True

                cmd = input(prompt)

                print("\033[1A\033[2K\033[1A\r")

                if not cmd:
                    break

                elif cmd == "c":
                    import repl
                    __kei__.step = False

                    try:
                        __kei__.error = False
                        repl.main(True)
                    except KeiError as e:
                        __kei__.error = True
                        __kei__.repl = False
                        globals()['source'] = e.code
                        raise
                    finally:
                        __kei__.error = True
                        __kei__.repl = False
                        __kei__.step = True

                elif cmd.startswith("q"):
                    sys.exit(0)

                elif cmd.startswith("v"):
                    # 获取所有用户变量
                    vars_to_show = {k: v for k, v in env.items()
                                   if not str(k).startswith('__')}

                    if vars_to_show:
                        # 找出最长的变量名
                        max_name_len = max(len(str(k)) for k in vars_to_show.keys())

                        # 对齐打印
                        for k, v in vars_to_show.items():
                            name = str(k)
                            value = content(v, _in_container=True)
                            # 格式化：变量名左对齐，值用颜色
                            print(f"  \033[36m{name:<{max_name_len}}\033[0m = \033[33m{value}\033[0m")
                    else:
                        print("  (无变量)")

                elif cmd.startswith('n'):
                    if cmd[2:]:
                        __kei__.step = cmd[2:]
                    else:
                        __kei__.step = None
                    break

                elif cmd.startswith("l"):
                    if __kei__.code is None:
                        print("  没有可显示的代码")
                    else:
                        line_num = node.get('linenum', -1)+1
                        if cmd[1:]:
                            if cmd[1] == "a":
                                start = 0
                                end   = len(__kei__.code)
                            else:
                                try:
                                    start = max(0, line_num - (int(cmd[1:]))-1)
                                except:
                                    print(f"  % \033[31m{cmd}需要整数参数\033[0m")
                                    continue

                                end = min(len(__kei__.code), line_num + int(cmd[1:]))
                        else:
                            start = max(0, line_num - 6)  # 显示前后5行
                            end = min(len(__kei__.code), line_num + 5)

                        for i in range(start, end):
                            marker = " \033[33m>\033[0m" if i == line_num - 1 else "  "  # line_num 是 1-based
                            print(f"{marker} {i+1}: {__kei__.code[i]}")

                elif cmd.startswith("k"):
                    return None, False

                elif cmd.startswith("b"):
                    try:
                        __kei__.step = int(cmd[1:])
                        break
                    except:
                        print(f"  % \033[31m{cmd}需要整数参数\033[0m")

                elif cmd.startswith("u "):
                    if cmd[2:]:
                        cmd = cmd[2:].split()
                        for c in cmd:
                            try:
                                del env[c]
                            except:
                                print(f"  % \033[31m变量{c}不存在\033[0m")
                    else:
                        print(f"  % \033[31m\"u\"需要变量名称\033[0m")

                elif cmd.startswith("p "):
                    if cmd[2:]:
                        cmd = cmd[2:].split()
                        for c in cmd:
                            try:
                                print(f"  \033[36m{c}\033[0m = \033[33m{env[c]}\033[0m")
                            except:
                                print(f"  % \033[31m变量{c}不存在\033[0m")
                    else:
                        print(f"  % \033[31m\"p\"需要变量名称\033[0m")

                elif cmd.startswith("t "):
                    __kei__.var = cmd[2:].split()

                elif cmd.startswith("h"):
                    print("Kei Debugger (KDB)")
                    print("  \033[33mq\033[0m - \033[36m退出\033[0m")
                    print("  \033[33mc\033[0m - \033[36m执行一行代码\033[0m")
                    print("  \033[33mv\033[0m - \033[36m查看全部变量(除了下划线开头的变量)\033[0m")
                    print("  \033[33mn\033[0m - \033[36m执行代码到下一个breakpoint()\033[0m")
                    print("  \033[33mk\033[0m - \033[36m跳过当前行\033[0m")
                    print("  \033[33mu\033[0m - \033[36m删除env的变量\033[0m")
                    print("  \033[33mp\033[0m - \033[36m打印变量\033[0m")
                    print("  \033[33ml\033[0m - \033[36m显示附近的代码\033[0m")
                    print("  \033[33mt\033[0m - \033[36m持续跟踪变量\033[0m")
                    print("  \033[33mb\033[0m - \033[36m执行到指定的行\033[0m")
                    print("  \033[33mh\033[0m - \033[36m显示此帮助\033[0m")
                    print()

                else:
                    print(f"  % \033[31m未知的指令: {cmd}, 尝试使用\"h\"获取帮助\033[0m")

            import copy

            try:
                oldenv = copy.deepcopy(env)
            except:
                try:
                    oldenv = copy.copy(env)
                except:
                    oldenv = env.copy()

            result = runtokentemp()
            try:
                newenv = copy.deepcopy(env)
            except:
                try:
                    newenv = copy.copy(env)
                except:
                    newenv = env.copy()

            rmvar, addvar, changevar = dict_diff(newenv, oldenv)
            if addvar:
                print(f"  \033[32m+ {' and '.join(addvar)}\033[0m")
            if rmvar:
                print(f"  \033[31m- {' and '.join(rmvar)}\033[0m")
            if changevar:
                print(f"  \033[33m& {' and '.join(changevar)}\033[0m")

            if __kei__.var:
                for v in __kei__.var:
                    if not v:
                        continue
                    try:
                        print(f"  \033[36m{v}\033[0m = \033[33m{env[v]}\033[0m")
                    except:
                        print(f"  % \033[31m变量{v}不存在\033[0m")

        else:
            result = runtokentemp()

        return result

    except Exception as e:
        if __kei__.catch or not __kei__.error:
            raise

        # 错误类型映射
        error_config = {
            ZeroDivisionError: ("ZeroDivisionError", "无法对 0 进行除法"),
            OverflowError: ("OverflowError", f"数值过大, 无法处理: {e}"),
            FloatingPointError: ("FloatingPointError", f"浮点运算错误: {e}"),
            ArithmeticError: ("ArithmeticError", f"运算错误: {e}"),
            IndexError: ("IndexError", f"索引超出范围: {e}"),
            KeyError: ("KeyError", f"键不存在: {e}"),
            LookupError: ("LookupError", f"查找错误: {e}"),
            TypeError: ("TypeError", f"类型错误: {e}"),
            ValueError: ("ValueError", f"值错误: {e}"),
            AttributeError: ("AttributeError", f"属性不存在: {e}"),
            UnboundLocalError: ("UnboundLocalError", f"局部变量未绑定: {e}"),
            NameError: ("NameError", f"名称未定义: {e}"),
            FileNotFoundError: ("NotFoundError", f"文件未找到: {e}"),
            PermissionError: ("PermissionError", f"权限不足无法访问文件: {e}"),
            IsADirectoryError: ("IsDirError", f"预期文件但得到目录: {e}"),
            NotADirectoryError: ("NotDirError", f"预期目录但得到文件: {e}"),
            FileExistsError: ("FileExistsError", f"文件已存在: {e}"),
            TimeoutError: ("TimeoutError", f"操作超时: {e}"),
            OSError: ("OSError", f"操作系统错误: {e}"),
            RecursionError: ("RecursionError", f"递归深度超过限制"),
            KeiError: (e.types, e.value) if isinstance(e, KeiError) else ()
        }

        # 获取错误类型
        for exc_type, (err_name, err_msg) in error_config.items():
            if isinstance(e, exc_type):
                error(
                    err_name if err_name is not err_msg else None,  # info
                    err_msg,
                    __kei__.stack.copy(),  # stack - 直接用 __kei__.stack
                    globals()['source'] if globals()['source'] is not None else node.get('source', None),
                    globals()['linenum']+1 if globals()['linenum'] is not None else node.get('linenum', -1)+1,
                    __kei__.get('file', '未知文件')
                )
                if not __kei__.repl:
                    sys.exit(1)
                else:
                    raise
        else:
            error(
                type(e).__name__,
                str(e),
                __kei__.stack.copy(),  # stack
                globals()['source'] if globals()['source'] is not None else node.get('source', None),
                globals()['linenum']+1 if globals()['linenum'] is not None else node.get('linenum', -1)+1,
                __kei__.get('file', '未知文件')
            )
            if not __kei__.repl:
                sys.exit(1)
            else:
                raise

def exec(code, env=None):
    if isinstance(code, KeiString):
        code = code.value

    if env is None:
        env = {}

    env.update({
        "__path__": KeiList(["."] + paths),
        "__name__": KeiString("__main__"),
        "__maxrecursion__": KeiInt(1024),
        "__env__": KeiDict(env),
        "__osname__": KeiString(platform.system().lower()),
        "__precision__": KeiInt(28),
        "__typeassert__": KeiBool(True),
    })

    for name, func in stdlib.func.items():
        env[name] = func

    tokens = token(code)
    tokens = ast(tokens)

    for node in tokens:
        ret = runtoken(node, env)[0]

    return env, ret

def execmain(code, env=None, step=False):
    if len(sys.argv) >= 3:
        cmd_args = []
        for arg in sys.argv[2:]:
            cmd_args.append(f"{arg}")

        code += f"\nmain({content(cmd_args)});"
    else:
        code += f"\nmain([]);"

    __kei__.step = step

    env, ret = exec(code, env)

    if isinstance(ret, KeiInt):
        return ret.value
    else:
        return 0

def main():
    try:
        if "-h" in sys.argv or "--help" in sys.argv:
            print("\033[1m" + r""" _  __    _ _
| |/ /___(_) |    __ _ _ __   __ _
| ' // _ \ | |   / _` | '_ \ / _` |
| . \  __/ | |__| (_| | | | | (_| |
|_|\_\___|_|_____\__,_|_| |_|\__, |
                             |___/ """ + "\033[0m")
            print(" " * 35 + __version__)
            print()
            print("\033[1m命令:\033[0m")
            print("  \033[33m<啥都木有>\033[0m - \033[36m进入REPL\033[0m")
            print("  \033[33m<文件名>\033[0m   - \033[36m运行Kei脚本\033[0m")
            print()
            print("\033[1m参数:\033[0m")
            print("  \033[33m-h/--help\033[0m  - \033[36m显示此帮助\033[0m")
            print("  \033[33m-d/--debug\033[0m - \033[36mDebug代码\033[0m")
            print("  \033[33m-c/--code\033[0m  - \033[36m直接执行代码\033[0m")
            print("  \033[33m--compile\033[0m  - \033[36m打印AST\033[0m")
            print()
            sys.exit(0)

        if len(sys.argv) >= 2:
            step       = False
            singlecode = False
            compile    = False
            if sys.argv[1] == "-d" or sys.argv[1] == "--debug":
                step = True
                sys.argv = [sys.argv[0]] + sys.argv[2:]

            if sys.argv[1] == "-c" or sys.argv[1] == "--code":
                singlecode = sys.argv[2:]

            if sys.argv[1] == "--compile":
                compile = True
                sys.argv = [sys.argv[0]] + sys.argv[2:]

            __kei__.file = sys.argv[1]

            if singlecode:
                for code in singlecode:
                    exec(code)
            else:
                if os.path.isfile(sys.argv[1]):
                    with open(sys.argv[1], "r", encoding="utf-8") as f:
                        filecontent = f.read()

                        if compile:
                            from pprint import pprint
                            pprint(ast(token(filecontent)))
                        else:
                            if step:
                                print(f"[Kei Debugger] \033[33;1m{os.path.abspath(sys.argv[1])}\033[0m")

                            try:
                                ret = execmain(filecontent, step=step)
                            except SystemExit as e:
                                if not step:
                                    raise
                                ret = e.code

                            if step:
                                print(f"[Kei Debugger] \033[33;1m程序返回: {ret}\033[0m")

                            return ret

                else:
                    raise KeiError("NotFoundError", f"未找到 {sys.argv[1]}")

        else:
            import repl
            repl.main()

    except KeyboardInterrupt:
        exit()

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        exit()

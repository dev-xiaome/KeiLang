#!/usr/bin/env python
"""KeiLang"""

from decimal import getcontext
from typing import List, Any, Optional
import platform
import inspect
import copy
import sys
import os

if __name__ == '__main__':
    sys.modules['kei'] = sys.modules['__main__']

__version__ = "1.7-20"

class KeiState:
    stack: List[Any]
    catch: list
    code: Optional[List[str]]
    repl: bool
    file: str
    step: object
    error: bool
    var: list
    env: dict
    recursion: int
    maxrecursion: int

    _instance: Optional['KeiState'] = None

    def __new__(cls) -> 'KeiState':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.stack = []
            cls._instance.catch = []
            cls._instance.code = None
            cls._instance.repl = False
            cls._instance.file = "未知文件"
            cls._instance.step = False
            cls._instance.error = True
            cls._instance.var = []
            cls._instance.env = {}
            cls._instance.recursion = 0
            cls._instance.maxrecursion = 1024

        return cls._instance

    def __init__(self) -> None:
        pass

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

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
__py_eval__ = eval

import stdlib
from object import *
from lib.kei2py import *

DEBUG = False

mapping = {}

keywords = {
   'class', 'namespace', 'if', 'while', 'fn', 'return', 'for',
   'else', 'elif', 'try', 'catch', 'with', 'import', 'break',
   'continue', 'global', 'raise', 'case', 'match', 'use', 'from'
}

sys.setrecursionlimit(1024)
getcontext().prec = 28

def check_python_call(func, args, kwargs, func_name):
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        return

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

    missing = []
    for i, p in enumerate(required_params):
        if p not in kwargs and i >= len(args):
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
    result = []
    seen = set()

    block_nodes = {
        'try', 'class', 'for', 'function', 'with', 'namespace',
        'if', 'while', 'unless', 'until', 'match'
    }

    def get_full_name(n):
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

            if n.get("type") == "name":
                name = n["value"]
                if name not in seen:
                    seen.add(name)
                    val = runtoken(n, env)[0]
                    result.append([name, val])

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

    if os.path.isfile(filename):
        print(f"File \033[33;1m{os.path.abspath(filename)}\033[0m")
    else:
        print(f"File \033[33;1m{filename}\033[0m")

    print(f"{space} ·")

    for s in stack:
        if type(s) is tuple:
            if s[1].strip():
                print(f"{space} | in \033[36;1m{s[0]}: {s[1].strip()}\033[0m")
            else:
                print(f"{space} | in \033[36;1m{s[0]}\033[0m")
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

    #import traceback
    #traceback.print_exc()

    if not __kei__.repl:
        sys.exit(1)

def dict_diff(d1, d2, path="", seen=None):
    if seen is None:
        seen = set()

    skip_keys = {'__env__', '__parent__', '__builtins__'}

    added = []
    removed = []
    changed = []

    for key in d1.keys():
        key_str = str(key)

        if key_str in skip_keys:
            continue

        full_path = f"{path}.{key_str}" if path else key_str

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

                if c == '|' and pos + 1 < length and codes[pos+1] == '>':
                    tokens.append("|>")
                    pos += 2
                    continue

                if c == '.' and pos + 2 < length and codes[pos+1] == '.' and codes[pos+2] == '.':
                    tokens.append("...")
                    pos += 3
                    continue

                if c == '*' and pos + 1 < length and codes[pos+1] == '*':
                    tokens.append("**")
                    pos += 2
                    continue

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

                if c == '+' and pos + 1 < length and codes[pos+1] == '=':
                    tokens.append("+=")
                    pos += 2
                    continue

                if c == '-' and pos + 1 < length and codes[pos+1] == '=':
                    tokens.append("-=")
                    pos += 2
                    continue

                if c == '*' and pos + 1 < length and codes[pos+1] == '=':
                    tokens.append("*=")
                    pos += 2
                    continue

                if c == '/' and pos + 1 < length and codes[pos+1] == '=':
                    tokens.append("/=")
                    pos += 2
                    continue

                if c == ':':
                    tokens.append(":")
                    pos += 1
                    continue

                if c == '{':
                    tokens.append("{")
                    pos += 1
                    continue
                if c == '}':
                    tokens.append("}")
                    pos += 1
                    continue

                if c == '[':
                    tokens.append("[")
                    pos += 1
                    continue
                if c == ']':
                    tokens.append("]")
                    pos += 1
                    continue

                if c == '(':
                    tokens.append("(")
                    pos += 1
                    continue
                if c == ')':
                    tokens.append(")")
                    pos += 1
                    continue

                if c in '"\'':
                    start = pos
                    quote = c
                    pos += 1
                    while pos < length and codes[pos] != quote:
                        if codes[pos] == '\\' and pos + 1 < length:
                            pos += 2
                        else:
                            pos += 1

                    if pos >= length:
                        raise KeiError("SyntaxError", f"未闭合的字符串: {codes[start:]}")

                    pos += 1
                    string = codes[start:pos]
                    tokens.append(('string', escape(string)))
                    continue

                if (c == 'r' and pos + 1 < length and codes[pos+1] == 'f') or \
                   (c == 'f' and pos + 1 < length and codes[pos+1] == 'r'):
                    temp_pos = pos + 2
                    while temp_pos < length and codes[temp_pos] in ' \n\t':
                        temp_pos += 1

                    if temp_pos < length and codes[temp_pos] in '"\'':
                        quote = codes[temp_pos]
                        pos = temp_pos + 1
                        start = pos
                        while pos < length and codes[pos] != quote:
                            pos += 1

                        if pos >= length:
                            raise KeiError("SyntaxError", f"未闭合的rf-string: {codes[start-3:]}")

                        pos += 1
                        string = codes[start-3:pos]
                        tokens.append(('rfstring', string[2:]))
                        continue

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

                        if pos >= length:
                            raise KeiError("SyntaxError", f"未闭合的r-string: {codes[start-2:]}")

                        pos += 1
                        string = codes[start-2:pos]
                        tokens.append(('rstring', string[1:]))
                        continue

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

                        if pos >= length:
                            raise KeiError("SyntaxError", f"未闭合的f-string: {codes[start-2:]}")

                        pos += 1
                        string = codes[start-2:pos]
                        tokens.append(('fstring', escape(string[1:])))
                        continue

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

                if "0" <= c <= "9":
                    start = pos
                    has_dot = False
                    while pos < length:
                        if "0" <= codes[pos] <= "9" or codes[pos] == "_" or codes[pos].lower() == "e":
                            if codes[pos].lower() == "e":
                                if pos + 1 < length and codes[pos+1] in {"+", "-"}:
                                    pos += 2
                                else:
                                    pos += 1
                            else:
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

                if c in "<>!" and pos + 1 < length and codes[pos+1] == "=":
                    tokens.append(c + "=")
                    pos += 2
                    continue

                if c == "=" and pos + 1 < length and codes[pos+1] == "=":
                    tokens.append("==")
                    pos += 2
                    continue

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

                if c.isalpha() or c == '_':
                    start = pos
                    while pos < length and (codes[pos].isalnum() or codes[pos] == '_'):
                        pos += 1
                    word = codes[start:pos]
                    tokens.append(word)
                    continue

                if c in ' \n\t':
                    pos += 1
                    continue

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

        if thetoken == "|>":
            result.append({"type":"op", "value":"|>", 'linenum':linetokens[pos][1]})
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
                        print(f"[ERROR] 映射文件 \033[33;1m{filename}\033[0m 不存在")
                        sys.exit(1)

                    pos += newpos

            except Exception as e:
                print(f"\033[31m[ERROR]\033[0m 无法加载映射 \033[33;1m{filename}\033[0m: {e}")
                sys.exit(1)

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
            new_token = i.copy()

            if new_token['type'] in {'name', 'op', 'symbol'}:
                if new_token['value'] in mapping:
                    map_val = mapping[new_token['value']]
                    if type(map_val) is list:
                        if len(map_val) == 2:
                            new_token['type'] = map_val[0]
                            new_token['value'] = map_val[1]
                        else:
                            print(f"\033[31m[ERROR]\033[0m 无法加载映射: 格式错误")
                            sys.exit(1)
                    else:
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

def parse_block(tokens: list, pos: int, all_lines: list, linepos: int,
                start_token: dict | None = None, end_token: str = '}') -> tuple[list, int, int]:
    """解析花括号块

    Args:
        tokens: 当前行的token列表
        pos: 当前位置
        all_lines: 所有行的tokens
        linepos: 当前行号
        start_token: 开始token（如果为None，假设当前位置已经跳过'{'）
        end_token: 结束符号，默认'}'，也可用于其他块如']'

    Returns:
        (body_statements, new_pos, new_linepos)
    """
    body = []
    brace_count = 1

    # 如果提供了start_token且当前token是'{'，先跳过
    if start_token is not None:
        if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != start_token.get('value', '{'):
            raise KeiError("SyntaxError", f"需要 '{start_token.get('value', '{')}'")
        pos += 1

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

        if current_tokens[current_pos]["type"] == "symbol" and current_tokens[current_pos]["value"] == end_token:
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

    return body, current_pos, current_line

def parse_stmt(tokens: list, pos: int, all_lines: list | None = None, linepos: int = -1) -> tuple:
    """解析语句"""
    try:
        def stmt(tokens: list, pos: int, all_lines: list | None = None, linepos: int = -1) -> tuple:
            if all_lines is None:
                all_lines = [tokens]
                linepos = 0

            if pos >= len(tokens):
                return None, pos, linepos

            t = tokens[pos]
            source_line = __kei__.get('code', [''])[t['linenum']] if __kei__.get('code') else ''

            globals()['source'] = source_line
            globals()['linenum'] = t['linenum']

            # 结束符
            if t['type'] == 'symbol' and t['value'] == '}':
                return None, pos, linepos

            # 装饰器
            if t['type'] == 'op' and t['value'] == '@':
                return parse_decorator(tokens, pos, all_lines, linepos, source_line)

            # 语句分发
            stmt_handlers = {
                'try': parse_try_stmt,
                'class': parse_class_stmt,
                'for': parse_for_stmt,
                'fn': parse_fn_stmt,
                'import': parse_import_stmt,
                'from': parse_from_stmt,
                'break': lambda t,p,al,ln,sl: ({'type': 'break'}, p+1, ln),
                'continue': lambda t,p,al,ln,sl: ({'type': 'continue'}, p+1, ln),
                'return': parse_return_stmt,
                'with': parse_with_stmt,
                'namespace': parse_namespace_stmt,
                'global': parse_global_del_raise_use,
                'del': parse_global_del_raise_use,
                'raise': parse_global_del_raise_use,
                'use': parse_global_del_raise_use,
                'if': parse_if_while_stmt,
                'while': parse_if_while_stmt,
                'unless': parse_if_while_stmt,
                'until': parse_if_while_stmt,
                'match': parse_match_stmt,
            }

            if t['type'] == 'name' and t['value'] in stmt_handlers:
                return stmt_handlers[t['value']](tokens, pos, all_lines, linepos, source_line)

            # 复合赋值
            compound_op = find_compound_op(tokens, pos)
            if compound_op:
                return parse_compoundassign(tokens, pos, all_lines, linepos, compound_op, source_line)

            # 普通赋值
            assign_pos = find_assign_pos(tokens, pos)
            if assign_pos != -1:
                return parse_assign(tokens, pos, assign_pos, all_lines, linepos, source_line)

            # 表达式
            node, new_pos, linepos = parse_expr(tokens, pos, allow_assign=False, all_lines=all_lines, linepos=linepos)
            if node is None:
                if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '}':
                    return None, pos, linepos
                raise KeiError("SyntaxError", f"无效的语法: {tokens[pos]['value'] if pos < len(tokens) else 'EOF'}")

            return node, new_pos, linepos

        node, new_pos, linepos = stmt(tokens, pos, all_lines, linepos)
        node['source'] = __kei__.get('code', [''])[tokens[pos]['linenum']] if __kei__.get('code') else ''
        node['linenum'] = tokens[pos]['linenum']
        return node, new_pos, linepos

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

def parse_decorator(tokens: list, pos: int, all_lines: list, linepos: int, source_line: str) -> tuple:
    """解析装饰器"""
    decorators = []
    current_line = linepos
    current_pos = pos

    while current_line < len(all_lines) and current_pos < len(all_lines[current_line]):
        toke = all_lines[current_line][current_pos]
        if toke['type'] == 'op' and toke['value'] == '@':
            current_pos += 1
            if current_pos >= len(all_lines[current_line]):
                current_line += 1
                current_pos = 0
                if current_line >= len(all_lines):
                    raise KeiError("SyntaxError", "装饰器后面缺少表达式")

            decorator, new_pos, new_line = parse_expr(all_lines[current_line], current_pos, all_lines=all_lines, linepos=current_line)
            decorators.append(decorator)

            if new_pos < len(all_lines[current_line]):
                current_pos = new_pos
            else:
                current_line += 1
                current_pos = 0

            # 跳过分号
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

def parse_try_stmt(tokens: list, pos: int, all_lines: list, linepos: int, source_line: str) -> tuple:
    """解析 try 语句"""
    pos += 1

    # try 块
    try_body, pos, linepos = parse_block(tokens, pos, all_lines, linepos, {'type': 'symbol', 'value': '{'})

    # catch 块
    var = None
    catch_body = None
    if linepos < len(all_lines) and pos < len(all_lines[linepos]):
        next_token = all_lines[linepos][pos]
        if next_token['type'] == 'name' and next_token['value'] == 'catch':
            pos += 1
            if pos < len(all_lines[linepos]) and all_lines[linepos][pos]['type'] == 'name':
                var = all_lines[linepos][pos]['value']
                pos += 1
            catch_body, pos, linepos = parse_block(all_lines[linepos], pos, all_lines, linepos, {'type': 'symbol', 'value': '{'})

    # finally 块
    finally_body = None
    if linepos < len(all_lines) and pos < len(all_lines[linepos]):
        next_token = all_lines[linepos][pos]
        if next_token['type'] == 'name' and next_token['value'] == 'finally':
            pos += 1
            finally_body, pos, linepos = parse_block(all_lines[linepos], pos, all_lines, linepos, {'type': 'symbol', 'value': '{'})

    node = {
        'type': 'try',
        'body': try_body,
        'var': var,
        'catchbody': catch_body,
        'finallybody': finally_body,
    }
    return node, pos, linepos

def parse_class_stmt(tokens: list, pos: int, all_lines: list, linepos: int, source_line: str) -> tuple:
    """解析 class 语句"""
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

    body, pos, linepos = parse_block(tokens, pos, all_lines, linepos, {'type': 'symbol', 'value': '{'})

    node = {
        'type': 'class',
        'name': class_name,
        'parent': parent_class,
        'body': body,
    }
    return node, pos, linepos

def parse_for_stmt(tokens: list, pos: int, all_lines: list, linepos: int, source_line: str) -> tuple:
    """解析 for 语句"""
    pos += 1

    # 解析变量列表
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

    body, pos, linepos = parse_block(tokens, pos, all_lines, linepos, {'type': 'symbol', 'value': '{'})

    node = {
        'type': 'for',
        'vars': vars,
        'iterable': iterable,
        'body': body,
    }
    return node, pos, linepos

def parse_fn_stmt(tokens: list, pos: int, all_lines: list, linepos: int, source_line: str) -> tuple:
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
        type_hints = {}

        while pos < len(tokens) and not (tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ')'):
            if tokens[pos]['type'] == 'name':
                param_name = tokens[pos]['value']
                pos += 1

                if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ':':
                    pos += 1

                    type_node, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)
                    type_hints[param_name] = type_node

                # 检查默认值
                if pos < len(tokens) and tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '=':
                    pos += 1
                    default_val, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)  # 解析 "Hello"
                    defaults[param_name] = default_val  # 存到 "x" 的默认值

                params.append(param_name)  # 只添加一次 "x"

            elif tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '*':
                pos += 1
                if pos < len(tokens) and tokens[pos]['type'] == 'name':
                    params.append('*' + tokens[pos]['value'])
                    pos += 1
                else:
                    params.append('*')
            elif tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '**':
                pos += 1
                if pos < len(tokens) and tokens[pos]['type'] == 'name':
                    params.append('**' + tokens[pos]['value'])
                    pos += 1
                else:
                    params.append('**')
            elif tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
                pos += 1
            else:
                raise KeiError("SyntaxError", f"未知符号: {tokens[pos]['value']}")

        pos += 1

        hint = None
        if pos < len(tokens) and tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '->':
            pos += 1
            hint, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)

        if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '=>':
            pos += 1
            # 检查是否多返回值
            values = []
            while True:
                val, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)
                values.append(val)
                if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
                    pos += 1
                    continue
                break

            if len(values) == 1:
                body = [{'type': 'return', 'value': values[0], 'linenum': globals()['linenum'], 'source': globals()['source']}]
            else:
                body = [{'type': 'return', 'value': {'type': 'list', 'elements': values}, 'linenum': globals()['linenum'], 'source': globals()['source']}]
            __kei__.stack.pop()
            return {
                'type': 'function', 'name': func_name, 'params': params,
                'defaults': defaults, 'typehints': type_hints, 'hint': hint,
                'body': body,
            }, pos, linepos

        body, pos, linepos = parse_block(tokens, pos, all_lines, linepos, {'type': 'symbol', 'value': '{'})

        __kei__.stack.pop()
        return {
            'type': 'function', 'name': func_name, 'params': params,
            'defaults': defaults, 'typehints': type_hints, 'hint': hint,
            'body': body,
        }, pos, linepos
    except:
        __kei__.stack.pop()
        raise

def parse_if_while_stmt(tokens: list, pos: int, all_lines: list, linepos: int, source_line: str) -> tuple:
    """解析 if/while/unless/until 语句"""
    stmt_type = tokens[pos]['value']
    pos += 1

    cond, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)

    body, pos, linepos = parse_block(tokens, pos, all_lines, linepos, {'type': 'symbol', 'value': '{'})

    node = {
        'type': stmt_type,
        'cond': cond,
        'body': body,
    }

    # if/unless 需要处理 elif/else
    if stmt_type in {'if', 'unless'}:
        elif_chain = []
        else_body = None

        while linepos < len(all_lines) and pos < len(all_lines[linepos]):
            # 跳过分号
            while pos < len(all_lines[linepos]) and all_lines[linepos][pos]['type'] == 'op' and all_lines[linepos][pos]['value'] == ';':
                pos += 1
            if pos >= len(all_lines[linepos]):
                linepos += 1
                pos = 0
                if linepos >= len(all_lines):
                    break
                continue

            next_token = all_lines[linepos][pos]

            if next_token['type'] == 'name' and next_token['value'] == 'elif':
                pos += 1
                elif_cond, pos, linepos = parse_expr(all_lines[linepos], pos, all_lines=all_lines, linepos=linepos)
                elif_body, pos, linepos = parse_block(all_lines[linepos], pos, all_lines, linepos, {'type': 'symbol', 'value': '{'})
                elif_chain.append({'cond': elif_cond, 'body': elif_body})

            elif next_token['type'] == 'name' and next_token['value'] == 'else':
                pos += 1
                else_body, pos, linepos = parse_block(all_lines[linepos], pos, all_lines, linepos, {'type': 'symbol', 'value': '{'})
                break

            else:
                break

        node['elif_chain'] = elif_chain
        node['else_body'] = else_body

    return node, pos, linepos

def parse_match_stmt(tokens: list, pos: int, all_lines: list, linepos: int, source_line: str) -> tuple:
    """解析 match 语句"""
    pos += 1

    value_expr, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)

    if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != '{':
        raise KeiError("SyntaxError", "match 后面需要 {")
    pos += 1

    arms = []
    current_line = linepos
    current_pos = pos

    while True:
        # 跳过空行和分号
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

            # 解析 pattern（支持 |）
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

            # case body
            body, current_pos, current_line = parse_block(all_lines[current_line], current_pos, all_lines, current_line, {'type': 'symbol', 'value': '{'})
            arms.append({'patterns': patterns, 'body': body})

        elif all_lines[current_line][current_pos]['type'] == 'symbol' and all_lines[current_line][current_pos]['value'] == '}':
            current_pos += 1
            break

        else:
            raise KeiError("SyntaxError", "match 块内只能有 case 语句")

    node = {
        'type': 'match',
        'value': value_expr,
        'arms': arms,
    }
    return node, current_pos, current_line

def parse_return_stmt(tokens: list, pos: int, all_lines: list, linepos: int, source_line: str) -> tuple:
    """解析 return 语句"""
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

def parse_with_stmt(tokens: list, pos: int, all_lines: list, linepos: int, source_line: str) -> tuple:
    """解析 with 语句"""
    pos += 1
    expr, pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)

    as_var = None
    if pos < len(tokens) and tokens[pos]['type'] == 'name' and tokens[pos]['value'] == 'as':
        pos += 1
        if pos >= len(tokens) or tokens[pos]['type'] != 'name':
            raise KeiError("SyntaxError", "as 后面需要变量名")
        as_var = tokens[pos]['value']
        pos += 1

    body, pos, linepos = parse_block(tokens, pos, all_lines, linepos, {'type': 'symbol', 'value': '{'})

    node = {
        'type': 'with',
        'expr': expr,
        'as_var': as_var,
        'body': body,
    }
    return node, pos, linepos

def parse_namespace_stmt(tokens: list, pos: int, all_lines: list, linepos: int, source_line: str) -> tuple:
    """解析 namespace 语句"""
    pos += 1

    if pos >= len(tokens) or tokens[pos]['type'] != 'name':
        raise KeiError("SyntaxError", "命名空间需要名字")
    ns_name = tokens[pos]['value']
    if ns_name in keywords:
        raise KeiError("SyntaxError", f"无法使用关键字 '{ns_name}' 作为命名空间名")
    pos += 1

    body, pos, linepos = parse_block(tokens, pos, all_lines, linepos, {'type': 'symbol', 'value': '{'})

    node = {
        'type': 'namespace',
        'name': ns_name,
        'body': body,
    }
    return node, pos, linepos

def parse_global_del_raise_use(tokens: list, pos: int, all_lines: list, linepos: int, source_line: str) -> tuple:
    """解析 global/del/raise/use 语句"""
    stmt_type = tokens[pos]['value']
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

    if not targets and stmt_type != "raise":
        raise KeiError("SyntaxError", f"{stmt_type} 需要至少一个参数")

    if len(targets) > 2 and stmt_type == "raise":
        raise KeiError("SyntaxError", "raise 只能抛出一个错误字符串和可选类型")

    node = {
        'type': stmt_type,
        'names': targets,
    }
    return node, pos, linepos

def parse_import_stmt(tokens: list, pos: int, all_lines: list, linepos: int, source_line: str) -> tuple:
    """解析 import 语句"""
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
                modules.append({'type': 'wildcard', 'module': module_name, 'alias': alias})
                pos += 2
            else:
                modules.append({'type': 'normal', 'module': module_name, 'alias': alias})

        if pos < len(tokens) and tokens[pos].get('type') == 'symbol' and tokens[pos].get('value') == ',':
            pos += 1
        else:
            break

    node = {
        'type': 'import',
        'modules': modules,
    }
    return node, pos, linepos

def parse_from_stmt(tokens: list, pos: int, all_lines: list, linepos: int, source_line: str) -> tuple:
    """解析 from ... import 语句"""
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
        imports.append({'type': 'wildcard', 'name': None, 'alias': None})
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

                imports.append({'type': 'normal', 'name': name, 'alias': alias})

                if pos < len(tokens) and tokens[pos].get('type') == 'symbol' and tokens[pos].get('value') == ',':
                    pos += 1
                    continue
                else:
                    break
            else:
                break

    node = {
        'type': 'fromimport',
        'module': module_name,
        'imports': imports,
    }
    return node, pos, linepos

def find_compound_op(tokens: list, pos: int) -> Optional[str]:
    """查找复合赋值运算符"""
    compound_ops = {"+=", "-=", "*=", "/="}
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

        if (toke.get('type') == 'op' and toke.get('value') in compound_ops
            and paren_count == 0 and bracket_count == 0 and brace_count == 0):
            return toke.get('value')

    return None

def find_assign_pos(tokens: list, pos: int) -> int:
    """查找赋值运算符 = 的位置"""
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
            return i

    return -1

def parse_compoundassign(tokens: list, pos: int, all_lines: list, linepos: int,
                          compound_op: str, source_line: str) -> tuple:
    """解析复合赋值语句，支持多变量、索引、属性等"""
    # 找到运算符位置
    op_pos = -1
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

        if (toke.get('type') == 'op' and toke.get('value') == compound_op
            and paren_count == 0 and bracket_count == 0 and brace_count == 0):
            op_pos = i
            break

    if op_pos == -1:
        raise KeiError("SyntaxError", "找不到复合赋值运算符")

    # 解析左边
    left_tokens = tokens[pos:op_pos]

    # 检查是否为多变量赋值（左边包含逗号）
    left_comma_positions = []
    paren_count = bracket_count = brace_count = 0

    for i, token in enumerate(left_tokens):
        if token['type'] == 'symbol':
            if token['value'] == '(':
                paren_count += 1
            elif token['value'] == ')':
                paren_count -= 1
            elif token['value'] == '[':
                bracket_count += 1
            elif token['value'] == ']':
                bracket_count -= 1
            elif token['value'] == '{':
                brace_count += 1
            elif token['value'] == '}':
                brace_count -= 1
        if (token['type'] == 'symbol' and token['value'] == ','
            and paren_count == 0 and bracket_count == 0 and brace_count == 0):
            left_comma_positions.append(i)

    if left_comma_positions:
        # 多变量复合赋值 a, b, *rest, **kwargs += ...
        # 支持 a: int, b: string += ...
        vars_list = []
        rest_var = None
        kwargs_var = None
        last_pos = 0

        for comma_pos in left_comma_positions:
            var_tokens = left_tokens[last_pos:comma_pos]
            var_tokens = [t for t in var_tokens if t.get('type') != 'space']

            # 检查是否是 **kwargs
            if len(var_tokens) == 2 and var_tokens[0]['type'] == 'op' and var_tokens[0]['value'] == '**':
                if var_tokens[1]['type'] == 'name':
                    kwargs_var = var_tokens[1]['value']
                else:
                    raise KeiError("SyntaxError", f"** 后面必须是变量名, 得到 {var_tokens[1]}")
            # 检查是否是 *rest
            elif len(var_tokens) == 2 and var_tokens[0]['type'] == 'op' and var_tokens[0]['value'] == '*':
                if var_tokens[1]['type'] == 'name':
                    rest_var = var_tokens[1]['value']
                else:
                    raise KeiError("SyntaxError", f"* 后面必须是变量名, 得到 {var_tokens[1]}")
            # 检查是否是带类型注解的变量 x: int
            elif len(var_tokens) >= 3 and var_tokens[0]['type'] == 'name' and var_tokens[1]['type'] == 'symbol' and var_tokens[1]['value'] == ':':
                var_name = var_tokens[0]['value']
                var_linenum = var_tokens[0].get('linenum', linepos)

                type_tokens = var_tokens[2:]
                if not type_tokens:
                    raise KeiError("SyntaxError", "类型注解不能为空")

                type_node, type_new_pos, type_linepos = parse_expr(
                    type_tokens, 0, allow_assign=False,
                    all_lines=all_lines, linepos=linepos
                )

                if type_node is None or type_new_pos != len(type_tokens):
                    raise KeiError("SyntaxError", f"无效的类型注解: {type_tokens}")

                vars_list.append({
                    'name': var_name,
                    'hint': type_node,
                    'linenum': var_linenum
                })
            # 普通变量名
            elif len(var_tokens) == 1 and var_tokens[0]['type'] == 'name':
                vars_list.append({
                    'name': var_tokens[0]['value'],
                    'hint': None,
                    'linenum': var_tokens[0].get('linenum', linepos)
                })
            # 占位符 _
            elif len(var_tokens) == 1 and var_tokens[0]['type'] == 'symbol' and var_tokens[0]['value'] == '_':
                vars_list.append({
                    'name': '_',
                    'hint': None,
                    'linenum': var_tokens[0].get('linenum', linepos)
                })
            elif len(var_tokens) > 0:
                raise KeiError("SyntaxError", f"多变量赋值左边必须是变量名、*rest 或 **kwargs, 得到 {var_tokens}")

            last_pos = comma_pos + 1

        # 处理最后一个
        var_tokens = left_tokens[last_pos:]
        var_tokens = [t for t in var_tokens if t.get('type') != 'space']

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
        elif len(var_tokens) >= 3 and var_tokens[0]['type'] == 'name' and var_tokens[1]['type'] == 'symbol' and var_tokens[1]['value'] == ':':
            var_name = var_tokens[0]['value']
            var_linenum = var_tokens[0].get('linenum', linepos)

            type_tokens = var_tokens[2:]
            if not type_tokens:
                raise KeiError("SyntaxError", "类型注解不能为空")

            type_node, type_new_pos, type_linepos = parse_expr(
                type_tokens, 0, allow_assign=False,
                all_lines=all_lines, linepos=linepos
            )

            if type_node is None or type_new_pos != len(type_tokens):
                raise KeiError("SyntaxError", f"无效的类型注解: {type_tokens}")

            vars_list.append({
                'name': var_name,
                'hint': type_node,
                'linenum': var_linenum
            })
        elif len(var_tokens) == 1 and var_tokens[0]['type'] == 'name':
            vars_list.append({
                'name': var_tokens[0]['value'],
                'hint': None,
                'linenum': var_tokens[0].get('linenum', linepos)
            })
        elif len(var_tokens) == 1 and var_tokens[0]['type'] == 'symbol' and var_tokens[0]['value'] == '_':
            vars_list.append({
                'name': '_',
                'hint': None,
                'linenum': var_tokens[0].get('linenum', linepos)
            })
        elif len(var_tokens) > 0:
            raise KeiError("SyntaxError", f"多变量赋值左边必须是变量名、*rest 或 **kwargs, 得到 {var_tokens}")

        if kwargs_var:
            raise KeiError("SyntaxError", "**kwargs 只能在函数参数中使用")

        left_node = {
            'type': 'multiassign',
            'vars': vars_list,
            'rest': rest_var,
            'kwargs': kwargs_var
        }
    else:
        # 普通左边表达式（可能是 name、attr、index 等）
        # 支持普通变量的类型注解 x: int += 1
        if len(left_tokens) >= 3 and left_tokens[0]['type'] == 'name' and left_tokens[1]['type'] == 'symbol' and left_tokens[1]['value'] == ':':
            var_name = left_tokens[0]['value']
            var_linenum = left_tokens[0].get('linenum', linepos)

            type_tokens = left_tokens[2:]
            if not type_tokens:
                raise KeiError("SyntaxError", "类型注解不能为空")

            type_node, type_new_pos, type_linepos = parse_expr(
                type_tokens, 0, allow_assign=False,
                all_lines=all_lines, linepos=linepos
            )

            if type_node is None or type_new_pos != len(type_tokens):
                raise KeiError("SyntaxError", f"无效的类型注解: {type_tokens}")

            left_node = {
                'type': 'name',
                'value': var_name,
                'hint': type_node,
                'linenum': var_linenum
            }
        else:
            left_node, left_new_pos, _ = parse_expr(left_tokens, 0, allow_assign=True, all_lines=all_lines, linepos=linepos)
            if not left_node or left_new_pos != len(left_tokens):
                raise KeiError("SyntaxError", f"无效的赋值左边: {left_tokens}")

    # 解析右边（保持不变）
    right_tokens = tokens[op_pos + 1:]

    # 检查右边是否为多值
    right_comma_positions = []
    paren_count = bracket_count = brace_count = 0

    for i, token in enumerate(right_tokens):
        if token['type'] == 'symbol':
            if token['value'] == '(':
                paren_count += 1
            elif token['value'] == ')':
                paren_count -= 1
            elif token['value'] == '[':
                bracket_count += 1
            elif token['value'] == ']':
                bracket_count -= 1
            elif token['value'] == '{':
                brace_count += 1
            elif token['value'] == '}':
                brace_count -= 1

        if (token['type'] == 'symbol' and token['value'] == ','
            and paren_count == 0 and bracket_count == 0 and brace_count == 0):
            right_comma_positions.append(i)

    if right_comma_positions:
        # 多值右边 a, b, c += 1, 2, 3
        elements = []
        last_pos = 0

        for comma_pos in right_comma_positions:
            value_tokens = right_tokens[last_pos:comma_pos]

            if value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '[':
                val_node, _, _ = parse_list(value_tokens, 0, all_lines=all_lines, linepos=linepos)
            elif value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '{':
                val_node, _, _ = parse_dict(value_tokens, 0, all_lines=all_lines, linepos=linepos)
            else:
                val_node, _, _ = parse_expr(value_tokens, 0, allow_assign=False, all_lines=all_lines, linepos=linepos)

            if val_node:
                elements.append(val_node)
            last_pos = comma_pos + 1

        # 处理最后一个
        value_tokens = right_tokens[last_pos:]
        if value_tokens:
            if value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '[':
                val_node, _, _ = parse_list(value_tokens, 0, all_lines=all_lines, linepos=linepos)
            elif value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '{':
                val_node, _, _ = parse_dict(value_tokens, 0, all_lines=all_lines, linepos=linepos)
            else:
                val_node, _, _ = parse_expr(value_tokens, 0, allow_assign=False, all_lines=all_lines, linepos=linepos)
            if val_node:
                elements.append(val_node)

        right_node = {'type': 'list', 'elements': elements}
        final_pos = op_pos + 1 + len(right_tokens)
    else:
        # 普通右边
        if right_tokens and right_tokens[0]['type'] == 'symbol' and right_tokens[0]['value'] == '{':
            right_node, right_new_pos, _ = parse_dict(right_tokens, 0, all_lines=all_lines, linepos=linepos)
        elif right_tokens and right_tokens[0]['type'] == 'symbol' and right_tokens[0]['value'] == '[':
            right_node, right_new_pos, _ = parse_list(right_tokens, 0, all_lines=all_lines, linepos=linepos)
        else:
            right_node, right_new_pos, _ = parse_expr(right_tokens, 0, allow_assign=False, all_lines=all_lines, linepos=linepos)

        if not right_node:
            raise KeiError("SyntaxError", "无效的赋值右边")
        final_pos = op_pos + 1 + right_new_pos

    node = {
        'type': 'compoundassign',
        'left': left_node,
        'right': right_node,
        'op': compound_op,
    }
    return node, final_pos, linepos

def parse_assign(tokens: list, pos: int, assign_pos: int, all_lines: list,
                 linepos: int, source_line: str) -> tuple:
    """解析赋值语句（支持解包、*rest、**kwargs、变量类型注解）"""
    # 解析左边
    left_tokens = tokens[pos:assign_pos]

    # 检查是否为 *var 或 **var 单独使用
    if len(left_tokens) == 2 and left_tokens[0]['type'] == 'op':
        if left_tokens[0]['value'] == '*' and left_tokens[1]['type'] == 'name':
            raise KeiError("SyntaxError", f"*{left_tokens[1]['value']} 不能单独使用，只能在多变量赋值中使用（如 a, *rest = ...）")
        elif left_tokens[0]['value'] == '**' and left_tokens[1]['type'] == 'name':
            raise KeiError("SyntaxError", f"**{left_tokens[1]['value']} 不能单独使用，只能在多变量赋值中使用")

    # 检查是否为多变量赋值（包含逗号）
    left_comma_positions = []
    paren_count = 0
    bracket_count = 0
    brace_count = 0

    for i, token in enumerate(left_tokens):
        if token['type'] == 'symbol':
            if token['value'] == '(':
                paren_count += 1
            elif token['value'] == ')':
                paren_count -= 1
            elif token['value'] == '[':
                bracket_count += 1
            elif token['value'] == ']':
                bracket_count -= 1
            elif token['value'] == '{':
                brace_count += 1
            elif token['value'] == '}':
                brace_count -= 1
        if token['type'] == 'symbol' and token['value'] == ',' and paren_count == 0 and bracket_count == 0 and brace_count == 0:
            left_comma_positions.append(i)

    if left_comma_positions:
        # 多变量赋值 a, b, *rest, **kwargs = ...
        # 支持 a: int, b: string = 1, "hello"
        vars = []
        rest_var = None
        kwargs_var = None
        last_pos = 0

        for comma_pos in left_comma_positions:
            var_tokens = left_tokens[last_pos:comma_pos]

            var_tokens = [t for t in var_tokens if t['type'] != 'space'] if any(t.get('type') == 'space' for t in var_tokens) else var_tokens

            # 检查是否是 **kwargs
            if len(var_tokens) == 2 and var_tokens[0]['type'] == 'op' and var_tokens[0]['value'] == '**':
                if var_tokens[1]['type'] == 'name':
                    kwargs_var = var_tokens[1]['value']
                else:
                    raise KeiError("SyntaxError", f"** 后面必须是变量名, 得到 {var_tokens[1]}")
            # 检查是否是 *rest
            elif len(var_tokens) == 2 and var_tokens[0]['type'] == 'op' and var_tokens[0]['value'] == '*':
                if var_tokens[1]['type'] == 'name':
                    rest_var = var_tokens[1]['value']
                else:
                    raise KeiError("SyntaxError", f"* 后面必须是变量名, 得到 {var_tokens[1]}")
            # 检查是否是带类型注解的变量 x: int
            elif len(var_tokens) >= 3 and var_tokens[0]['type'] == 'name' and var_tokens[1]['type'] == 'symbol' and var_tokens[1]['value'] == ':':
                var_name = var_tokens[0]['value']
                var_linenum = var_tokens[0].get('linenum', linepos)

                # 解析类型表达式
                type_tokens = var_tokens[2:]
                if not type_tokens:
                    raise KeiError("SyntaxError", "类型注解不能为空")

                type_node, type_new_pos, type_linepos = parse_expr(
                    type_tokens, 0, allow_assign=False,
                    all_lines=all_lines, linepos=linepos
                )

                if type_node is None or type_new_pos != len(type_tokens):
                    raise KeiError("SyntaxError", f"无效的类型注解: {type_tokens}")

                # 创建带 hint 的变量信息
                vars.append({
                    'name': var_name,
                    'hint': type_node,
                    'linenum': var_linenum
                })
            # 普通变量名
            elif len(var_tokens) == 1 and var_tokens[0]['type'] == 'name':
                vars.append({
                    'name': var_tokens[0]['value'],
                    'hint': None,
                    'linenum': var_tokens[0].get('linenum', linepos)
                })
            # 占位符 _
            elif len(var_tokens) == 1 and var_tokens[0]['type'] == 'symbol' and var_tokens[0]['value'] == '_':
                vars.append({
                    'name': '_',
                    'hint': None,
                    'linenum': var_tokens[0].get('linenum', linepos)
                })
            elif len(var_tokens) > 0:
                raise KeiError("SyntaxError", f"多变量赋值左边必须是变量名、*rest 或 **kwargs, 得到 {var_tokens}")

            last_pos = comma_pos + 1

        # 处理最后一个
        var_tokens = left_tokens[last_pos:]
        var_tokens = [t for t in var_tokens if t['type'] != 'space'] if any(t.get('type') == 'space' for t in var_tokens) else var_tokens

        # 检查是否是 **kwargs
        if len(var_tokens) == 2 and var_tokens[0]['type'] == 'op' and var_tokens[0]['value'] == '**':
            if var_tokens[1]['type'] == 'name':
                kwargs_var = var_tokens[1]['value']
            else:
                raise KeiError("SyntaxError", f"** 后面必须是变量名, 得到 {var_tokens[1]}")
        # 检查是否是 *rest
        elif len(var_tokens) == 2 and var_tokens[0]['type'] == 'op' and var_tokens[0]['value'] == '*':
            if var_tokens[1]['type'] == 'name':
                rest_var = var_tokens[1]['value']
            else:
                raise KeiError("SyntaxError", f"* 后面必须是变量名, 得到 {var_tokens[1]}")
        # 检查是否是带类型注解的变量 x: int
        elif len(var_tokens) >= 3 and var_tokens[0]['type'] == 'name' and var_tokens[1]['type'] == 'symbol' and var_tokens[1]['value'] == ':':
            var_name = var_tokens[0]['value']
            var_linenum = var_tokens[0].get('linenum', linepos)

            type_tokens = var_tokens[2:]
            if not type_tokens:
                raise KeiError("SyntaxError", "类型注解不能为空")

            type_node, type_new_pos, type_linepos = parse_expr(
                type_tokens, 0, allow_assign=False,
                all_lines=all_lines, linepos=linepos
            )

            if type_node is None or type_new_pos != len(type_tokens):
                raise KeiError("SyntaxError", f"无效的类型注解: {type_tokens}")

            vars.append({
                'name': var_name,
                'hint': type_node,
                'linenum': var_linenum
            })
        # 普通变量名
        elif len(var_tokens) == 1 and var_tokens[0]['type'] == 'name':
            vars.append({
                'name': var_tokens[0]['value'],
                'hint': None,
                'linenum': var_tokens[0].get('linenum', linepos)
            })
        elif len(var_tokens) == 1 and var_tokens[0]['type'] == 'symbol' and var_tokens[0]['value'] == '_':
            vars.append({
                'name': '_',
                'hint': None,
                'linenum': var_tokens[0].get('linenum', linepos)
            })
        elif len(var_tokens) > 0:
            raise KeiError("SyntaxError", f"多变量赋值左边必须是变量名、*rest 或 **kwargs, 得到 {var_tokens}")

        if kwargs_var:
            raise KeiError("SyntaxError", "**kwargs 只能在函数参数中使用")

        left_node = {
            'type': 'multiassign',
            'vars': vars,
            'rest': rest_var,
            'kwargs': kwargs_var
        }
    else:
        # 普通赋值 - 支持变量类型注解 x: int = 42
        if len(left_tokens) >= 3 and left_tokens[0]['type'] == 'name' and left_tokens[1]['type'] == 'symbol' and left_tokens[1]['value'] == ':':
            var_name = left_tokens[0]['value']
            var_linenum = left_tokens[0].get('linenum', linepos)

            type_tokens = left_tokens[2:]
            if not type_tokens:
                raise KeiError("SyntaxError", "类型注解不能为空")

            type_node, type_new_pos, type_linepos = parse_expr(
                type_tokens, 0, allow_assign=False,
                all_lines=all_lines, linepos=linepos
            )

            if type_node is None or type_new_pos != len(type_tokens):
                raise KeiError("SyntaxError", f"无效的类型注解: {type_tokens}")

            left_node = {
                'type': 'name',
                'value': var_name,
                'hint': type_node,
                'linenum': var_linenum
            }
        else:
            left_node, left_new_pos, left_linepos = parse_expr(
                left_tokens, 0, allow_assign=True,
                all_lines=all_lines, linepos=linepos
            )
            if not left_node or left_new_pos != len(left_tokens):
                raise KeiError("SyntaxError", f"无效的赋值左边: {left_tokens}")
            if left_linepos > linepos:
                linepos = left_linepos

    # 解析右边（保持不变）
    right_tokens = tokens[assign_pos + 1:]

    # 检查是否为多值返回（右边有逗号）
    right_comma_positions = []
    paren_count = 0
    bracket_count = 0
    brace_count = 0

    for i, token in enumerate(right_tokens):
        if token['type'] == 'symbol':
            if token['value'] == '(':
                paren_count += 1
            elif token['value'] == ')':
                paren_count -= 1
            elif token['value'] == '[':
                bracket_count += 1
            elif token['value'] == ']':
                bracket_count -= 1
            elif token['value'] == '{':
                brace_count += 1
            elif token['value'] == '}':
                brace_count -= 1

        if token['type'] == 'symbol' and token['value'] == ',' and paren_count == 0 and bracket_count == 0 and brace_count == 0:
            right_comma_positions.append(i)

    if right_comma_positions:
        elements = []
        last_pos = 0

        for comma_pos in right_comma_positions:
            value_tokens = right_tokens[last_pos:comma_pos]

            if value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '[':
                val_node, _, val_linepos = parse_list(value_tokens, 0, all_lines=all_lines, linepos=linepos)
            elif value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '{':
                val_node, _, val_linepos = parse_dict(value_tokens, 0, all_lines=all_lines, linepos=linepos)
            else:
                val_node, _, val_linepos = parse_expr(value_tokens, 0, allow_assign=False, all_lines=all_lines, linepos=linepos)

            if val_node:
                elements.append(val_node)
            if val_linepos > linepos:
                linepos = val_linepos
            last_pos = comma_pos + 1

        value_tokens = right_tokens[last_pos:]
        if value_tokens:
            if value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '[':
                val_node, _, val_linepos = parse_list(value_tokens, 0, all_lines=all_lines, linepos=linepos)
            elif value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '{':
                val_node, _, val_linepos = parse_dict(value_tokens, 0, all_lines=all_lines, linepos=linepos)
            else:
                val_node, _, val_linepos = parse_expr(value_tokens, 0, allow_assign=False, all_lines=all_lines, linepos=linepos)
            if val_node:
                elements.append(val_node)
            if val_linepos > linepos:
                linepos = val_linepos

        right_node = {'type': 'list', 'elements': elements}
        final_pos = assign_pos + 1 + len(right_tokens)
    else:
        if right_tokens and right_tokens[0]['type'] == 'symbol' and right_tokens[0]['value'] == '{':
            right_node, right_new_pos, right_linepos = parse_dict(right_tokens, 0, all_lines=all_lines, linepos=linepos)
        elif right_tokens and right_tokens[0]['type'] == 'symbol' and right_tokens[0]['value'] == '[':
            right_node, right_new_pos, right_linepos = parse_list(right_tokens, 0, all_lines=all_lines, linepos=linepos)
        else:
            right_node, right_new_pos, right_linepos = parse_expr(right_tokens, 0, allow_assign=False, all_lines=all_lines, linepos=linepos)

        if not right_node:
            raise KeiError("SyntaxError", "无效的赋值右边")

        final_pos = assign_pos + 1 + right_new_pos
        if right_linepos > linepos:
            linepos = right_linepos

    node = {
        'type': 'assign',
        'left': left_node,
        'right': right_node,
        'linenum': tokens[pos].get('linenum', linepos) if pos < len(tokens) else linepos
    }

    return node, final_pos, linepos

def parse_call(name, tokens, pos, is_attr=False, all_lines=None, linepos=0):
    pos += 1
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
        if (pos < len(tokens) and tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '**' and
              pos + 1 < len(tokens)):
            pos += 1
            val, pos, linepos = parse_expr(tokens, pos, in_call=True, all_lines=all_lines, linepos=linepos)
            arguments.append({'type': 'starkwargs', 'value': val})

        elif (pos < len(tokens) and tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '*' and
              pos + 1 < len(tokens)):
            pos += 1
            val, pos, linepos = parse_expr(tokens, pos, in_call=True, all_lines=all_lines, linepos=linepos)
            arguments.append({'type': 'starargs', 'value': val})

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
    return parse_call(obj_node, tokens, pos, is_attr=True, all_lines=all_lines, linepos=linepos)

def parse_atom(tokens: list, pos: int, in_call=False, all_lines=None, linepos=0) -> tuple:
    debug_print(f"parse_atom: pos={pos}, token={tokens[pos] if pos < len(tokens) else 'EOF'}")
    if pos >= len(tokens):
        return None, pos, linepos
    t = tokens[pos]

    if t["type"] == "symbol" and t["value"] == "}":
        return None, pos, linepos

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

    if t["type"] == "name" and t["value"] in keywords:
        return None, pos, linepos

    if t["type"] in {"int", "float", "str", "bool", "null", "list", "dict"}:
        node = t
        pos += 1
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

    if t["type"] == "name":
        name = t["value"]
        pos += 1
        node = {'type': 'name', 'value': name}
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

    if t["type"] == "symbol" and t["value"] == "[":
        node, pos, linepos = parse_list(tokens, pos, all_lines, linepos)
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

    if t["type"] == "symbol" and t["value"] == "{":
        if pos + 1 < len(tokens) and tokens[pos+1]["type"] == "name" and tokens[pos+1]["value"] in keywords:
            return None, pos, linepos
        node, pos, linepos = parse_dict(tokens, pos, all_lines, linepos)
        return node, pos, linepos

    return None, pos, linepos

def parse_index_with_obj(obj_node, tokens, pos, all_lines=None, linepos=0):
    pos += 1
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

    parts = []
    current = []
    colon_count = 0
    paren_count = 0
    bracket_count = 0
    brace_count = 0

    for toke in inner_tokens:
        is_colon = (toke == ':' or (isinstance(toke, dict) and toke.get('value') == ':'))
        if is_colon and paren_count == 0 and bracket_count == 0 and brace_count == 0:
            parts.append(current)
            current = []
            colon_count += 1
        else:
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

    while pos < len(tokens):
        t = tokens[pos]
        if t['value'] == 'if' and not in_comp:
            if left is None:
                raise KeiError("SyntaxError", "三目运算符缺少真值")

            true_val = left
            pos += 1
            cond, pos, linepos = parse_expr(tokens, pos, in_call, allow_assign, in_comp, all_lines, linepos)

            if cond is None:
                raise KeiError("SyntaxError", "三目运算符缺少条件表达式")

            if pos >= len(tokens) or tokens[pos].get('value') != 'else':
                raise KeiError("SyntaxError", "三目运算符需要 else")
            pos += 1

            false_val, pos, linepos = parse_expr(tokens, pos, in_call, allow_assign, in_comp, all_lines, linepos)

            if false_val is None:
                raise KeiError("SyntaxError", "三目运算符缺少假值")

            node = {'type': 'ternary', 'cond': cond, 'true_val': true_val, 'false_val': false_val}
            return node, pos, linepos

        if t['value'] == 'unless' and not in_comp:
            if left is None:
                raise KeiError("SyntaxError", "三目运算符缺少真值")

            true_val = left
            pos += 1
            cond, pos, linepos = parse_expr(tokens, pos, in_call, allow_assign, in_comp, all_lines, linepos)

            if cond is None:
                raise KeiError("SyntaxError", "三目运算符缺少条件表达式")

            if pos >= len(tokens) or tokens[pos].get('value') != 'else':
                raise KeiError("SyntaxError", "三目运算符需要 else")
            pos += 1

            false_val, pos, linepos = parse_expr(tokens, pos, in_call, allow_assign, in_comp, all_lines, linepos)

            if false_val is None:
                raise KeiError("SyntaxError", "三目运算符缺少假值")

            node = {'type': 'unternary', 'cond': cond, 'true_val': true_val, 'false_val': false_val}
            return node, pos, linepos

        break

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

        # 处理 not（一元）
        if t["value"] == "not":
            pos += 1
            right, new_pos, linepos = parse_compare(tokens, pos, in_call, allow_assign, in_comp, all_lines, linepos)
            if right is None:
                raise KeiError("SyntaxError", f"运算符 'not' 后面缺少表达式")
            left = {"type": "unary", "op": "not", "expr": right}
            pos = new_pos
            continue

        # 处理 and / or（二元）
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
    start_pos = pos
    pos += 1

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
    pos += 1

    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '}':
        pos += 1
        return {'type': 'dict', 'pairs': []}, pos, linepos

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

        if (tok.get('value') == 'for' and
            bracket_count == 1 and
            paren_count == 0 and
            square_count == 0):
            return parse_dictcomp(tokens, start_pos, all_lines, linepos)

        temp_pos += 1

    pairs = []

    while pos < len(tokens):
        if tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '}':
            pos += 1
            break

        key = tokens[pos]

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
    ifunless = None
    start_pos = pos
    pos += 1

    expr_tokens = []
    paren_count = 0
    bracket_count = 0
    brace_count = 0
    temp_pos = pos

    while temp_pos < len(tokens):
        toke = tokens[temp_pos]

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

        if (toke.get('value') == 'for' and
            paren_count == 0 and
            bracket_count == 0 and
            brace_count == 0):
            break

        expr_tokens.append(toke)
        temp_pos += 1

    if not expr_tokens:
        raise KeiError("SyntaxError", "列表生成式需要表达式")

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

    iterable, pos, linepos = parse_expr(tokens, pos, in_comp=True, all_lines=all_lines, linepos=linepos)

    cond = None
    if pos < len(tokens) and tokens[pos].get('value') == 'if':
        ifunless = tokens[pos]['value']
        pos += 1
        cond, pos, linepos = parse_expr(tokens, pos, in_comp=True, all_lines=all_lines, linepos=linepos)

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
    pos += 1

    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ']':
        pos += 1
        return {'type': 'list', 'elements': []}, pos, linepos

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

        if (tok.get('value') == 'for' and
            bracket_count == 1 and
            paren_count == 0 and
            brace_count == 0):
            return parse_listcomp(tokens, start_pos, all_lines, linepos)

        temp_pos += 1

    elements = []

    while True:
        elem, new_pos, linepos = parse_expr(tokens, pos, all_lines=all_lines, linepos=linepos)
        if elem:
            elements.append(elem)
            pos = new_pos
        else:
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
            # 新增：常用转义
            elif s[i+1] == 'a':
                result.append('\a')
                i += 2
            elif s[i+1] == 'b':
                result.append('\b')
                i += 2
            elif s[i+1] == 'f':
                result.append('\f')
                i += 2
            elif s[i+1] == 'v':
                result.append('\v')
                i += 2
            elif s[i+1] == 'e':
                result.append('\x1b')  # ESC 字符
                i += 2
            # 八进制 \0xx 或 \0
            elif s[i+1] == '0':
                if i + 2 < length and s[i+2].isdigit():
                    # 至少有一位数字
                    j = i + 2
                    while j < length and j < i + 4 and s[j].isdigit():
                        j += 1
                    try:
                        result.append(chr(int(s[i+2:j], 8)))
                        i = j
                    except:
                        result.append(s[i])
                        i += 1
                else:
                    result.append('\x00')  # 空字符
                    i += 2
            # 十六进制 \xHH
            elif s[i+1] == 'x' and i + 3 < length:
                try:
                    result.append(chr(int(s[i+2:i+4], 16)))
                    i += 4
                except:
                    result.append(s[i])
                    i += 1
            # Unicode 16位 \uHHHH
            elif s[i+1] == 'u' and i + 5 < length:
                try:
                    result.append(chr(int(s[i+2:i+6], 16)))
                    i += 6
                except:
                    result.append(s[i])
                    i += 1
            # Unicode 32位 \UHHHHHHHH
            elif s[i+1] == 'U' and i + 9 < length:
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
    while class_obj:
        if method_name in class_obj.get('methods_map', {}):
            return class_obj['methods_map'][method_name]
        class_obj = env.get(class_obj.get('parent')) if class_obj.get('parent') else None
    return None

def get_from_env(name, env, default=undefined):
    """从当前环境向上查找任意变量 / 配置 / 函数"""
    current = env
    while current is not None:
        if name in current:
            return current[name]
        current = current.get('__parent__')
    return default

def runtoken(node, env) -> tuple:
    import eval

    if node is None:
        raise KeiError("RuntimeError", "出现了未意料的None节点")

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
        nodetypes = {}

        nodetypes.update(dict.fromkeys(
            ('null', 'int', 'float', 'str', 'bool', 'list', 'dict'),
            eval.node_literal))

        nodetypes['match'] = eval.node_match
        nodetypes['name'] = eval.node_name
        nodetypes['coalesce'] = eval.node_coalesce
        nodetypes['notnullassert'] = eval.node_notnullassert
        nodetypes['index'] = eval.node_index
        nodetypes['trysingle'] = eval.node_trysingle
        nodetypes['slice'] = eval.node_slice
        nodetypes['attr'] = eval.node_attr
        nodetypes['postfix'] = eval.node_postfix
        nodetypes['compoundassign'] = eval.node_compoundassign
        nodetypes['ternary'] = eval.node_ternary
        nodetypes['unternary'] = eval.node_unternary
        nodetypes['listcomp'] = eval.node_listcomp
        nodetypes['unlistcomp'] = eval.node_listcomp
        nodetypes['dictcomp'] = eval.node_dictcomp
        nodetypes['undictcomp'] = eval.node_dictcomp
        nodetypes['binop'] = eval.node_binop
        nodetypes['unary'] = eval.node_unary
        nodetypes['listscope'] = eval.node_listscope
        nodetypes['call'] = eval.node_call
        nodetypes['methodcall'] = eval.node_call
        nodetypes['assign'] = eval.node_assign
        nodetypes['return'] = eval.node_return
        nodetypes['if'] = eval.node_if
        nodetypes['unless'] = eval.node_if
        nodetypes['while'] = eval.node_while
        nodetypes['until'] = eval.node_while
        nodetypes['for'] = eval.node_for
        nodetypes['break'] = eval.node_break
        nodetypes['continue'] = eval.node_break
        nodetypes['function'] = eval.node_block
        nodetypes['class'] = eval.node_class
        nodetypes['import'] = eval.node_import
        nodetypes['fromimport'] = eval.node_fromimport
        nodetypes['del'] = eval.node_del
        nodetypes['raise'] = eval.node_raise
        nodetypes['use'] = eval.node_use
        nodetypes['namespace'] = eval.node_namespace
        nodetypes['with'] = eval.node_with
        nodetypes['lambda'] = eval.node_lambda
        nodetypes['try'] = eval.node_try
        nodetypes['global'] = eval.node_global
        nodetypes['typeassert'] = eval.node_typeassert

        if node['type'] in nodetypes:
            return nodetypes[node['type']](node, env)
        else:
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
                try:
                    save_env = copy.deepcopy(env)
                except:
                    try:
                        save_env = copy.copy(env)
                    except:
                        save_env = env.copy()

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
                    vars_to_show = {k: v for k, v in env.items()
                                   if not str(k).startswith('__')}

                    if vars_to_show:
                        max_name_len = max(len(str(k)) for k in vars_to_show.keys())

                        for k, v in vars_to_show.items():
                            name = str(k)
                            value = content(v, _in_container=True)
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
                            start = max(0, line_num - 6)
                            end = min(len(__kei__.code), line_num + 5)

                        for i in range(start, end):
                            marker = " \033[33m>\033[0m" if i == line_num - 1 else "  "
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

        __kei__.stack.append(get_from_env('__caller__', env, '<global>'))

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
                __kei__.stack.copy(),
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
        "__env__": KeiDict(env),
        "__osname__": KeiString(platform.system().lower()),
    })

    for name, func in stdlib.func.items():
        env[name] = func

    tokens = token(code)
    tokens = ast(tokens)

    for node in tokens:
        ret = runtoken(node, env)[0]

    return env, ret

def execmain(code, env=None, step=False):
    cmd_args = []
    for arg in sys.argv[1:]:
        cmd_args.append(f"{arg}")

    code += f"\nmain({content(cmd_args)});"

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

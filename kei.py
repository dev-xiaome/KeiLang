#!/usr/bin/env python
"""KeiLang"""

import platform
import copy
import sys
import os

__kei__ = {}
__version__ = "0.1"

try:
    __import__('readline')
except:
    pass

keidir = os.path.dirname(os.path.abspath(__file__))
path = os.environ.get('PATH', '')
paths = path.split(os.pathsep)

modulenames = []

for f in os.listdir(os.path.join(keidir, 'lib')):
    if os.path.isfile(f) and f.endswith('.py'):
        modulenames.append(f)

sys.path.append('/usr/local/lib/keilang')
paths.append('/usr/local/lib/keilang')

__py_exec__ = exec

import lib.stdlib as stdlib
from lib.object import *

KeiFunction.__kei__ = __kei__

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
   'merge'
]

sys.setrecursionlimit(30 if DEBUG else 1024)

def debug_print(*args, **kwargs):
    if DEBUG:
        print("[DEBUG]", *args, **kwargs)

def error(info: str|object, stack: list=[], code:str|None=None, linenum=None, filename='未知文件') -> None:
    linenum = linenum if linenum is not None else "??"
    space   = ' ' * len(str(linenum) if linenum is not None else "")

    print(f"File \033[33;1m{filename}\033[0m")

    print(f"{space} ·")

    for s in stack:
        print(f"{space} | in \033[36;1m{s}\033[0m")

    if stack:
        print(f"{space} |")

    if code is None:
        code = "未知行"

    code = code.strip()

    print(f"\033[33;1m{linenum}\033[0m | {code}")

    print(f"{space} | \033[31;1m" + ('^' * stdlib.kei.cnlen(KeiString(code))) + "\033[0m")

    if isinstance(info, KeiError):
        print(f"{space} | \033[36m>>>\033[0m \033[33;1m[{info.types}] {info.value}\033[0m")
    else:
        print(f"{space} | \033[36m>>>\033[0m \033[33;1m{info}\033[0m")

    print(f"{space} ·")

    #import traceback
    #traceback.print_exc()

    sys.exit(1)

def token(original: str) -> list:
    __kei__['code'] = original.splitlines()

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

            # 检查 :=
            if c == ':' and pos + 1 < length and codes[pos+1] == '=':
                tokens.append(":=")
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
                # 普通单行字符串
                start = pos
                quote = c
                pos += 1
                while pos < length and codes[pos] != quote:
                    if codes[pos] == '\\' and pos + 1 < length:
                        pos += 2
                    else:
                        pos += 1
                if pos < length and codes[pos] == quote:
                    pos += 1
                string = codes[start:pos]
                tokens.append(('string', escape(string)))
                continue

            # r-string 单行
            if c == 'r':
                # 先跳过可能的空格
                temp_pos = pos + 1
                while temp_pos < length and codes[temp_pos] in ' \n\t':
                    temp_pos += 1

                if temp_pos < length and codes[temp_pos] in '"\'':
                    # r-string 单行
                    quote = codes[temp_pos]
                    pos = temp_pos + 1
                    start = pos
                    while pos < length and codes[pos] != quote:
                        pos += 1
                    if pos < length and codes[pos] == quote:
                        pos += 1
                    string = codes[start:pos]
                    tokens.append(('rstring', '"' + string))
                    continue

            # f-string 单行
            if c == 'f':
                # 先跳过可能的空格
                temp_pos = pos + 1
                while temp_pos < length and codes[temp_pos] in ' \n\t':
                    temp_pos += 1

                if temp_pos < length and codes[temp_pos] in '"\'':
                    # f-string 单行
                    quote = codes[temp_pos]
                    pos = temp_pos + 1
                    start = pos
                    while pos < length and codes[pos] != quote:
                        if codes[pos] == '\\' and pos + 1 < length:
                            pos += 2
                        else:
                            pos += 1
                    if pos < length and codes[pos] == quote:
                        pos += 1
                    string = codes[start:pos]
                    tokens.append(('fstring', '"' + escape(string)))
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

            # 检查关键字
            if c == "i" and pos + 2 < length and codes[pos+1] in ["s", "n"] and (pos + 2 >= length or codes[pos+2] in ' \n\t'):
                if codes[pos+1] == 's':
                    tokens.append("is")
                    pos += 2
                elif codes[pos+1] == 'n':
                    tokens.append("in")
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

        if isinstance(thetoken, tuple) and thetoken[0] == 'fstring':
            result.append({"type":"str", "value":thetoken[1][1:-1], "mark": "f", 'linenum':linetokens[pos][1]})
            pos += 1
            continue

        if isinstance(thetoken, tuple) and thetoken[0] == 'rstring':
            result.append({"type":"str", "value":thetoken[1][1:-1], "mark": "r", 'linenum':linetokens[pos][1]})
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

def parse_call(name: str, tokens: list, pos: int) -> tuple:
    """解析函数调用, 支持函数作为参数"""
    pos += 1  # 跳过 '('

    args = []  # 普通位置参数
    kwargs = {}  # 关键字参数
    starargs = None  # *args 解包
    starkwargs = None  # **kwargs 解包

    # 如果没有参数
    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ')':
        pos += 1
        return {
            'type': 'call',
            'name': name,
            'args': args,
            'kwargs': kwargs,
            'starargs': starargs,
            'starkwargs': starkwargs
        }, pos

    # 解析参数
    while True:
        # 检查是否是 **kwargs 解包
        if (pos < len(tokens) and tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '**' and
              pos + 1 < len(tokens)):
            pos += 1  # 跳过 '**'
            # 解析后面的表达式（应该是字典）
            starkwargs, pos = parse_expr(tokens, pos, in_call=True)
            if not starkwargs:
                raise KeiError("SyntaxError", "** 后面需要表达式")

        # 检查是否是 *args 解包
        elif (pos < len(tokens) and tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '*' and
              pos + 1 < len(tokens)):
            pos += 1  # 跳过 '*'
            # 解析后面的表达式（应该是列表）
            starargs, pos = parse_expr(tokens, pos, in_call=True)
            if not starargs:
                raise KeiError("SyntaxError", "* 后面需要表达式")

        # 检查是否是关键字参数 (name=value)
        elif (pos < len(tokens) and tokens[pos]['type'] == 'name' and
            pos + 1 < len(tokens) and tokens[pos+1]['type'] == 'op' and
            tokens[pos+1]['value'] == "="):

            # 关键字参数
            kwarg_name = tokens[pos]['value']
            pos += 2  # 跳过 name 和 =

            # 解析值
            kwarg_value, pos = parse_expr(tokens, pos, in_call=True)
            if kwarg_value:
                kwargs[kwarg_name] = kwarg_value
        else:
            # 普通位置参数
            arg, pos = parse_expr(tokens, pos, in_call=True)
            if arg:
                args.append(arg)

        # 检查逗号或结束
        if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
            pos += 1
            continue
        elif pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ')':
            pos += 1
            break
        else:
            if pos >= len(tokens):
                raise KeiError("SyntaxError", "缺少右括号 ')'")
            raise KeiError("SyntaxError", f"参数列表后有多余的 token: {tokens[pos]['value']}")

    return {
        'type': 'call',
        'name': name,
        'args': args,
        'kwargs': kwargs,
        'starargs': starargs,
        'starkwargs': starkwargs,
    }, pos

def parse_call_attr(obj_node, tokens, pos, in_call=False):
    pos += 1  # 跳过 '('

    args = []
    kwargs = {}
    starargs = None
    starkwargs = None

    # 如果没有参数
    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ')':
        pos += 1
        return {
            'type': 'methodcall',
            'obj': obj_node,
            'args': args,
            'kwargs': kwargs,
            'starargs': starargs,
            'starkwargs': starkwargs
        }, pos

    # 解析参数
    while True:
        # 🔥 这里要处理函数作为参数！
        if (pos < len(tokens) and
            tokens[pos]['type'] == 'name' and
            tokens[pos]['value'] == 'fn'):

            pos += 1

            # 解析参数列表（直到 =>）
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

            # 解析表达式
            expr, pos = parse_expr(tokens, pos)

            args.append({
                'type': 'lambda',
                'params': params,
                'body': expr
            })

        # 检查是否是 **kwargs 解包
        elif (pos < len(tokens) and tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '**' and
              pos + 1 < len(tokens)):
            pos += 1
            starkwargs, pos = parse_expr(tokens, pos, in_call=True)

        # 检查是否是 *args 解包
        elif (pos < len(tokens) and tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '*' and
              pos + 1 < len(tokens)):
            pos += 1
            starargs, pos = parse_expr(tokens, pos, in_call=True)

        # 检查是否是关键字参数
        elif (pos < len(tokens) and tokens[pos]['type'] == 'name' and
              pos + 1 < len(tokens) and tokens[pos+1]['type'] == 'op' and
              tokens[pos+1]['value'] == "="):
            kwarg_name = tokens[pos]['value']
            pos += 2
            kwarg_value, pos = parse_expr(tokens, pos, in_call=True)
            kwargs[kwarg_name] = kwarg_value
        else:
            # 普通位置参数
            arg, pos = parse_expr(tokens, pos, in_call=True)
            if arg:
                args.append(arg)

        # 检查逗号或结束
        if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
            pos += 1
            continue
        elif pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ')':
            pos += 1
            break
        else:
            break

    return {
        'type': 'methodcall',
        'obj': obj_node,
        'args': args,
        'kwargs': kwargs,
        'starargs': starargs,
        'starkwargs': starkwargs
    }, pos

def parse_atom(tokens: list, pos: int, in_call=False) -> tuple:
    debug_print(f"parse_atom: pos={pos}, token={tokens[pos] if pos < len(tokens) else 'EOF'}")

    if pos >= len(tokens):
        debug_print("parse_atom: EOF")
        return None, pos
    t = tokens[pos]

    # 如果是 }，返回特殊标记让上层处理
    if t["type"] == "symbol" and t["value"] == "}":
        debug_print("parse_atom: found '}', returning None")
        return None, pos

    if t['type'] == 'name' and t['value'] == 'fn':
        pos += 1

        # 解析参数列表（直到 =>）
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

        # 解析表达式
        expr, pos = parse_expr(tokens, pos)

        return {
            'type': 'lambda',
            'params': params,
            'body': expr
        }, pos

    # 如果是关键字（包括 fn），返回 None 让 parse_stmt 处理
    if t["type"] == "name" and t["value"] in keywords:
        debug_print(f"parse_atom: keyword {t['value']} at pos {pos}, returning None")
        return None, pos

    # ========== 处理字面量 ==========
    if t["type"] in {"int", "float", "str", "bool", "null", "list", "dict"}:
        debug_print(f"parse_atom: literal {t['type']} at pos {pos}")
        node = t
        pos += 1

        # 统一处理属性访问、索引访问和方法调用
        while pos < len(tokens):
            current_token = tokens[pos]

            # 处理 . 属性访问
            if current_token['type'] == 'symbol' and current_token['value'] == '.':
                pos += 1
                if pos >= len(tokens) or tokens[pos]['type'] != 'name':
                    raise KeiError("SyntaxError", "属性访问语法错误")

                node = {
                    'type': 'attr',
                    'obj': node,
                    'attr': tokens[pos]['value']
                }
                pos += 1

                # 如果是方法调用
                if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '(':
                    return parse_call_attr(node, tokens, pos, in_call)

            # 处理 [ 索引访问
            elif current_token['type'] == 'symbol' and current_token['value'] == '[':
                node, new_pos = parse_index_with_obj(node, tokens, pos)
                pos = new_pos
                continue

            # 处理 ( 方法调用
            elif current_token['type'] == 'symbol' and current_token['value'] == '(':
                return parse_call_attr(node, tokens, pos, in_call)

            else:
                break

        return node, pos

    # ========== 处理名字（标识符）==========
    if t["type"] == "name":
        name = t["value"]
        pos += 1

        # 检查是否是 key=value 形式（在字典或参数列表中）
        if pos < len(tokens) and tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '=':
            if {'type': 'name', 'value': 'type'} not in tokens:
                pos -= 1
                return None, pos

        # 先构建基础节点
        node = {'type': 'name', 'value': name}

        # 检查属性链和方法调用
        while pos < len(tokens):
            # 检查 . 属性访问
            if tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '.':
                if pos + 1 < len(tokens) and tokens[pos+1]['type'] == 'symbol' and tokens[pos+1]['value'] == '.':
                    break

                pos += 1
                if pos >= len(tokens) or tokens[pos]['type'] != 'name':
                    raise KeiError("SyntaxError", "属性访问语法错误：'.' 后面缺少属性名")

                attr_name = tokens[pos]['value']
                pos += 1

                node = {
                    'type': 'attr',
                    'obj': node,
                    'attr': attr_name
                }

                if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '(':
                    return parse_call_attr(node, tokens, pos, in_call)

            # 检查函数调用 ( )
            elif tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '(':
                node, pos = parse_call(name, tokens, pos)

            # 检查索引访问 [ ]
            elif tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '[':
                node, new_pos = parse_index_with_obj(node, tokens, pos)
                pos = new_pos

            else:
                break

        return node, pos

    # 处理括号、列表、字典
    if t["type"] == "symbol" and t["value"] == "(":
        pos += 1
        saved_pos = pos
        try:
            expr, new_pos = parse_expr(tokens, pos, in_call)
            if new_pos < len(tokens) and tokens[new_pos]["type"] == "symbol" and tokens[new_pos]["value"] == ")":
                pos = new_pos + 1
                node = expr

                while pos < len(tokens):
                    if tokens[pos]["type"] == "symbol" and tokens[pos]["value"] == ".":
                        pos += 1
                        if pos >= len(tokens) or tokens[pos]["type"] != "name":
                            raise KeiError("SyntaxError", "属性访问语法错误")
                        attr = tokens[pos]["value"]
                        pos += 1

                        if pos < len(tokens) and tokens[pos]["type"] == "symbol" and tokens[pos]["value"] == "(":
                            node = {
                                'type': 'attr',
                                'obj': node,
                                'attr': attr
                            }
                            return parse_call_attr(node, tokens, pos, in_call)
                        else:
                            node = {"type": "attr", "obj": node, "attr": attr}
                    else:
                        break
                return node, pos
        except:
            pass

        pos = saved_pos
        stmt, new_pos, _ = parse_stmt(tokens, pos, None, 0)

        if new_pos >= len(tokens) or tokens[new_pos]["type"] != "symbol" or tokens[new_pos]["value"] != ")":
            raise KeiError("SyntaxError", "括号不匹配")

        node = stmt
        pos = new_pos + 1

        while pos < len(tokens):
            if tokens[pos]["type"] == "symbol" and tokens[pos]["value"] == ".":
                pos += 1
                if pos >= len(tokens) or tokens[pos]["type"] != "name":
                    raise KeiError("SyntaxError", "属性访问语法错误")
                attr = tokens[pos]["value"]
                pos += 1

                if pos < len(tokens) and tokens[pos]["type"] == "symbol" and tokens[pos]["value"] == "(":
                    node = {
                        'type': 'attr',
                        'obj': node,
                        'attr': attr
                    }
                    return parse_call_attr(node, tokens, pos, in_call)
                else:
                    node = {"type": "attr", "obj": node, "attr": attr}
            else:
                break

        return node, pos

    # 处理列表
    if t["type"] == "symbol" and t["value"] == "[":
        node, new_pos = parse_list(tokens, pos)
        pos = new_pos

        while pos < len(tokens):
            if tokens[pos]["type"] == "symbol" and tokens[pos]["value"] == ".":
                pos += 1
                if pos >= len(tokens) or tokens[pos]["type"] != "name":
                    raise KeiError("SyntaxError", "属性访问语法错误")
                attr = tokens[pos]["value"]
                pos += 1

                node = {
                    'type': 'attr',
                    'obj': node,
                    'attr': attr
                }

                if pos < len(tokens) and tokens[pos]["type"] == "symbol" and tokens[pos]["value"] == "(":
                    return parse_call_attr(node, tokens, pos)
            else:
                break

        return node, pos

    if t["type"] == "symbol" and t["value"] == "{":
        if pos + 1 < len(tokens) and tokens[pos+1]["type"] == "name" and tokens[pos+1]["value"] in keywords:
            return None, pos
        node, pos = parse_dict(tokens, pos)

        return node, pos

    return None, pos

def parse_index_with_obj(obj_node, tokens, pos):
    # 跳过 '['
    pos += 1

    # 找到匹配的 ']'
    bracket_count = 1
    end_pos = pos

    while end_pos < len(tokens):
        current_token = tokens[end_pos]
        token_desc = f"{current_token}" if isinstance(current_token, dict) else current_token

        if current_token == '[' or (isinstance(current_token, dict) and current_token.get('value') == '['):
            bracket_count += 1
        elif current_token == ']' or (isinstance(current_token, dict) and current_token.get('value') == ']'):
            bracket_count -= 1
            if bracket_count == 0:
                break

        end_pos += 1

    if end_pos >= len(tokens) or bracket_count != 0:
        raise KeiError("SyntaxError", "缺少 ]")

    # 提取内部 tokens
    inner_tokens = tokens[pos:end_pos]

    # 按 ':' 分割
    parts = []
    current = []
    colon_positions = []

    for i, token in enumerate(inner_tokens):
        if token == ':' or (isinstance(token, dict) and token.get('value') == ':'):
            parts.append(current)
            current = []
            colon_positions.append(i)
        else:
            current.append(token)
    parts.append(current)

    # 解析各部分
    start = None
    end = None
    step = None

    if len(parts) >= 1 and parts[0]:
        start, _ = parse_expr(parts[0], 0)

    if len(parts) >= 2 and parts[1]:
        end, _ = parse_expr(parts[1], 0)

    if len(parts) >= 3 and parts[2]:
        step, _ = parse_expr(parts[2], 0)

    # 判断类型
    is_slice = len(parts) > 1 or (len(parts) == 1 and colon_positions)

    # 返回
    if is_slice:
        result = {
            'type': 'slice',
            'obj': obj_node,
            'start': start,
            'end': end,
            'step': step
        }
    else:
        result = {
            'type': 'index',
            'obj': obj_node,
            'index': start
        }

    new_pos = end_pos + 1

    return result, new_pos

def parse_assign(tokens: list, pos: int) -> tuple:
    # 检查是否是 ** 赋值
    if (pos + 1 < len(tokens) and
        tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '*' and
        tokens[pos + 1]['type'] == 'op' and tokens[pos + 1]['value'] == '*'):

        # ** 赋值：**kwargs = {"a": 1, "b": 2}
        if pos + 2 >= len(tokens) or tokens[pos + 2]['type'] != 'name':
            raise KeiError("SyntaxError", "** 后面必须是变量名")

        left = {
            'type': 'starstarassign',
            'name': tokens[pos + 2]['value']
        }
        pos += 3  # 跳过 ** 和 变量名

    # 检查是否是 * 赋值
    elif tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '*':
        # * 赋值：*all = 1,2,3
        if pos + 1 >= len(tokens) or tokens[pos + 1]['type'] != 'name':
            raise KeiError("SyntaxError", "* 后面必须是变量名")

        left = {
            'type': 'starassign',
            'name': tokens[pos + 1]['value']
        }
        pos += 2  # 跳过 * 和 变量名

    else:
        # 普通赋值
        left = tokens[pos]
        pos += 1  # 跳过变量名

    # 检查 =
    if pos >= len(tokens) or tokens[pos].get('type') != 'op' or tokens[pos].get('value') != '=':
        raise KeiError("SyntaxError", "需要 =")
    pos += 1  # 跳过 =

    # 解析右边
    right, pos = parse_expr(tokens, pos)

    node = {'type': 'assign', 'left': left, 'right': right}
    return node, pos

def parse_term(tokens, pos, in_call=False):
    left, pos = parse_unary(tokens, pos, in_call)

    while pos < len(tokens):
        t = tokens[pos]
        if t["type"] != "op":
            break

        # 处理 * / 等
        if t["value"] in {"*", "**", "/", "//", "%", "|"}:
            op = t["value"]
            pos += 1
            right, pos = parse_unary(tokens, pos)
            left = {"type": "binop", "op": op, "left": left, "right": right}
        else:
            break

    return left, pos

def parse_expr(tokens: list, pos: int, in_call=False, allow_assign=False, in_comp=False) -> tuple:
    """新的 parse_expr：正确处理优先级（兼容旧接口）"""

    # 先处理三目运算符（优先级最低中的最低）
    left, pos = parse_logic(tokens, pos, in_call, allow_assign, in_comp)

    # 处理三目 if/unless（需要在最外层）
    while pos < len(tokens):
        t = tokens[pos]

        if t['value'] == 'if' and not in_comp:
            true_val = left
            pos += 1
            cond, pos = parse_expr(tokens, pos, in_call, allow_assign, in_comp)

            if pos >= len(tokens) or tokens[pos].get('value') != 'else':
                raise KeiError("SyntaxError", "三目运算符需要 else 分支")
            pos += 1

            false_val, pos = parse_expr(tokens, pos, in_call, allow_assign, in_comp)

            return {
                'type': 'ternary',
                'cond': cond,
                'true_val': true_val,
                'false_val': false_val
            }, pos

        if t['value'] == 'unless' and not in_comp:
            true_val = left
            pos += 1
            cond, pos = parse_expr(tokens, pos, in_call, allow_assign, in_comp)

            if pos >= len(tokens) or tokens[pos].get('value') != 'else':
                raise KeiError("SyntaxError", "三目运算符需要 else 分支")
            pos += 1

            false_val, pos = parse_expr(tokens, pos, in_call, allow_assign, in_comp)

            return {
                'type': 'unternary',
                'cond': cond,
                'true_val': true_val,
                'false_val': false_val
            }, pos

        break

    # 处理 ?
    if pos < len(tokens) and tokens[pos].get('type') == 'op' and tokens[pos].get('value') == '?':
        pos += 1
        return {
            'type': 'trysingle',
            'expr': left
        }, pos

    return left, pos

def parse_logic(tokens: list, pos: int, in_call=False, allow_assign=False, in_comp=False) -> tuple:
    """解析逻辑运算符 and/or"""
    left, pos = parse_compare(tokens, pos, in_call, allow_assign, in_comp)

    while pos < len(tokens):
        t = tokens[pos]

        if t["type"] != "op":
            break

        if t["value"] in {"and", "or"}:
            op = t["value"]
            pos += 1
            right, pos = parse_compare(tokens, pos, in_call, allow_assign, in_comp)
            left = {"type": "binop", "op": op, "left": left, "right": right}
        else:
            break

    return left, pos

def parse_compare(tokens: list, pos: int, in_call=False, allow_assign=False, in_comp=False) -> tuple:
    """解析比较运算符 == != < > <= >= in is"""
    left, pos = parse_addsub(tokens, pos, in_call, allow_assign, in_comp)

    while pos < len(tokens):
        t = tokens[pos]

        if t["type"] != "op":
            break

        if t["value"] in {"==", "!=", "<", ">", "<=", ">=", "in", "is"}:
            op = t["value"]
            pos += 1
            right, pos = parse_addsub(tokens, pos, in_call, allow_assign, in_comp)
            left = {"type": "binop", "op": op, "left": left, "right": right}
        else:
            break

    return left, pos

def parse_addsub(tokens: list, pos: int, in_call=False, allow_assign=False, in_comp=False) -> tuple:
    """解析加减法 + - 和范围 .."""
    left, pos = parse_term(tokens, pos, in_call)

    while pos < len(tokens):
        t = tokens[pos]

        if t["type"] != "op":
            break

        if t["value"] in {"+", "-"}:
            op = t["value"]
            pos += 1
            right, pos = parse_term(tokens, pos, in_call)
            left = {"type": "binop", "op": op, "left": left, "right": right}
            continue

        if t["value"] == "..":
            pos += 1
            right, pos = parse_addsub(tokens, pos, in_call, allow_assign, in_comp)
            left = {'type': 'listscope', 'start': left, 'end': right}
            continue

        # 遇到 = 且允许赋值时，停止（让上层处理）
        if t["value"] == "=" and allow_assign:
            break

        break

    return left, pos

def parse_stmt(tokens: list, pos: int, all_lines: list|None=None, linepos: int=-1) -> tuple:
    """解析语句

    Args:
        tokens: 当前行的token列表
        pos: 当前位置
        all_lines: 所有行的token列表
        linepos: 当前行号

    Returns:
        (node, new_pos, new_linepos)
    """
    debug_print(f"parse_stmt: pos={pos}, linepos={linepos}, token={tokens[pos] if pos < len(tokens) else 'EOF'}")

    globals()['all_lines'] = all_lines
    globals()['pos']       = pos
    globals()['linepos']   = linepos
    globals()['code']      = __kei__.get('code', '未知行')[tokens[pos]['linenum']]
    globals()['linenum']   = tokens[pos]['linenum']

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
                    token = all_lines[current_line][current_pos]
                    if token['type'] == 'op' and token['value'] == '@':
                        current_pos += 1

                        if current_pos >= len(all_lines[current_line]):
                            current_line += 1
                            current_pos = 0
                            if current_line >= len(all_lines):
                                raise KeiError("SyntaxError", "装饰器后面缺少表达式")
                            continue

                        decorator, new_pos = parse_expr(all_lines[current_line], current_pos)
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

                stmt, new_pos, new_line = parse_stmt(all_lines[current_line], current_pos, all_lines, current_line)

                if stmt and stmt['type'] == 'function':
                    stmt['decorators'] = decorators
                    return stmt, new_pos, new_line
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

                    stmt, new_pos, new_line = parse_stmt(current_tokens, current_pos, all_lines, current_line)
                    if stmt:
                        try_body.append(stmt)

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

                            stmt, new_pos, new_line = parse_stmt(catch_tokens, catch_pos, all_lines, catch_line)
                            if stmt:
                                catchbody.append(stmt)

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

                            stmt, new_pos, new_line = parse_stmt(finally_tokens, finally_pos, all_lines, finally_line)
                            if stmt:
                                finallybody.append(stmt)

                            if new_line > finally_line:
                                finally_line = new_line
                                finally_pos = new_pos
                            else:
                                finally_pos = new_pos
                                if new_pos == finally_pos:
                                    finally_pos += 1

                return {
                    'type': 'try',
                    'body': try_body,
                    'var': var,
                    'catchbody': catchbody,
                    'finallybody': finallybody
                }, current_pos, current_line

            # 处理 class 语句
            if t['type'] == 'name' and t['value'] == 'class':
                pos += 1

                if pos >= len(tokens) or tokens[pos]['type'] != 'name':
                    raise KeiError("SyntaxError", "类需要名字")
                class_name = tokens[pos]['value']
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

                methods = []
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

                    stmt, new_pos, new_line = parse_stmt(current_tokens, current_pos, all_lines, current_line)
                    if stmt:
                        methods.append(stmt)

                    if new_line > current_line:
                        current_line = new_line
                        current_pos = new_pos
                    else:
                        current_pos = new_pos
                        if new_pos == current_pos:
                            current_pos += 1

                return {
                    'type': 'class',
                    'name': class_name,
                    'parent': parent_class,
                    'methods': methods,
                }, current_pos, current_line

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

                iterable, pos = parse_expr(tokens, pos)

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

                    stmt, new_pos, new_line = parse_stmt(current_tokens, current_pos, all_lines, current_line)
                    if stmt:
                        body.append(stmt)

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

                # 函数名
                if pos >= len(tokens) or tokens[pos]['type'] != 'name':
                    raise KeiError("SyntaxError", "函数定义需要名字")
                func_name = tokens[pos]['value']
                pos += 1

                if __kei__.get('stack') is None:
                    __kei__['stack'] = []

                __kei__['stack'].append(func_name)

                try:
                    # 参数列表
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
                                default_val, pos = parse_expr(tokens, pos)
                                defaults[param_name] = default_val

                            params.append(param_name)
                            continue

                        elif tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '*':
                            pos += 1
                            if pos < len(tokens) and tokens[pos]['type'] == 'name':
                                params.append('*' + tokens[pos]['value'])
                                pos += 1
                            else:
                                raise KeiError("SyntaxError", "* 后面需要参数名")
                            continue

                        elif tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '**':
                            pos += 1
                            if pos < len(tokens) and tokens[pos]['type'] == 'name':
                                params.append('**' + tokens[pos]['value'])
                                pos += 1
                            else:
                                raise KeiError("SyntaxError", "** 后面需要参数名")
                            continue

                        elif tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
                            pos += 1
                            continue
                        else:
                            raise KeiError("SyntaxError", f"未知的符号: \"{tokens[pos]['value']}\"")

                    pos += 1  # 跳过 )

                    #检查类型断言
                    if pos < len(tokens) and tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '->':
                        pos += 1
                        expr, pos = parse_expr(tokens, pos)

                        hint = expr

                    # 检查箭头函数
                    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '=>':
                        pos += 1

                        # 解析箭头函数体（单个表达式）
                        expr, pos = parse_expr(tokens, pos)
                        body = [{
                            'type': 'return',
                            'value': expr
                        }]

                        __kei__['stack'].pop()
                        return {
                            'type': 'function',
                            'name': func_name,
                            'params': params,
                            'defaults': defaults,
                            'body': body,
                            'hint': hint
                        }, pos, linepos

                    # 普通函数体
                    if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != '{':
                        raise KeiError("SyntaxError", "期待 {")

                except:
                    __kei__['stack'].pop()
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

                        stmt, new_pos, new_line = parse_stmt(current_tokens, current_pos, all_lines, current_line)

                        if stmt:
                            body.append(stmt)

                        if new_line > current_line:
                            current_line = new_line
                            current_pos = new_pos
                        else:
                            current_pos = new_pos
                            if new_pos == current_pos:
                                current_pos += 1

                    __kei__['stack'].pop()

                    return {
                        'type': 'function',
                        'name': func_name,
                        'params': params,
                        'defaults': defaults,
                        'body': body,
                        'hint': hint
                    }, current_pos, current_line
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

                return {'type': sentencename, 'modules': modules}, pos, linepos

            # 处理 break/continue
            if t['type'] == 'name' and t['value'] in {'break', 'continue'}:
                stmt_type = t['value']
                pos += 1
                if pos < len(tokens) and tokens[pos].get('type') == 'op' and tokens[pos].get('value') == ';':
                    pos += 1
                return {'type': stmt_type}, pos, linepos

            # 处理 return 语句
            if t['type'] == 'name' and t['value'] == 'return':
                pos += 1

                if pos >= len(tokens) or (tokens[pos]['type'] == 'op' and tokens[pos]['value'] == ';'):
                    return {'type': 'return', 'value': None}, pos, linepos

                first, pos = parse_expr(tokens, pos)

                values = [first]
                while pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
                    pos += 1
                    next_val, pos = parse_expr(tokens, pos)
                    values.append(next_val)

                if len(values) == 1:
                    return {'type': 'return', 'value': values[0]}, pos, linepos

                return {'type': 'return', 'value': {'type': 'list', 'elements': values}}, pos, linepos

            # 处理 with 语句
            if t['type'] == 'name' and t['value'] == 'with':
                pos += 1

                expr, pos = parse_expr(tokens, pos)

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

                    stmt, new_pos, new_line = parse_stmt(current_tokens, current_pos, all_lines, current_line)
                    if stmt:
                        body.append(stmt)

                    if new_line > current_line:
                        current_line = new_line
                        current_pos = new_pos
                    else:
                        current_pos = new_pos
                        if new_pos == current_pos:
                            current_pos += 1

                return {
                    'type': 'with',
                    'expr': expr,
                    'as_var': as_var,
                    'body': body
                }, current_pos, current_line

            # 处理 namespace 语句
            if t['type'] == 'name' and t['value'] == 'namespace':
                pos += 1

                if pos >= len(tokens) or tokens[pos]['type'] != 'name':
                    raise KeiError("SyntaxError", "命名空间需要名字")
                ns_name = tokens[pos]['value']
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

                    stmt, new_pos, new_line = parse_stmt(current_tokens, current_pos, all_lines, current_line)
                    if stmt:
                        body.append(stmt)

                    if new_line > current_line:
                        current_line = new_line
                        current_pos = new_pos
                    else:
                        current_pos = new_pos
                        if new_pos == current_pos:
                            current_pos += 1

                return {
                    'type': 'namespace',
                    'name': ns_name,
                    'body': body
                }, current_pos, current_line

            # 处理 global/del/raise/merge
            if t['type'] == 'name' and t['value'] in {'global', 'del', 'raise', 'merge'}:
                sentencename = t['value']
                pos += 1
                targets = []

                while pos < len(tokens):
                    target, new_pos = parse_expr(tokens, pos, allow_assign=True)
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

                return {'type': sentencename, 'names': targets}, pos, linepos

            # 处理 if/while/unless/until
            if t['type'] == 'name' and t['value'] in {'if', 'while', 'unless', 'until'}:
                sentencename = t['value']
                pos += 1
                cond, pos = parse_expr(tokens, pos)

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

                    stmt, new_pos, new_line = parse_stmt(current_tokens, current_pos, all_lines, current_line)
                    if stmt:
                        body.append(stmt)

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
                            elif_cond, current_pos = parse_expr(all_lines[current_line], current_pos)

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

                                stmt, new_pos, new_line = parse_stmt(elif_tokens, elif_pos, all_lines, elif_line)
                                if stmt:
                                    elif_body.append(stmt)

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

                                stmt, new_pos, new_line = parse_stmt(else_tokens, else_pos, all_lines, else_line)
                                if stmt:
                                    else_body.append(stmt)

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
                    return {
                        'type': sentencename,
                        'cond': cond,
                        'body': body
                    }, current_pos, current_line

            if t['type'] == 'name' and t['value'] == 'alias':
                pos += 1

                # 解析左边（变量名）
                if pos >= len(tokens) or tokens[pos]['type'] != 'name':
                    raise KeiError("SyntaxError", "alias 后面需要变量名")
                left_name = tokens[pos]
                pos += 1

                # 检查等号（可选？）
                if pos < len(tokens) and tokens[pos]['type'] == 'op' and tokens[pos]['value'] == '=':
                    pos += 1
                else:
                    raise KeiError("SyntaxError", "alias缺少等号")

                # 解析右边（表达式）
                right_node, pos = parse_expr(tokens, pos)

                return {
                    'type': 'alias',
                    'left': left_name,
                    'right': right_node,
                }, pos, linepos

            # 在 parse_stmt 里，处理 if/while/unless/until 之后，加上 match 的处理
            if t['type'] == 'name' and t['value'] == 'match':
                pos += 1

                # 解析要匹配的值（表达式）
                value_expr, pos = parse_expr(tokens, pos)

                # 检查 {
                if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != '{':
                    raise KeiError("SyntaxError", "match 后面需要 {")
                pos += 1

                # 解析所有 case 分支
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

                    # 检查是否是 case
                    if all_lines[current_line][current_pos]['type'] == 'name' and all_lines[current_line][current_pos]['value'] == 'case':
                        current_pos += 1

                        # 解析操作符和值
                        op = None
                        right = None

                        # 检查是否是 _
                        if current_pos < len(all_lines[current_line]) and all_lines[current_line][current_pos]['type'] == 'name' and all_lines[current_line][current_pos]['value'] == '_':
                            op = None
                            right = None
                            current_pos += 1
                        else:
                            # 解析操作符
                            if current_pos >= len(all_lines[current_line]):
                                raise KeiError("SyntaxError", "case 后面需要操作符")
                            op_token = all_lines[current_line][current_pos]
                            if op_token['type'] != 'op':
                                raise KeiError("SyntaxError", f"case 后面需要操作符，得到 {op_token}")
                            op = op_token['value']
                            current_pos += 1

                            # 解析右边的值
                            right, current_pos = parse_expr(all_lines[current_line], current_pos)

                        # 检查 {
                        if current_pos >= len(all_lines[current_line]) or all_lines[current_line][current_pos]['type'] != 'symbol' or all_lines[current_line][current_pos]['value'] != '{':
                            raise KeiError("SyntaxError", "case 后面需要 {")
                        current_pos += 1

                        # 解析 case 的 body
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

                            stmt, new_pos, new_line = parse_stmt(case_tokens, case_pos, all_lines, case_line)
                            if stmt:
                                body.append(stmt)

                            if new_line > case_line:
                                case_line = new_line
                                case_pos = new_pos
                            else:
                                case_pos = new_pos
                                if new_pos == case_pos:
                                    case_pos += 1

                        arms.append({
                            'op': op,
                            'right': right,
                            'body': body
                        })

                    else:
                        # 不是 case，可能是 }
                        if all_lines[current_line][current_pos]['type'] == 'symbol' and all_lines[current_line][current_pos]['value'] == '}':
                            current_pos += 1
                            break
                        else:
                            raise KeiError("SyntaxError", "match 块内只能有 case 语句")

                return {
                    'type': 'match',
                    'value': value_expr,
                    'arms': arms
                }, current_pos, current_line

            # 查找复合赋值
            compound_ops = {"+=", "-=", "*=", "/="}
            assig_pos = -1
            paren_count = 0
            bracket_count = 0
            brace_count = 0
            compound_op = None

            for i in range(pos, len(tokens)):
                token = tokens[i]
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

                if (token.get('type') == 'op' and token.get('value') in compound_ops
                    and paren_count == 0 and bracket_count == 0 and brace_count == 0):
                    assig_pos = i
                    compound_op = token.get('value')
                    break

            if assig_pos != -1 and assig_pos > pos:
                # ===== 解析左边（和 = 完全一致）=====
                left_tokens = tokens[pos:assig_pos]

                # 检查左边是否有逗号（多变量赋值）
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
                    # 多变量赋值左边
                    vars = []
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
                            vars.append(var_tokens[0]['value'])
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
                        vars.append(var_tokens[0]['value'])
                    elif len(var_tokens) > 0:
                        raise KeiError("SyntaxError", f"多变量赋值左边必须是变量名、*rest 或 **kwargs, 得到 {var_tokens}")

                    left_node = {'type': 'multiassign', 'vars': vars, 'rest': rest_var, 'kwargs': kwargs_var}
                else:
                    # 单变量或表达式
                    left_node, left_new_pos = parse_expr(left_tokens, 0, allow_assign=True)
                    if not left_node or left_new_pos != len(left_tokens):
                        raise KeiError("SyntaxError", f"无效的赋值左边: {left_tokens}")

                # ===== 解析右边（和 = 完全一致）=====
                right_tokens = tokens[assig_pos + 1:]

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
                    # 多值右边
                    elements = []
                    last_pos = 0

                    for comma_pos in right_comma_positions:
                        value_tokens = right_tokens[last_pos:comma_pos]

                        if value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '[':
                            val_node, _ = parse_list(value_tokens, 0)
                        elif value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '{':
                            val_node, _ = parse_dict(value_tokens, 0)
                        else:
                            val_node, _ = parse_expr(value_tokens, 0, allow_assign=False)

                        if val_node:
                            elements.append(val_node)
                        last_pos = comma_pos + 1

                    value_tokens = right_tokens[last_pos:]
                    if value_tokens:
                        if value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '[':
                            val_node, _ = parse_list(value_tokens, 0)
                        elif value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '{':
                            val_node, _ = parse_dict(value_tokens, 0)
                        else:
                            val_node, _ = parse_expr(value_tokens, 0, allow_assign=False)
                        if val_node:
                            elements.append(val_node)

                    right_node = {'type': 'list', 'elements': elements}
                    final_pos = assig_pos + 1 + len(right_tokens)
                else:
                    # 单值右边
                    if right_tokens and right_tokens[0]['type'] == 'symbol' and right_tokens[0]['value'] == '{':
                        right_node, right_new_pos = parse_dict(right_tokens, 0)
                    elif right_tokens and right_tokens[0]['type'] == 'symbol' and right_tokens[0]['value'] == '[':
                        right_node, right_new_pos = parse_list(right_tokens, 0)
                    else:
                        right_node, right_new_pos = parse_expr(right_tokens, 0, allow_assign=False)

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

            # 查找 = 位置
            assig_pos = -1
            paren_count = 0
            bracket_count = 0
            brace_count = 0

            for i in range(pos, len(tokens)):
                token = tokens[i]
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

                if (token.get('type') == 'op' and token.get('value') == "="
                    and paren_count == 0 and bracket_count == 0 and brace_count == 0):
                    assig_pos = i
                    break

            if assig_pos != -1 and assig_pos > pos:
                left_tokens = tokens[pos:assig_pos]

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
                    vars = []
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
                            vars.append(var_tokens[0]['value'])
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
                        vars.append(var_tokens[0]['value'])
                    elif len(var_tokens) > 0:
                        raise KeiError("SyntaxError", f"多变量赋值左边必须是变量名、*rest 或 **kwargs, 得到 {var_tokens}")

                    left_node = {'type': 'multiassign', 'vars': vars, 'rest': rest_var, 'kwargs': kwargs_var}
                else:
                    left_node, left_new_pos = parse_expr(left_tokens, 0, allow_assign=True)
                    if not left_node or left_new_pos != len(left_tokens):
                        raise KeiError("SyntaxError", f"无效的赋值左边: {left_tokens}")

                right_tokens = tokens[assig_pos + 1:]

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
                            val_node, _ = parse_list(value_tokens, 0)
                        elif value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '{':
                            val_node, _ = parse_dict(value_tokens, 0)
                        else:
                            val_node, _ = parse_expr(value_tokens, 0, allow_assign=False)

                        if val_node:
                            elements.append(val_node)
                        last_pos = comma_pos + 1

                    value_tokens = right_tokens[last_pos:]
                    if value_tokens:
                        if value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '[':
                            val_node, _ = parse_list(value_tokens, 0)
                        elif value_tokens and value_tokens[0]['type'] == 'symbol' and value_tokens[0]['value'] == '{':
                            val_node, _ = parse_dict(value_tokens, 0)
                        else:
                            val_node, _ = parse_expr(value_tokens, 0, allow_assign=False)
                        if val_node:
                            elements.append(val_node)

                    right_node = {'type': 'list', 'elements': elements}
                    final_pos = assig_pos + 1 + len(right_tokens)
                else:
                    if right_tokens and right_tokens[0]['type'] == 'symbol' and right_tokens[0]['value'] == '{':
                        right_node, right_new_pos = parse_dict(right_tokens, 0)
                    elif right_tokens and right_tokens[0]['type'] == 'symbol' and right_tokens[0]['value'] == '[':
                        right_node, right_new_pos = parse_list(right_tokens, 0)
                    else:
                        right_node, right_new_pos = parse_expr(right_tokens, 0, allow_assign=False)

                    if not right_node:
                        raise KeiError("SyntaxError", "无效的赋值右边")
                    final_pos = assig_pos + 1 + right_new_pos

                node = {'type': 'assign', 'left': left_node, 'right': right_node}
                return node, final_pos, linepos

            # 不是赋值语句，作为表达式解析
            node, new_pos = parse_expr(tokens, pos, allow_assign=False)
            if node is None:
                if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '}':
                    return None, pos, linepos

                raise KeiError("SyntaxError", f"无效的语法: {tokens[pos]['value'] if pos < len(tokens) else 'EOF'}")
            return node, new_pos, linepos

        node, new_pos, new_line = stmt()
        if node is not None:
            return node | {'source':globals()['code'],'linenum':globals()['linenum']}, new_pos, new_line
        else:
            return None, new_pos, new_line

    except KeiError as e:
        raise KeiError(e.types, e.value, globals()['code'], globals()['linenum'])

    except Exception as e:
        raise KeiError(type(e).__name__, str(e), globals()['code'], globals()['linenum'])

def parse_index(tokens: list, pos: int) -> tuple:
    """解析索引访问, 递归解析整个链条"""

    # 1. 先解析出左边的对象（可能是名字、属性访问、另一个索引等）
    obj_node, pos = parse_expr(tokens, pos)  # ← 关键！先递归解析左边！

    # 2. 然后解析索引
    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '[':
        pos += 1  # 跳过 '['

        # 解析索引表达式
        index, pos = parse_expr(tokens, pos)

        # 检查 ']'
        if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != ']':
            raise KeiError("SyntaxError", "缺少 ]")
        pos += 1

        # 创建索引节点
        node = {
            'type': 'index',
            'obj': obj_node,  # 左边是解析出来的节点
            'index': index
        }

        # 3. 递归处理后续的索引（比如 [1][2]）
        while pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '[':
            pos += 1
            index, pos = parse_expr(tokens, pos)
            if pos >= len(tokens) or tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != ']':
                raise KeiError("SyntaxError", "缺少 ]")
            pos += 1
            node = {
                'type': 'index',
                'obj': node,  # 上一层的索引节点
                'index': index
            }

        return node, pos

    # 如果没有索引, 返回左边解析的结果
    return obj_node, pos

def parse_dictcomp(tokens, pos):
    """解析字典生成式 {key: value for var in iterable} 或 {key: value for var in iterable if cond}"""
    ifunless = None
    pos += 1  # 跳过 '{'

    # 解析 key
    key, pos = parse_expr(tokens, pos, in_comp=True)

    # 检查 ':'
    if pos >= len(tokens) or tokens[pos].get('value') != ':':
        raise KeiError("SyntaxError", "字典生成式需要 ':'")
    pos += 1  # 跳过 ':'

    # 解析 value
    value, pos = parse_expr(tokens, pos, in_comp=True)

    # 检查 'for'
    if pos >= len(tokens) or tokens[pos].get('value') != 'for':
        raise KeiError("SyntaxError", "字典生成式需要 'for'")
    pos += 1  # 跳过 'for'

    # 解析变量名
    if pos >= len(tokens) or tokens[pos]['type'] != 'name':
        raise KeiError("SyntaxError", "字典生成式需要变量名")
    var = tokens[pos]['value']
    pos += 1

    # 检查 'in'
    if pos >= len(tokens) or tokens[pos].get('value') != 'in':
        raise KeiError("SyntaxError", "字典生成式需要 'in'")
    pos += 1  # 跳过 'in'

    # 解析可迭代对象
    iterable, pos = parse_expr(tokens, pos, in_comp=True)

    # 可选的条件
    cond = None
    if pos < len(tokens) and tokens[pos].get('value') == 'if':
        ifunless = tokens[pos]['value']
        pos += 1  # 跳过 'if'
        cond, pos = parse_expr(tokens, pos, in_comp=True)  # 避免三目混淆

    # 检查 '}'
    if pos >= len(tokens) or tokens[pos].get('value') != '}':
        raise KeiError("SyntaxError", "字典生成式缺少 '}'")
    pos += 1

    if ifunless == "if":
        rettype = 'dictcomp'
    elif ifunless == "unless":
        rettype = 'undictcomp'
    else:
        rettype = undefined

    return {
        'type': rettype,
        'key': key,
        'value': value,
        'var': var,
        'iterable': iterable,
        'cond': cond
    }, pos

def parse_dict(tokens: list, pos: int) -> tuple:
    """解析字典 {"key": value} 或 {key: value for x in iterable}"""
    start_pos = pos
    pos += 1  # 跳过 '{'

    # 先看看是不是字典生成式
    bracket_count = 1
    for i in range(pos, len(tokens)):
        if tokens[i].get('value') == '{':
            bracket_count += 1
        elif tokens[i].get('value') == '}':
            bracket_count -= 1
            if bracket_count == 0:
                break
        elif tokens[i].get('value') == 'for' and bracket_count == 1:
            return parse_dictcomp(tokens, start_pos)

    # 普通字典
    pairs = []

    # 空字典
    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '}':
        pos += 1
        return {'type': 'dict', 'pairs': pairs}, pos

    # 解析键值对
    while pos < len(tokens):
        # 如果遇到 }, 结束解析
        if tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '}':
            pos += 1
            break

        # 键可以是字符串数字或名字
        if tokens[pos]['type'] == 'str':
            key = tokens[pos]['value']
        if tokens[pos]['type'] == 'str':
            key = tokens[pos]['value']
        elif tokens[pos]['type'] == 'int':
            key = int(tokens[pos]['value'])
        elif tokens[pos]['type'] == 'float':
            key = float(tokens[pos]['value'])
        else:
            raise KeiError("SyntaxError", f"字典键必须是字符串或数字或名字, 得到 {tokens[pos]['value']}")
        pos += 1

        # 检查冒号
        if pos >= len(tokens):
            raise KeiError("SyntaxError", "字典键值对缺少 :")
        if tokens[pos]['type'] != 'symbol' or tokens[pos]['value'] != ':':
            raise KeiError("SyntaxError", f"字典键值对缺少 :, 得到 {tokens[pos]['value']}")

        pos += 1

        # 解析值
        value, new_pos = parse_expr(tokens, pos)

        if value is None:
            raise KeiError("SyntaxError", "字典值不能为空")

        pairs.append({'key': key, 'value': value})
        pos = new_pos

        # 检查逗号或结束
        if pos < len(tokens):
            if tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
                pos += 1
                continue
            elif tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == '}':
                pos += 1
                break
            else:
                continue
        else:
            break

    return {'type': 'dict', 'pairs': pairs}, pos

def parse_unary(tokens: list, pos: int, in_call=False) -> tuple:
    """新的 parse_unary：处理后缀 ->（优先级最高）"""

    # 1. 先解析前缀一元（not, -, ++, --）和原子
    left, pos = parse_unary_prefix(tokens, pos, in_call)

    # 2. 处理后缀操作符（优先级从高到低）
    while pos < len(tokens):
        t = tokens[pos]

        # 处理 ->（类型断言，优先级最高）
        if t.get('type') == 'op' and t.get('value') == '->':
            pos += 1
            type_node, pos = parse_atom(tokens, pos, in_call)
            left = {
                'type': 'typeassert',
                'expr': left,
                'hint': type_node
            }

        # 处理 ??（空值合并后缀，优先级次高）
        elif t.get('type') == 'op' and t.get('value') == '??':
            pos += 1

            right, pos = parse_atom(tokens, pos, in_call)
            left = {
                'type': 'coalesce',
                'left': left,
                'right': right
            }

        else:
            break

    return left, pos

def parse_unary_prefix(tokens: list, pos: int, in_call=False) -> tuple:
    """旧的 parse_unary：处理前缀一元运算符"""
    if pos >= len(tokens):
        return None, pos

    t = tokens[pos]

    # 处理前缀 ++
    if t["type"] == "op" and t["value"] in {"++", "--"}:
        op = t["value"]
        pos += 1
        expr, pos = parse_unary_prefix(tokens, pos, in_call)
        return {"type": "prefix", "op": op, "expr": expr}, pos

    # 处理 not
    if t["type"] == "op" and t["value"] == "not":
        pos += 1
        expr, pos = parse_unary_prefix(tokens, pos, in_call)
        return {"type": "unary", "op": "not", "expr": expr}, pos

    # 处理一元负号
    if t["type"] == "op" and t["value"] == "-":
        pos += 1
        expr, pos = parse_unary_prefix(tokens, pos, in_call)
        return {"type": "unary", "op": "-", "expr": expr}, pos

    # 原子
    return parse_atom(tokens, pos, in_call)

def parse_methodcall(parts: list, tokens: list, pos: int) -> tuple:
    """解析方法调用（处理链式调用）"""
    # 获取方法名
    method_name = parts[-1] if isinstance(parts[-1], str) else parts[-1].get('method')

    pos += 1  # 跳过 '('

    args = []

    # 如果没有参数
    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ')':
        pos += 1
        return {
            'type': 'methodcall',
            'obj_parts': parts[:-1],
            'method': method_name,
            'args': args
        }, pos

    # 解析第一个参数
    arg, pos = parse_expr(tokens, pos)
    if arg:
        args.append(arg)

    # 继续解析后续参数
    while pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
        pos += 1
        arg, pos = parse_expr(tokens, pos)
        if arg:
            args.append(arg)

    # 跳过 ')'
    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ')':
        pos += 1

    return {
        'type': 'methodcall',
        'obj_parts': parts[:-1],
        'method': method_name,
        'args': args
    }, pos

def parse_listcomp(tokens, pos):
    """解析列表生成式 [expr for var in iterable] 或 [expr for var in iterable if cond]"""
    ifunless = None
    pos += 1  # 跳过 '['

    # 解析表达式
    expr, pos = parse_expr(tokens, pos, in_comp=True)

    # 检查 'for'
    if pos >= len(tokens) or tokens[pos].get('value') != 'for':
        raise KeiError("SyntaxError", "列表生成式需要 'for'")
    pos += 1  # 跳过 'for'

    # 解析变量名
    if pos >= len(tokens) or tokens[pos]['type'] != 'name':
        raise KeiError("SyntaxError", "列表生成式需要变量名")
    var = tokens[pos]['value']
    pos += 1

    # 检查 'in'
    if pos >= len(tokens) or tokens[pos].get('value') != 'in':
        raise KeiError("SyntaxError", "列表生成式需要 'in'")
    pos += 1  # 跳过 'in'

    # 解析可迭代对象
    iterable, pos = parse_expr(tokens, pos, in_comp=True)

    # 可选的条件
    cond = None
    if pos < len(tokens) and tokens[pos].get('value') == 'if':
        ifunless = tokens[pos]['value']
        pos += 1  # 跳过 'if'
        cond, pos = parse_expr(tokens, pos, in_comp=True)

    # 检查 ']'
    if pos >= len(tokens) or tokens[pos].get('value') != ']':
        raise KeiError("SyntaxError", "列表生成式缺少 ']'")
    pos += 1  # 跳过 ']'

    if ifunless == "if":
        rettype = 'listcomp'
    elif ifunless == "unless":
        rettype = 'unlistcomp'
    else:
        rettype = undefined

    return {
        'type': rettype,
        'expr': expr,
        'var': var,
        'iterable': iterable,
        'cond': cond
    }, pos

def parse_list(tokens: list, pos: int) -> tuple:
    """解析列表 [1, 2, 3] 或生成器 [expr for var in iterable]"""

    start_pos = pos
    pos += 1  # 跳过 '['

    # 先看看是不是生成器
    bracket_count = 1
    for i in range(pos, len(tokens)):
        if tokens[i].get('value') == '[':
            bracket_count += 1
        elif tokens[i].get('value') == ']':
            bracket_count -= 1
            if bracket_count == 0:
                break
        elif tokens[i].get('value') == 'for' and bracket_count == 1:
            # 是生成器，重新解析
            return parse_listcomp(tokens, start_pos)

    # 不是生成器，按普通列表解析
    elements = []

    # 如果直接遇到 ], 返回空列表
    if pos < len(tokens) and tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ']':
        pos += 1
        return {'type': 'list', 'elements': elements}, pos

    # 循环解析所有元素
    while True:
        # 保存当前位置
        current_pos = pos

        # 解析当前元素
        elem, new_pos = parse_expr(tokens, pos)

        if elem:
            elements.append(elem)
            pos = new_pos
        else:
            pos = current_pos + 1  # 跳过当前 token

        # 检查下一个 token
        if pos >= len(tokens):
            break

        # 如果是逗号, 跳过并继续
        if tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ',':
            pos += 1
            continue

        # 如果是 ], 结束
        if tokens[pos]['type'] == 'symbol' and tokens[pos]['value'] == ']':
            pos += 1
            break

        # 其他情况, 退出循环
        break

    return {'type': 'list', 'elements': elements}, pos

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

    if 'source' not in globals():
        globals()['source'] = None
    if 'linenum' not in globals():
        globals()['linenum'] = None

    def runtokentemp() -> tuple:
        if node.get('source', None) is not None:
            globals()['source']  = node.get('source')

        if node.get('linenum', None) is not None:
            globals()['linenum'] = node.get('linenum')

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

        if node is None:
            return None, False

        # ========== 字面量 - 返回 Kei 对象 ==========
        if node['type'] in {'null', 'int', 'float', 'str', 'bool', 'list', 'dict'}:
            def temp() -> tuple:
                if node['type'] == 'null':
                    return null, False
                if node['type'] == 'int':
                    return KeiInt(int(node['value'])), False
                if node['type'] == 'float':
                    prec = env.get("__precision__", KeiInt(28))
                    if not isinstance(prec, KeiInt):
                        prec = KeiInt(28)
                    if prec.value <= 0:
                        raise KeiError("ValueError", "浮点数精度不能小于或等于 0")
                    return KeiFloat(node['value'], prec.value), False
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

        if node['type'] == 'alias':
            left_name = node['left']['value']
            target_name = node['right']['value']

            env[left_name] = KeiRef(env, target_name)
            return env[left_name], False

        # ========== match/case 语句 ==========
        if node['type'] == 'match':
            value, _ = runtoken(node['value'], env)

            for arm in node['arms']:
                if arm['op'] is None:
                    # 直接执行 body
                    for stmt in arm['body']:
                        val, is_return = runtoken(stmt, env)
                        if is_return:
                            return val, True

                    return None, False

                # 手动构造 binop AST 节点
                cond_node = {
                    'type': 'binop',
                    'op': arm['op'],  # 比如 '==', '>', '<'
                    'left': {'type': 'name', 'value': node['value']['value']},  # 变量名
                    'right': arm['right']  # 比较的值
                }

                # 🔥 让 runtoken 去执行 binop！
                cond, _ = runtoken(cond_node, env)

                if cond:
                    for stmt in arm['body']:
                        val, is_return = runtoken(stmt, env)
                        if is_return:
                            return val, True
                    break

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

            if left_val:
                return left_val, left_flag

            right_val, right_flag = runtoken(node['right'], env)
            return right_val, right_flag

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
                val, flag = runtoken(node['expr'], env)
                return val, flag
            except:
                return null, False

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
                    return val, flag
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
                    return val, flag
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

        if node['type'] in {'listcomp', 'unlistcomp'}:
            un = True if node['type'] == "unlistcomp" else False
            result = []
            iterable_val, _ = runtoken(node['iterable'], env)
            var_name = node['var']
            expr = node['expr']
            cond = node.get('cond')  # 可能没有 cond

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
                env[var_name] = item

                # 如果有条件，先判断
                if cond:
                    cond_val, _ = runtoken(cond, env)
                    if un:
                        if cond_val:
                            continue
                    else:
                        if not cond_val:
                            continue

                val, _ = runtoken(expr, env)
                result.append(val)

            return KeiList(result), False

        if node['type'] in {'dictcomp', 'undictcomp'}:
            un = True if node['type'] == "undictcomp" else False
            result = {}
            iterable_val, _ = runtoken(node['iterable'], env)
            var_name = node['var']
            key_expr = node['key']
            value_expr = node['value']
            cond = node.get('cond')

            # 获取可迭代对象
            if isinstance(iterable_val, KeiList):
                items = iterable_val.items
            elif isinstance(iterable_val, KeiString):
                items = [KeiString(c) for c in iterable_val.value]
            else:
                try:
                    items = list(iterable_val)
                except:
                    items = [iterable_val]

            # 遍历
            for item in items:
                env[var_name] = item

                # 如果有条件，先判断
                if cond:
                    cond_val, _ = runtoken(cond, env)
                    if un:
                        if cond_val:
                            continue
                    else:
                        if not cond_val:
                            continue

                key, _ = runtoken(key_expr, env)
                val, _ = runtoken(value_expr, env)

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
                    raise KeiError("TypeError", f"无法对 {val} 进行取负运算")

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
            # ----- 1. 统一解析参数 -----
            args = []
            kwargs = {}

            # 普通参数
            for arg in node.get('args', []):
                val, _ = runtoken(arg, env)
                args.append(val)

            # 关键字参数
            for key, value in node.get('kwargs', {}).items():
                val, _ = runtoken(value, env)
                kwargs[key] = val

            # 解包 *args
            if node.get('starargs'):
                star_val, _ = runtoken(node['starargs'], env)
                if isinstance(star_val, KeiList):
                    args.extend(star_val.items)
                elif isinstance(star_val, (list, tuple)):
                    args.extend(star_val)
                else:
                    args.append(star_val)

            # 解包 **kwargs
            if node.get('starkwargs'):
                star_val, _ = runtoken(node['starkwargs'], env)
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
                            if i < len(node.get('args', [])):
                                arg_val, _ = runtoken(node['args'][i], env)
                                new_env[p] = arg_val
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

                    # 逐级访问属性
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
                            # KeiLang 函数 - 直接传递所有参数
                            result = method(*args, **kwargs)
                        else:
                            # Python 函数
                            result = method(*args, **kwargs)
                        return result, False
                    raise KeiError("NameError", f"对象没有方法 {method_name}")

                # 普通函数/类调用
                if name in env:
                    func_obj = env[name]

                    if isinstance(func_obj, KeiInstance) and hasattr(func_obj, '__call__'):
                        # 调用 __call__ 方法
                        result = func_obj.__call__(*args, **kwargs)
                        return result, False

                    if isinstance(func_obj, KeiClass):
                        # 类实例化
                        instance = func_obj(*args, **kwargs)
                        init_method = find_method(func_obj.class_obj, '__init__', env)
                        if init_method:
                            new_env = {'__parent__': init_method['closure'], 'self': instance}
                            new_env.update({k: v for k, v in init_method['closure'].items() if k != '__parent__'})

                            # 绑定参数
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
                        # KeiLang 函数 - 直接传递参数
                        return func_obj(*args, **kwargs), False

                    if callable(func_obj):
                        return func_obj(*args, **kwargs), False

                # 标准库函数
                if name in stdlib.func:
                    result = stdlib.func[name](*args, **kwargs)
                    return result, False

                raise KeiError("NameError", f"未知函数: {name}")

            # ----- 3. 处理 methodcall -----
            else:  # node['type'] == 'methodcall'
                # 解析对象和方法名
                obj = None
                method_name = None

                if 'obj' in node and isinstance(node['obj'], dict):
                    if node['obj'].get('type') == 'attr':
                        obj, _ = runtoken(node['obj']['obj'], env)
                        method_name = node['obj']['attr']
                    else:
                        obj, _ = runtoken(node['obj'], env)
                        method_name = node.get('method')

                elif 'obj_parts' in node:
                    for part in node['obj_parts']:
                        if obj is None:
                            obj = env.get(part) if isinstance(part, str) else runtoken(part, env)[0]
                        else:
                            if isinstance(obj, KeiBase):
                                obj = obj[part]
                            elif isinstance(obj, dict):
                                obj = obj.get(part)
                            else:
                                obj = getattr(obj, part)
                    method_name = node['method']

                if obj is None:
                    raise KeiError("NameError", "对象未定义")
                if method_name is None:
                    raise KeiError("NameError", "方法名未定义")

                # 获取并调用方法
                method = obj[method_name] if isinstance(obj, KeiBase) else getattr(obj, method_name, None)

                if method is undefined or not callable(method):
                    raise KeiError("SyntaxError", f"方法 {method_name} 调用失败")

                # 🔥 判断这是不是命名空间/字典中的函数（不需要 self）
                is_namespace_func = isinstance(obj, KeiNamespace) or (isinstance(obj, KeiDict) and method_name in obj.items)

                # 处理 KeiLang 函数/方法
                if isinstance(method, (KeiFunction, KeiMethod, KeiBoundMethod)):
                    # 获取参数信息
                    if isinstance(method, KeiFunction):
                        params = method.func_obj['params']
                    else:
                        params = method.method_obj['params']

                    # 分离参数类型
                    regular_params = []
                    star_param = starstar_param = None
                    for p in params:
                        if p.startswith('**'):
                            starstar_param = p[2:]
                        elif p.startswith('*'):
                            star_param = p[1:]
                        else:
                            regular_params.append(p)

                    # 🔥 关键修复：如果是命名空间函数，当作普通函数调用
                    if is_namespace_func:
                        # 命名空间函数 - 直接传递所有参数，不需要 self
                        if star_param:
                            result = method(*args, **kwargs)
                        elif starstar_param:
                            result = method(*args, **kwargs)
                        else:
                            # 按位置匹配参数
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
                        return result, False

                    # 普通方法调用（需要 self）
                    is_bound = isinstance(method, KeiBoundMethod) or hasattr(method, '__self__')

                    if is_bound:
                        # 已绑定的方法
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
                        # 未绑定的方法，需要传递 self
                        # self 就是 obj
                        call_args = [obj]  # self 作为第一个参数
                        remaining = kwargs.copy()
                        # 从 regular_params[1:] 开始（跳过 self）
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

                # Python 函数/方法
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
                items = [(KeiString(k), v) for k, v in iterable_val.items.items()]
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
                'methods': [],
                'methods_map': {}
            }

            if class_obj['parent']:
                parent = env.get(class_obj['parent'])
                if parent is None or parent is undefined:
                    raise KeiError("NameError", f"父类 '{class_obj['parent']}' 未定义")
                if not isinstance(parent, KeiClass):
                    raise KeiError("TypeError", f"'{class_obj['parent']}' 不是类")
                try:
                    class_obj['methods_map'] = copy.deepcopy(parent.class_obj['methods_map'])
                except:
                    try:
                        class_obj['methods_map'] = copy.copy(parent.class_obj['methods_map'])
                    except:
                        class_obj['methods_map'] = parent.class_obj['methods_map'].copy()

            for method in node['methods']:
                if method['type'] == 'function':
                    method_obj = {
                        'type': 'user_function',
                        'name': method['name'],
                        'params': method['params'],
                        'body': method['body'],
                        'defaults': method.get('defaults', {}),
                        'decorators': method.get('decorators', []),
                        'is_property': False,
                        'is_method': True,
                        'closure': env
                    }
                    # 检查是否有 @prop 装饰器
                    if 'decorators' in method:
                        for dec in method['decorators']:
                            if dec['value'] == 'prop':
                                method_obj['is_property'] = True

                    class_obj['methods'].append(method_obj)
                    class_obj['methods_map'][method['name']] = method_obj

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

                    lib_path = os.path.join(keidir, 'lib')

                    assert isinstance(env.get("__path__", KeiList([])), KeiList), "__path__需要是一个列表"

                    __path__ = env.get("__path__", KeiList([])).items

                    full_module_name = full_module_name.replace('.', '/')

                    module_name = full_module_name.split("/")[-1]

                    # ==== 1. 先找 .kei 文件（KeiLang 模块）====

                    kei_file = os.path.join(lib_path, f"{full_module_name}.kei")
                    kei_files = [os.path.join(path, f"{full_module_name}.kei") for path in __path__] + [kei_file]

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
                    py_file = os.path.join(lib_path, f"{full_module_name}.py")
                    py_files = [os.path.join(path, f"{full_module_name}.py") for path in __path__] + [py_file]

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
                                    print(name)
                                    env[name] = value
                            else:
                                name = alias or full_module_name
                                print(name)
                                env[name] = KeiNamespace(name, module_dict)

                            return None, False

                    # ==== 3. 都找不到就报错 ====
                    raise KeiError("ImportError", f"找不到模块: {full_module_name}")

                return None, False

            except Exception as e:
                raise KeiError("ImportError", f"导入模块失败: {e}")

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

                        raise err
                    else:
                        raise KeiError("Runtime", "异常抛出失败: __error__栈不是list")

                else:
                    raise KeiError("Runtime", "没有异常可抛出")

        if node['type'] == 'merge':
            if len(node['names']) >= 1:
                for name in node['names']:
                    if isinstance(env[name['value']], KeiNamespace):
                        env.update(env[name['value']].env)
                    else:
                        raise KeiError("TypeError", "merge 需要 namespace")

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
                if node['catchbody'] is not None:
                    old_e = env.get(node['var']) if node['var'] else None
                    if isinstance(e, KeiError):
                        err_obj = Error(e.types, e.value)
                    else:
                        err_obj = Error(type(e).__name__, str(e))

                    if node['var']:
                        env[node['var']] = err_obj

                    env.setdefault('__error__', []).append(err_obj)

                    for stmt in node['catchbody']:
                        val, is_return = runtoken(stmt, env)
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
            else:
                if node['finallybody']:
                    for f_stmt in node['finallybody']:
                        f_val, f_is_return = runtoken(f_stmt, env)
                        if f_is_return:
                            return f_val, True

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
        return runtokentemp()

    except ZeroDivisionError:
        raise KeiError("ZeroDivisionError",
                       "无法对 0 进行除法",
                       (globals()['source']
                       if globals()['source'] is not None
                       else node.get('source', None)),
                       (globals()['linenum']
                       if globals()['linenum'] is not None
                       else node.get('linenum', None))
        )

    except OverflowError as e:
        raise KeiError("OverflowError",
                       f"数值过大, 无法处理: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except FloatingPointError as e:
        raise KeiError("FloatingPointError",
                       f"浮点运算错误: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except ArithmeticError as e:
        raise KeiError("ArithmeticError",
                       f"运算错误: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except IndexError as e:
        raise KeiError("IndexError",
                       f"索引超出范围: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except KeyError as e:
        raise KeiError("KeyError",
                       f"键不存在: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except LookupError as e:
        raise KeiError("LookupError",
                       f"查找错误: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except TypeError as e:
        raise KeiError("TypeError",
                       f"类型错误: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except ValueError as e:
        raise KeiError("ValueError",
                       f"值错误: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except AttributeError as e:
        raise KeiError("AttributeError",
                       f"属性不存在: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except UnboundLocalError as e:
        raise KeiError("UnboundLocalError",
                       f"局部变量未绑定: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except NameError as e:
        raise KeiError("NameError",
                       f"名称未定义: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except FileNotFoundError as e:
        raise KeiError("NotFoundError",
                       f"文件未找到: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except PermissionError as e:
        raise KeiError("PermissionError",
                       f"权限不足无法访问文件: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except IsADirectoryError as e:
        raise KeiError("IsDirError",
                       f"预期文件但得到目录: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except NotADirectoryError as e:
        raise KeiError("NotDirError",
                       f"预期目录但得到文件: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except FileExistsError as e:
        raise KeiError("FileExistsError",
                       f"文件已存在: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except TimeoutError as e:
        raise KeiError("TimeoutError",
                       f"操作超时: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except OSError as e:
        raise KeiError("OSError",
                       f"操作系统错误: {e}",
                       (globals()['source'] if globals()['source'] is not None else node.get('source', None)),
                       (globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)))

    except RecursionError:
        raise KeiError("RecursionError",
                       f"递归超过{f" {env['__maxrecursion__']} " if env.get('__maxrecursion__', False) else ''}限制",
                       (globals()['source']
                       if globals()['source'] is not None
                       else node.get('source', None)),
                       (globals()['linenum']
                       if globals()['linenum'] is not None
                       else node.get('linenum', None))
        )

    except KeiError as e:
        if e.code is None:
            e.code = globals()['source'] if globals()['source'] is not None else node.get('source', None)

        if e.linenum == -1:
            e.linenum = globals()['linenum'] if globals()['linenum'] is not None else node.get('linenum', -1)

        raise

    except Exception as e:
        raise KeiError(type(e).__name__,
                       str(e),
                       (globals()['source']
                       if globals()['source'] is not None
                       else node.get('source', None)),
                       (globals()['linenum']
                       if globals()['linenum'] is not None
                       else node.get('linenum', None))
        )

def exec(code, env=None, compile:str|bool=False, fromjson:bool=False):
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

    if not fromjson:
        tokens = token(code)
        tokens = ast(tokens)
    else:
        import json
        tokens = json.loads(code)

    if not compile:
        for node in tokens:
            ret = runtoken(node, env)[0]

    else:
        import json
        json.dump(tokens, open(compile, "w"), indent=4, ensure_ascii=False)

    return env, ret

def execmain(code, env=None, compile:str|bool=False, fromjson:bool=False):
    if len(sys.argv) >= 3:
        cmd_args = []
        for arg in (sys.argv[2:] if not ((sys.argv[2] == '-j' or sys.argv[2] == '--json') and fromjson) else sys.argv[3:]):
            cmd_args.append(f'{arg}')

        code += f"\nmain({[','.join(cmd_args)]});"
    else:
        code += f"\nmain();"

    env, ret = exec(code, env, compile, fromjson)

    if compile:
        return 0

    if type(ret) in HASVALUE:
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
            print("  \033[33m<啥都木有>\033[0m - \033[36m进入REP\033[0m")
            print("  \033[33m<文件名>\033[0m   - \033[36m运行Kei脚本\033[0m")
            print()
            print("\033[1m参数:\033[0m")
            print("  \033[33m-h/--help\033[0m  - \033[36m显示此帮助\033[0m")
            print("  \033[33m-c\033[0m         - \033[36m将AST编译为json\033[0m")
            print()
            sys.exit(0)

        if len(sys.argv) >= 2:
            if os.path.isfile(sys.argv[1]):
                globals()['file'] = sys.argv[1]

                with open(sys.argv[1], "r", encoding="utf-8") as f:
                    filecontent = f.read()

                    # print("========== AST ==========") #DEBUG
                    # print(ast(token(filecontent)))     #DEBUG
                    # print("========== AST ==========") #DEBUG
                    # print()                            #DEBUG

                    if not ("-c" in sys.argv or "--compile" in sys.argv):
                        execmain(filecontent, fromjson=True if (sys.argv[1].endswith(".json") or "-j" in sys.argv or "--json" in sys.argv) else False)
                    else:
                        if len(sys.argv) >= 4:
                            execmain(filecontent, compile=sys.argv[2])
                        else:
                            print("格式: kei <输入文件> <输出文件> -c")
            else:
                raise KeiError("NotFoundError", f"未找到 {sys.argv[1]}")

        else:
            import repl
            repl.main()

    except KeyboardInterrupt:
        exit()
    except ZeroDivisionError as e:
        error(f"除数不能为零: {e}")
    except OverflowError as e:
        error(f"数值过大, 无法处理: {e}")
    except FloatingPointError as e:
        error(f"浮点运算错误: {e}")
    except ArithmeticError as e:
        error(f"运算错误: {e}")
    except IndexError as e:
        error(f"索引超出范围: {e}")
    except KeyError as e:
        error(f"键不存在: {e}")
    except LookupError as e:
        error(f"查找错误: {e}")
    except TypeError as e:
        error(f"类型错误: {e}")
    except ValueError as e:
        error(f"值错误: {e}")
    except AttributeError as e:
        error(f"属性不存在: {e}")
    except UnboundLocalError as e:
        error(f"局部变量未绑定: {e}")
    except NameError as e:
        error(f"名称未定义: {e}")
    except FileNotFoundError as e:
        error(f"文件未找到: {e}")
    except PermissionError as e:
        error(f"权限不足无法访问文件: {e}")
    except IsADirectoryError as e:
        error(f"预期文件但找到目录: {e}")
    except NotADirectoryError as e:
        error(f"预期目录但找到文件: {e}")
    except FileExistsError as e:
        error(f"文件已存在: {e}")
    except TimeoutError as e:
        error(f"操作超时: {e}")
    except OSError as e:
        error(f"操作系统错误: {e}")
    except RecursionError as e:
        error(f"递归深度超过限制: {e}")
    except KeiError as e:
        if not __kei__.get('stack') is None:
            error(e, stack=__kei__['stack'], code=e.code, linenum=e.linenum+1, filename=globals()['file'])
        else:
            error(e, code=e.code, linenum=e.linenum+1, filename=globals()['file'])

    except Exception as e:
        error(f"{e}")

if __name__ == "__main__":
    sys.exit(main())

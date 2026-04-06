import platform
import inspect
import copy
import sys
import os

import stdlib
from lib.object import *
from kei import __kei__, runtoken, get_from_env, process_fstring, find_method, paths, __py_exec__, exec

def node_literal(node, env) -> tuple: # if node['type'] in {'null', 'int', 'float', 'str', 'bool', 'list', 'dict'}:
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
                key_val, _ = runtoken(pair['key'], env)
                val, _ = runtoken(pair['value'], env)

                # 检查键类型是否可哈希
                if not isinstance(key_val, (KeiInt, KeiString, KeiFloat)):
                    raise KeiError("TypeError",
                        f"字典键必须是整数、字符串或浮点数，得到 {type(key_val).__name__}")

                pairs[key_val] = val
            return KeiDict(pairs), False

        return None, False

    return temp()

def node_match(node, env) -> tuple: # if node['type'] == 'match':
    value, _ = runtoken(node['value'], env)

    for arm in node['arms']:
        matched = False

        for pattern_node in arm['patterns']:
            if pattern_node['type'] == 'wildcard':
                matched = True
                break

            elif pattern_node['type'] == 'expr':
                pattern_val, _ = runtoken(pattern_node['value'], env)
                if value.__eq__(pattern_val):
                    matched = True
                    break

            elif pattern_node['type'] == 'or_pattern':
                for sub_pattern in pattern_node['patterns']:
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

def node_name(node, env) -> tuple: # if node['type'] == 'name':
    name_value = node['value']
    while isinstance(name_value, dict) and 'value' in name_value:
        name_value = name_value['value']

    if name_value == "..." and "..." in env:
        return env["..."], False

    parts = name_value.split('.') if '.' in name_value else [name_value]

    # 关键：统一向上查找
    obj = get_from_env(parts[0], env)

    if obj is undefined:
        return undefined, False

    for part in parts[1:]:
        if isinstance(obj, KeiBase):
            obj = obj[part]
        elif isinstance(obj, dict):
            obj = obj.get(part, undefined)
        else:
            try:
                obj = getattr(obj, part)
            except AttributeError:
                return undefined, False
        if obj is undefined:
            return undefined, False

    return obj, False

def node_coalesce(node, env) -> tuple: # if node['type'] == 'coalesce':
    left_val, left_flag = runtoken(node['left'], env)

    if left_flag:
        return left_val, True

    if not (left_val is undefined or left_val is null):
        return left_val, left_flag

    right_val, right_flag = runtoken(node['right'], env)
    return right_val, right_flag

def node_notnullassert(node, env) -> tuple: # if node['type'] == 'notnullassert':
    val, flag = runtoken(node['expr'], env)

    if flag:
        return val, True

    if val is undefined or val is null:
        raise KeiError("TypeError", f"非空断言失败: {val} 是空的")

    return val, flag

def node_index(node, env) -> tuple: # if node['type'] == 'index':
    obj, _ = runtoken(node['obj'], env)
    index, _ = runtoken(node['index'], env)

    # 检查是否是 KeiInstance 且有 __getitem__ 方法
    if isinstance(obj, KeiInstance):
        # 直接从类的方法表拿，不触发 __getitem__
        method_info = obj._class._methods_map.get('__getitem__')
        if method_info:
            # 绑定实例并调用
            method = KeiMethod(method_info, obj._class)
            bound = method.bind(obj)
            return bound(index), False

    if isinstance(obj, KeiBase):
        if isinstance(index, KeiInt):
            result = obj[index.value]
        else:
            result = obj[index]
    elif isinstance(obj, (list, dict, str)):
        if get_from_env("__compat_mode__", env):
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

def node_trysingle(node, env) -> tuple: # if node['type'] == 'trysingle':
    try:
        __kei__.catch.append(True)
        val, flag = runtoken(node['expr'], env)
        return val, flag
    except:
        return null, False
    finally:
        __kei__.catch.pop()

def node_slice(node, env) -> tuple: # if node['type'] == 'slice':
    obj, _ = runtoken(node['obj'], env)

    start = None
    end = None
    step = 1

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

    if hasattr(obj, '__getitem__'):
        py_slice = slice(start, end, step)
        return obj[py_slice], False

def node_attr(node, env) -> tuple: # if node['type'] == 'attr':
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

def node_postfix(node, env) -> tuple: # if node['type'] == 'postfix':
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

            if isinstance(val, KeiInt):
                return KeiInt(new_val), flag
            else:
                return KeiFloat(new_val), flag
        else:
            raise KeiError("TypeError", f"无法对 {type(val)} 进行 -- 运算")

def node_compoundassign(node, env) -> tuple: # if node['type'] == 'compoundassign':
    def compoundassign():
        try:
            right_val, flag = runtoken(node['right'], env)
            left = node['left']
            op = node['op']

            if left['type'] == 'multiassign':
                vars_list = left['vars']
                rest_var = left.get('rest')
                kwargs_var = left.get('kwargs')

                if isinstance(right_val, KeiList):
                    right_items = right_val.items
                elif isinstance(right_val, (list, tuple)):
                    right_items = list(right_val)
                else:
                    right_items = [right_val]

                new_values = []
                for i, var in enumerate(vars_list):
                    if var == '_':
                        continue
                    current = env.get(var, undefined)

                    if op == '+=':
                        new_val = current.__add__(right_items[i] if i < len(right_items) else undefined)
                    elif op == '-=':
                        new_val = current.__sub__(right_items[i] if i < len(right_items) else undefined)
                    elif op == '*=':
                        new_val = current.__mul__(right_items[i] if i < len(right_items) else undefined)
                    elif op == '/=':
                        r = right_items[i] if i < len(right_items) else undefined
                        if r == 0:
                            raise KeiError("ZeroDivisionError", "除数不能为零")
                        new_val = current.__truediv__(r)
                    else:
                        raise KeiError("SyntaxError", f"不支持的操作符: {op}")

                    env[var] = new_val
                    new_values.append(new_val)

                if rest_var:
                    rest_items = right_items[len(vars_list):]
                    current = env.get(rest_var, KeiList([]))

                    if op == '+=':
                        if isinstance(current, KeiList):
                            new_val = KeiList(current.items + rest_items)
                        else:
                            new_val = KeiList([current] + rest_items)
                    elif op == '-=':
                        if isinstance(current, KeiList):
                            new_items = [x for x in current.items if x not in rest_items]
                        else:
                            new_items = [current] if current not in rest_items else []
                        new_val = KeiList(new_items)
                    elif op == '*=':
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

                if kwargs_var:
                    current = env.get(kwargs_var, KeiDict({}))

                    if isinstance(right_val, KeiDict):
                        right_dict = right_val.items
                    elif isinstance(right_val, dict):
                        right_dict = right_val
                    else:
                        raise KeiError("TypeError", f"**kwargs 赋值右边必须是字典，得到 {type(right_val)}")

                    if op == '+=':
                        if isinstance(current, KeiDict):
                            new_dict = current.items.copy()
                        elif isinstance(current, dict):
                            new_dict = current.copy()
                        else:
                            new_dict = {}
                        new_dict.update(right_dict)
                        new_val = KeiDict(new_dict)
                    elif op == '-=':
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
                        raise KeiError("TypeError", f"字典不支持 *= 操作")
                    elif op == '/=':
                        raise KeiError("TypeError", f"字典不支持 /= 操作")
                    else:
                        raise KeiError("TypeError", f"**kwargs 变量不支持 {op} 操作")

                    env[kwargs_var] = new_val

                return KeiList(new_values), flag

            elif left['type'] == 'name':
                name = left['value']
                current = env.get(name, undefined)

                if op == '+=':
                    new_val = current.__add__(right_val)
                elif op == '-=':
                    new_val = current.__sub__(right_val)
                elif op == '*=':
                    new_val = current.__mul__(right_val)
                elif op == '/=':
                    if right_val == 0:
                        raise KeiError("ZeroDivisionError", "除数不能为零")
                    new_val = current.__truediv__(right_val)
                else:
                    raise KeiError("SyntaxError", f"不支持的操作符: {op}")

                env[name] = new_val
                return new_val, flag

            elif left['type'] == 'attr':
                obj, _ = runtoken(left['obj'], env)
                attr = left['attr']

                if isinstance(obj, KeiBase):
                    current = obj[attr]
                elif isinstance(obj, dict):
                    current = obj.get(attr, undefined)
                else:
                    current = getattr(obj, attr, undefined)

                if op == '+=':
                    new_val = current.__add__(right_val)
                elif op == '-=':
                    new_val = current.__sub__(right_val)
                elif op == '*=':
                    new_val = current.__mul__(right_val)
                elif op == '/=':
                    if right_val == 0:
                        raise KeiError("ZeroDivisionError", "除数不能为零")
                    new_val = current.__truediv__(right_val)
                else:
                    raise KeiError("SyntaxError", f"不支持的操作符: {op}")

                if isinstance(obj, KeiBase):
                    obj[attr] = new_val
                elif isinstance(obj, dict):
                    obj[attr] = new_val
                else:
                    setattr(obj, attr, new_val)

                return new_val, flag

            elif left['type'] == 'index':
                obj, _ = runtoken(left['obj'], env)
                index, _ = runtoken(left['index'], env)

                current = obj[index]

                if op == '+=':
                    new_val = current.__add__(right_val)
                elif op == '-=':
                    new_val = current.__sub__(right_val)
                elif op == '*=':
                    new_val = current.__mul__(right_val)
                elif op == '/=':
                    if right_val == 0:
                        raise KeiError("ZeroDivisionError", "除数不能为零")
                    new_val = current.__truediv__(right_val)
                else:
                    raise KeiError("SyntaxError", f"不支持的操作符: {op}")

                obj[index] = new_val
                return new_val, flag

            elif left['type'] in ('star_target', 'starassign'):
                name = left['name']
                current = env.get(name, undefined)

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

            elif left['type'] in ('starstar_target', 'starstarassign'):
                name = left['name']
                current = env.get(name, undefined)

                if not isinstance(right_val, (KeiDict, dict)):
                    raise KeiError("TypeError", f"** 赋值右边必须是字典，得到 {type(right_val)}")

                if op == '+=':
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

        except AttributeError:
            raise KeiError("TypeError", f"{runtoken(left, env)[0]} 和 {right_val} 无法 {op} 运算")
        except TypeError:
            raise KeiError("TypeError", f"{runtoken(left, env)[0]} 和 {right_val} 无法 {op} 运算")

    return compoundassign()

def node_ternary(node, env) -> tuple: # if node['type'] == 'ternary':
    cond_val, cond_flag = runtoken(node['cond'], env)
    if cond_flag:
        return cond_val, True

    if cond_val:
        return runtoken(node['true_val'], env)
    else:
        return runtoken(node['false_val'], env)

def node_unternary(node, env) -> tuple: # if node['type'] == 'unternary':
    cond_val, cond_flag = runtoken(node['cond'], env)
    if cond_flag:
        return cond_val, True

    if not cond_val:
        return runtoken(node['true_val'], env)
    else:
        return runtoken(node['false_val'], env)

def node_listcomp(node, env) -> tuple: # if node['type'] in {'listcomp', 'unlistcomp'}:
    un = True if node['type'] == "unlistcomp" else False
    result = []
    iterable_val, _ = runtoken(node['iterable'], env)
    vars_list = node['vars']
    expr_node = node['expr']
    cond = node.get('cond')

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

    for item in items:
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

        if cond:
            cond_val, _ = runtoken(cond, env)
            if un:
                if cond_val:
                    continue
            else:
                if not cond_val:
                    continue

        if isinstance(expr_node, list):
            for sub_expr in expr_node:
                val, _ = runtoken(sub_expr, env)
                result.append(val)
        else:
            val, _ = runtoken(expr_node, env)
            result.append(val)

    return KeiList(result), False

def node_dictcomp(node, env) -> tuple: # if node['type'] in {'dictcomp', 'undictcomp'}:
    un = True if node['type'] == "undictcomp" else False
    result = {}
    iterable_val, _ = runtoken(node['iterable'], env)
    vars_list = node['vars']
    pairs = node['pairs']
    cond = node.get('cond')

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

    for item in items:
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

        if cond:
            cond_val, _ = runtoken(cond, env)
            if un:
                if cond_val:
                    continue
            else:
                if not cond_val:
                    continue

        for pair in pairs:
            key, _ = runtoken(pair['key'], env)
            val, _ = runtoken(pair['value'], env)

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

def node_binop(node, env) -> tuple: # if node['type'] == 'binop':
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
                left, l_flag = runtoken(node['left'], env)
                right, r_flag = runtoken(node['right'], env)

                if isinstance(right, KeiClass):
                    if isinstance(left, KeiInstance):
                        result = true if left._class == right else false
                    elif isinstance(left, KeiClass):
                        result = true if left == right else false
                    else:
                        result = false

                elif isinstance(left, type) and isinstance(right, type):
                    # 都是类型，检查派生关系
                    if issubclass(left, right):
                        result = true
                    else:
                        result = false

                elif isinstance(right, type) and issubclass(right, KeiBase):
                    if isinstance(left, type) and issubclass(left, KeiBase):
                        result = true if left == right else false
                    elif isinstance(left, KeiBase):
                        result = true if isinstance(left, right) else false
                    else:
                        result = false

                elif right == KeiFloat and isinstance(left, KeiInt):
                    result = true

                else:
                    result = true if left is right else false

                return result, (l_flag or r_flag)

            elif op == 'in':
                if isinstance(right, KeiList):
                    found = false
                    for item in right.items:
                        if left == item:
                            found = true
                            break
                    result = found

                elif isinstance(right, KeiDict):
                    key = left.value if hasattr(left, 'value') else left
                    result = true if key in right.items else false

                elif isinstance(right, KeiString):
                    val = left.value if hasattr(left, 'value') else str(left)
                    result = true if val in right.value else false

                elif hasattr(right, '__contains__'):
                    result = right.__contains__(left)

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

def node_unary(node, env) -> tuple: # if node['type'] == 'unary':
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

def node_listscope(node, env) -> tuple: # if node['type'] == 'listscope':
    start_val, _ = runtoken(node['start'], env)
    end_val, _ = runtoken(node['end'], env)

    start = start_val.value if isinstance(start_val, KeiInt) else int(start_val)
    end = end_val.value if isinstance(end_val, KeiInt) else int(end_val)

    result = []
    if start <= end:
        current = start
        while current <= end:
            result.append(KeiInt(current))
            current += 1
    else:
        current = start
        while current >= end:
            result.append(KeiInt(current))
            current -= 1

    return KeiList(result), False

def node_call(node, env) -> tuple: # if node['type'] in {'call', 'methodcall'}:
    args = []
    kwargs = {}

    call_source = node.get('source')
    if call_source is None:
        call_source = globals().get('source', '')

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

    if node['type'] == 'call':
        name = node['name']
        stdlib.kei.setenv(env)

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
                    result = method(linecode=call_source, name=get_from_env('__caller__', env, '<global>'), *args, **kwargs)
                else:
                    result = method(*args, **kwargs)
                return result, False
            raise KeiError("NameError", f"对象没有方法 {method_name}")

        func_obj = get_from_env(name, env)

        if func_obj is not undefined:
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
                return func_obj(linecode=call_source, name=get_from_env('__caller__', env, '<global>'), *args, **kwargs), False

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

    else:
        obj = None
        method_name = None

        if 'obj' in node:
            obj, _ = runtoken(node['obj'], env)
            method_name = node.get('method')

        if obj is None:
            raise KeiError("NameError", "对象未定义")
        if method_name is None:
            if callable(obj):
                if isinstance(obj, KeiFunction):
                    result = obj(linecode=call_source, name=get_from_env('__caller__', env, '<global>'), *args, **kwargs)
                else:
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
                    if isinstance(method, KeiFunction):
                        result = method(linecode=call_source, name=get_from_env('__caller__', env, '<global>'), *args, **kwargs)
                    else:
                        result = method(*args, **kwargs)
                elif starstar_param:
                    if isinstance(method, KeiFunction):
                        result = method(linecode=call_source, name=get_from_env('__caller__', env, '<global>'), *args, **kwargs)
                    else:
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
                    if isinstance(method, KeiFunction):
                        result = method(linecode=call_source, name=get_from_env('__caller__', env, '<global>'), *call_args)
                    else:
                        result = method(*call_args)
                return result, False

            is_bound = isinstance(method, KeiBoundMethod) or hasattr(method, '__self__')

            if is_bound:
                if star_param:
                    if isinstance(method, KeiFunction):
                        result = method(linecode=call_source, name=get_from_env('__caller__', env, '<global>'), *args, **kwargs)
                    else:
                        result = method(*args, **kwargs)
                elif starstar_param:
                    if isinstance(method, KeiFunction):
                        result = method(linecode=call_source, name=get_from_env('__caller__', env, '<global>'), *args, **kwargs)
                    else:
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
                    if isinstance(method, KeiFunction):
                        result = method(linecode=call_source, name=get_from_env('__caller__', env, '<global>'), *call_args)
                    else:
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
                if isinstance(method, KeiFunction):
                    result = method(linecode=call_source, name=get_from_env('__caller__', env, '<global>'), *call_args)
                else:
                    result = method(*call_args)

            return result, False

        if callable(method):
            if isinstance(method, KeiFunction):
                result = method(linecode=call_source, name=get_from_env('__caller__', env, '<global>'), *args, **kwargs)
            else:
                result = method(*args, **kwargs)
            return result, False

        if isinstance(method, KeiFunction):
            result = method(linecode=call_source, name=get_from_env('__caller__', env, '<global>'), *args, **kwargs)
        else:
            result = method(*args, **kwargs)
        return result, False

def node_assign(node, env) -> tuple: # if node['type'] == 'assign':
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
                    env[var] = undefined
            return val, flag

    elif left['type'] == 'star_target' or left['type'] == 'starassign':
        name = left['name']
        if isinstance(val, KeiList):
            env[name] = val
        elif isinstance(val, (list, tuple)):
            env[name] = KeiList(list(val))
        else:
            env[name] = KeiList([val])
        return val, flag

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
            if name in get_from_env('__globals__', env, []):
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

        if isinstance(start, KeiInt):
            start = start.value
        if isinstance(end, KeiInt):
            end = end.value
        if isinstance(step, KeiInt):
            step = step.value

        if isinstance(obj, KeiString):
            length = len(obj.value)
            if start is not None and start < 0:
                start = length + start
            if end is not None and end < 0:
                end = length + end

            if isinstance(val, KeiString):
                new_str = val.value
            else:
                new_str = str(val)

            if start is None:
                start = 0
            if end is None:
                end = length

            obj.value = obj.value[:start] + new_str + obj.value[end:]

        elif isinstance(obj, KeiList):
            if start is None:
                start = 0
            if end is None:
                end = len(obj.items)

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

def node_return(node, env) -> tuple: # if node['type'] == 'return':
    if node['value'] is None:
        return None, True
    val, flag = runtoken(node['value'], env)
    return val, True

def node_if(node, env) -> tuple: # if node['type'] in {'if', 'unless'}:
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

def node_while(node, env) -> tuple: # if node['type'] in {'while', 'until'}:
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

def node_for(node, env) -> tuple: # if node['type'] == 'for':
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

def node_break(node, env) -> tuple: # if node['type'] in {'break', 'continue'}:
    return (node['type'], None), True

def node_block(node, env) -> tuple: # if node['type'] == 'function':
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
        'typeassert': node.get('hint', None),
        'typehints': node.get('typehints', {})
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

def node_class(node, env) -> tuple: # if node['type'] == 'class':
    class_obj = {
        'type': 'class',
        'name': node['name'],
        'parent': node.get('parent'),
        'body': node['body'],
        'methods': [],
        'attrs': {},
        'methods_map': {}
    }

    if class_obj['parent']:
        parent = env.get(class_obj['parent'])
        if parent is None or parent is undefined:
            raise KeiError("NameError", f"父类 '{class_obj['parent']}' 未定义")
        if not isinstance(parent, KeiClass):
            raise KeiError("TypeError", f"'{class_obj['parent']}' 不是类")
        class_obj['attrs'] = parent._class_attrs.copy()
        class_obj['methods_map'] = parent.class_obj['methods_map'].copy()

    for stmt in node['body']:
        if stmt['type'] == 'function':
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
            if 'decorators' in stmt:
                for dec in stmt['decorators']:
                    if dec['value'] == 'prop':
                        method_obj['is_property'] = True

            class_obj['methods'].append(method_obj)
            class_obj['methods_map'][stmt['name']] = method_obj

        elif stmt['type'] == 'assign':
            if stmt['left']['type'] == 'name':
                attr_name = stmt['left']['value']
                attr_val, _ = runtoken(stmt['right'], env)
                class_obj['attrs'][attr_name] = attr_val

    kei_class = KeiClass(class_obj, env)
    env[node['name']] = kei_class
    return None, False

def _get_exported_dict(module_env, module_dict):
    """从模块环境中构建导出字典（统一规则）"""
    # 获取 __all__
    all_names = None
    if '__all__' in module_env:
        all_val = module_env['__all__']
        if isinstance(all_val, KeiList):
            all_names = [item.value if isinstance(item, KeiString) else str(item) for item in all_val.items]
        elif isinstance(all_val, list):
            all_names = [str(item) for item in all_val]
        elif isinstance(all_val, KeiString):
            all_names = [all_val.value]
        elif isinstance(all_val, str):
            all_names = [all_val]

    # 构建模块字典（包含所有非私有和 __all__ 指定的）
    for k, v in module_env.items():
        if not k.startswith('__'):
            module_dict[k] = v
        elif k == '__all__':
            module_dict['__all__'] = v
        elif all_names is not None and k in all_names:
            # 即使以 __ 开头，只要在 __all__ 里就加入
            module_dict[k] = v

    # 构建导出字典
    if all_names is not None:
        # __all__ 最高优先级：只导出 __all__ 中存在的
        exported_dict = {}
        for name in all_names:
            if name in module_dict:
                exported_dict[name] = module_dict[name]
            elif name in module_env:
                exported_dict[name] = module_env[name]
    else:
        # 没有 __all__：导出所有非 _ 开头的
        exported_dict = {k: v for k, v in module_dict.items() if not k.startswith('_')}

    return exported_dict

def node_import(node, env) -> tuple:
    try:
        for module_info in node['modules']:
            full_module_name = module_info['module']
            alias = module_info.get('alias')
            is_wildcard = module_info.get('type') == 'wildcard'

            assert isinstance(get_from_env("__path__", env, KeiList([])), KeiList), "__path__需要是一个列表"

            __path__ = get_from_env("__path__", env, KeiList([])).items

            full_module_name = full_module_name.replace('.', '/')

            module_name = full_module_name.split("/")[-1]

            kei_files = [os.path.join(path, f"{full_module_name}.kei") for path in __path__]

            for keifile in kei_files:
                if os.path.isfile(keifile):
                    with open(keifile, "r", encoding="utf-8") as f:
                        code = f.read()

                    module_env = {
                        "__path__": KeiList(["."] + paths),
                        "__name__": KeiString(f"__{module_name}__"),
                        "__env__": KeiDict(env),
                        "__osname__": KeiString(platform.system().lower()),
                    }

                    module_env.update({
                        "__env__": module_env,
                    })

                    exec(code, module_env)

                    module_dict = {}
                    exported_dict = _get_exported_dict(module_env, module_dict)

                    if is_wildcard:
                        for name, value in exported_dict.items():
                            env[name] = value
                    else:
                        name = alias or module_name
                        env[name] = KeiNamespace(name, exported_dict)

                    return None, False

            py_files = [os.path.join(path, f"{full_module_name}.py") for path in __path__]

            for pyfile in py_files:
                if os.path.isfile(pyfile):
                    with open(pyfile, "r", encoding="utf-8") as f:
                        code = f.read()

                    module_env = {}
                    __py_exec__(code, module_env)

                    module_dict = {}
                    exported_dict = _get_exported_dict(module_env, module_dict)

                    if is_wildcard:
                        for name, value in exported_dict.items():
                            env[name] = value
                    else:
                        name = alias or full_module_name
                        env[name] = KeiNamespace(name, exported_dict)

                    return None, False

            raise KeiError("ImportError", f"找不到模块: {full_module_name}")

        return None, False

    except Exception as e:
        raise KeiError("ImportError", f"导入模块失败: {e}")

def node_fromimport(node, env) -> tuple:
    module_name = node['module']
    imports = node['imports']

    assert isinstance(get_from_env("__path__", env, KeiList([])), KeiList), "__path__需要是一个列表"

    __path__ = get_from_env("__path__", env, KeiList([])).items

    module_path = module_name.replace('.', '/')
    module_short_name = module_path.split("/")[-1]

    module_env = None

    kei_files = [os.path.join(path, f"{module_path}.kei") for path in __path__]

    for keifile in kei_files:
        if os.path.isfile(keifile):
            with open(keifile, "r", encoding="utf-8") as f:
                code = f.read()

            module_env = {
                "__path__": KeiList(["."] + paths),
                "__name__": KeiString(f"__{module_short_name}__"),
                "__env__": KeiDict(env),
                "__osname__": KeiString(platform.system().lower()),
            }

            module_env.update({
                "__env__": module_env,
            })

            exec(code, module_env)
            break

    if module_env is None:
        py_files = [os.path.join(path, f"{module_path}.py") for path in __path__]

        for pyfile in py_files:
            if os.path.isfile(pyfile):
                with open(pyfile, "r", encoding="utf-8") as f:
                    code = f.read()

                module_env = {}
                __py_exec__(code, module_env)
                break

    if module_env is None:
        raise KeiError("ImportError", f"找不到模块: {module_name}")

    module_dict = {}
    exported_dict = _get_exported_dict(module_env, module_dict)

    for imp in imports:
        if imp['type'] == 'wildcard':
            for name, value in exported_dict.items():
                env[name] = value
        else:
            name = imp['name']
            alias = imp['alias'] or name

            # 显式导入：优先从 module_dict，再从 module_env
            if name in module_dict:
                env[alias] = module_dict[name]
            elif name in module_env:
                env[alias] = module_env[name]
            else:
                raise KeiError("ImportError", f"无法从 {module_name} 导入 {name}")

    return None, False

def node_del(node, env) -> tuple: # if node['type'] == 'del':
    for target in node['names']:
        if target['type'] == 'name':
            name = target['value']
            if name in env:
                del env[name]
        elif target['type'] == 'index':
            obj, _ = runtoken(target['obj'], env)
            index, _ = runtoken(target['index'], env)
            if isinstance(obj, KeiList):
                idx = index.value if isinstance(index, KeiInt) else int(index)
                if 0 <= idx < len(obj.items):
                    del obj.items[idx]
        elif target['type'] == 'attr':
            obj, _ = runtoken(target['obj'], env)
            attr = target['attr']
            if isinstance(obj, KeiBase):
                if attr in obj._props:
                    del obj._props[attr]

    return None, False

def node_raise(node, env) -> tuple: # if node['type'] == 'raise':
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
        if get_from_env("__error__", env, None) is not None:
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

def node_use(node, env) -> tuple: # if node['type'] == 'use':
    for target in node['names']:
        # 计算表达式（不再是简单的名字）
        ns, _ = runtoken(target, env)
        if isinstance(ns, KeiNamespace):
            env.update(ns.env)  # 导入成员
        else:
            raise KeiError("TypeError", f"use 需要 namespace，得到 {type(ns)}")
    return None, False

def node_namespace(node, env) -> tuple: # if node['type'] == 'namespace':
    ns_data = {}
    ns_env = NamespaceEnv(env, ns_data)

    for stmt in node['body']:
        runtoken(stmt, ns_env)

    ns = env.copy()
    ns[node['name']] = ns_data

    env[node['name']] = KeiNamespace(node['name'], ns, True)
    return None, False

def node_with(node, env) -> tuple: # if node['type'] == 'with':
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

def node_lambda(node, env) -> tuple: # if node['type'] == 'lambda':
    func_obj = {
        'type': 'user_function',
        'name': None,
        'params': node['params'],
        'defaults': {},
        'body': [{'type': 'return', 'value': node['body']}],
        'globals': [],
        'closure': env,
    }
    return KeiFunction(func_obj, env), False

def node_try(node, env) -> tuple: # if node['type'] == 'try':
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
            linenum = globals()['linenum']
            source  = globals()['source']

            if node['finallybody']:
                for f_stmt in node['finallybody']:
                    f_val, f_is_return = runtoken(f_stmt, env)
                    if f_is_return:
                        return f_val, True

            globals()['linenum'] = linenum
            globals()['source']  = source

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

def node_global(node, env) -> tuple: # if node['type'] == 'global':
    for name_node in node['names']:
        var_name = name_node['value']
        if '__globals__' not in env:
            env['__globals__'] = set()
        env['__globals__'].add(var_name)
    return None, False

def node_typeassert(node, env) -> tuple: # if node['type'] == 'typeassert':
    val, flag = runtoken(node['expr'], env)
    hint = runtoken(node['hint'], env)[0]

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

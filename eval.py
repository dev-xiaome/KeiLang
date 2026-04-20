import platform
import inspect
import copy
import sys
import os

import stdlib
from object import *
from kei import __kei__, runtoken, get_from_env, process_fstring, find_method, paths, __py_exec__, exec
from lib.python import tokei, topy

def _get_exported_dict(module_env, module_dict):
    """从模块环境中构建导出字典（统一规则）"""
    # 特殊允许的私有变量
    ALLOWED_PRIVATE = {'__import__', '__all__'}

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

    # 构建模块字典（所有变量，包括私有）
    for k, v in module_env.items.items():
        module_dict[k] = v

    # 构建导出字典
    exported_dict = KeiDict({})

    if all_names is not None:
        # 有 __all__：导入 __all__ 里的（即使是 _ 开头）
        for name in all_names:
            if name in module_dict:
                exported_dict[name] = module_dict[name]
            elif name in module_env:
                exported_dict[name] = module_env[name]

        # 额外导入 ALLOWED_PRIVATE 里的（只要存在）
        for name in ALLOWED_PRIVATE:
            if name in module_dict:
                exported_dict[name] = module_dict[name]
            elif name in module_env:
                exported_dict[name] = module_env[name]
    else:
        # 没有 __all__：导出非 _ 开头的 + ALLOWED_PRIVATE
        for k, v in module_dict.items():
            if not k.startswith('_') or k in ALLOWED_PRIVATE:
                exported_dict[k] = v

    return exported_dict

def _load_kei_module(module_path, module_name, env, __path__):
    """加载 .kei 模块，返回模块字典和是否成功"""

    try:
        oldfilename = __kei__.file

        kei_files = [os.path.join(path, f"{module_path}.kei") for path in __path__]

        for keifile in kei_files:
            if os.path.isfile(keifile):
                __kei__.file = os.path.abspath(keifile)

                with open(keifile, "r", encoding="utf-8") as f:
                    code = f.read()

                module_env = KeiDict({
                    "__path__": KeiList(["."] + paths),
                    "__name__": KeiString(f"__{module_name}__"),
                    "__env__": KeiDict(env),
                    "__osname__": KeiString(platform.system().lower()),
                    "__file__": KeiString(os.path.abspath(__kei__.file))
                })
                module_env["__env__"] = module_env

                exec(code, module_env)

                # 获取导出字典
                module_dict = KeiDict({})
                exported_dict = _get_exported_dict(module_env, module_dict)

                return exported_dict, module_env, True
    finally:
        __kei__.file = oldfilename

    return None, None, False

def _load_py_module(module_path, __path__):
    """加载 .py 模块，返回模块环境"""
    py_files = [os.path.join(path, f"{module_path}.py") for path in __path__]

    for pyfile in py_files:
        if os.path.isfile(pyfile):
            with open(pyfile, "r", encoding="utf-8") as f:
                code = f.read()

            module_env = {}.copy()
            __py_exec__(code, module_env)
            return KeiDict(module_env), True

    return None, False

def _call_import_hook(exported_dict):
    """如果模块有 __import__ 函数，执行它"""
    if "__import__" in exported_dict:
        importfunc = exported_dict.get("__import__")
        if callable(importfunc):
            importfunc()

def unwrap_prop(obj):
    """递归展开 prop，直到不是 prop 为止"""
    while True:
        # 安全获取 is_property 属性
        is_prop = getattr(obj, 'is_property', False)
        if not is_prop or not callable(obj):
            break
        obj = obj()
    return obj

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
                try:
                    result = process_fstring(node['value'], env)
                except:
                    raise

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
        captured_vars = {}  # 存储捕获的变量

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

            # ========== 新增：字典模式 ==========
            elif pattern_node['type'] == 'dict_pattern':
                # 检查 value 是否是字典
                if not isinstance(value, KeiDict):
                    continue

                matched = True
                items = pattern_node['items']

                for item in items:
                    key_node = item['key']
                    key_val, _ = runtoken(key_node, env)

                    # 检查键是否存在
                    if key_val not in value.items:
                        matched = False
                        break

                    if item['type'] == 'capture':
                        # 捕获变量：rights -> value["rights"]
                        captured_vars[item['name']] = value.items[key_val]
                    else:  # literal
                        # 字面量匹配：type == "admin"
                        pattern_val, _ = runtoken(item['value'], env)
                        if not value.items[key_val].__eq__(pattern_val):
                            matched = False
                            break

                if matched:
                    # 将捕获的变量注入环境
                    for var_name, var_val in captured_vars.items():
                        env[var_name] = var_val
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

    # 关键：统一向上查找
    obj = get_from_env(name_value, env)
    obj = unwrap_prop(obj)

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
        raise KeiError("TypeError", f"非空断言失败: {node['expr']['value'] if node['expr'].get("value", None) is not None else val} 是空的")

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

    return None, False

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

def node_postfix(node, env) -> tuple:
    val, flag = runtoken(node['expr'], env)
    if flag:
        return val, True

    if node['op'] == '++':
        if isinstance(val, (KeiInt, KeiFloat)):
            new_val = val.value + 1

            if node['expr']['type'] == 'name':
                var_name = node['expr']['value']

                # 沿着环境链向上查找变量
                target_env = env
                found = False
                while target_env is not None:
                    if var_name in target_env:
                        found = True
                        break
                    target_env = target_env.get('__parent__')

                # 如果没找到，就在当前环境创建
                if not found:
                    target_env = env

                # 赋值
                if isinstance(val, KeiInt):
                    target_env[var_name] = KeiInt(new_val)
                else:
                    target_env[var_name] = KeiFloat(new_val)

            elif node['expr']['type'] == 'attr':
                obj, _ = runtoken(node['expr']['obj'], env)
                attr = node['expr']['attr']

                # 处理属性赋值
                if isinstance(obj, KeiBase):
                    if isinstance(val, KeiInt):
                        obj[attr] = KeiInt(new_val)
                    else:
                        obj[attr] = KeiFloat(new_val)
                elif isinstance(obj, dict):
                    obj[attr] = new_val
                else:
                    setattr(obj, attr, new_val)

            # 返回值
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
                var_name = node['expr']['value']

                # 沿着环境链向上查找变量
                target_env = env
                found = False
                while target_env is not None:
                    if var_name in target_env:
                        found = True
                        break
                    target_env = target_env.get('__parent__')

                # 如果没找到，就在当前环境创建
                if not found:
                    target_env = env

                # 赋值
                if isinstance(val, KeiInt):
                    target_env[var_name] = KeiInt(new_val)
                else:
                    target_env[var_name] = KeiFloat(new_val)

            elif node['expr']['type'] == 'attr':
                obj, _ = runtoken(node['expr']['obj'], env)
                attr = node['expr']['attr']

                # 处理属性赋值
                if isinstance(obj, KeiBase):
                    if isinstance(val, KeiInt):
                        obj[attr] = KeiInt(new_val)
                    else:
                        obj[attr] = KeiFloat(new_val)
                elif isinstance(obj, dict):
                    obj[attr] = new_val
                else:
                    setattr(obj, attr, new_val)

            # 返回值
            if isinstance(val, KeiInt):
                return KeiInt(new_val), flag
            else:
                return KeiFloat(new_val), flag
        else:
            raise KeiError("TypeError", f"无法对 {type(val)} 进行 -- 运算")

    return None, False

def node_compoundassign(node, env) -> tuple:
    """复合赋值 += -= *= /= """
    left = node['left']
    right_node = node['right']
    op = node['op']

    # 先计算右边的值
    right_val, _ = runtoken(right_node, env)

    # ========== 多变量复合赋值 ==========
    if left['type'] == 'multiassign':
        vars_list = left['vars']
        rest_var = left.get('rest')
        kwargs_var = left.get('kwargs')

        if kwargs_var:
            raise KeiError("TypeError", "**kwargs 不支持复合赋值")

        current_vals = []
        for var_info in vars_list:
            if isinstance(var_info, dict):
                var_name = var_info['name']
            else:
                var_name = var_info

            # 沿环境链查找
            target_env = env
            found = False
            while target_env is not None:
                if var_name in target_env:
                    found = True
                    break
                target_env = target_env.get('__parent__')
            if found:
                current_vals.append(target_env.get(var_name, undefined))
            else:
                current_vals.append(undefined)

        if isinstance(right_val, KeiList):
            right_items = right_val.items
        elif isinstance(right_val, (list, tuple)):
            right_items = list(right_val)
        else:
            right_items = [right_val]

        result_vals = []
        for i, current in enumerate(current_vals):
            if i < len(right_items):
                r = right_items[i]
            else:
                r = right_items[-1] if right_items else undefined

            if op == '+=':
                result = current + r
            elif op == '-=':
                result = current - r
            elif op == '*=':
                result = current * r
            elif op == '/=':
                result = current / r
            else:
                raise KeiError("TypeError", f"不支持的复合运算符: {op}")
            result_vals.append(result)

        if rest_var:
            rest_items = right_items[len(vars_list):]
            env[rest_var] = KeiList(rest_items)

        for i, var_info in enumerate(vars_list):
            if isinstance(var_info, dict):
                var_name = var_info['name']
                var_hint = var_info.get('hint')
            else:
                var_name = var_info
                var_hint = None

            if var_name == '_':
                continue

            val = result_vals[i] if i < len(result_vals) else undefined

            if var_hint is not None:
                val, _ = node_typeassert_typecheck(val, var_hint, env)

            # 沿环境链查找并赋值
            target_env = env
            found = False
            while target_env is not None:
                if var_name in target_env:
                    found = True
                    break
                target_env = target_env.get('__parent__')
            if not found:
                target_env = env
            target_env[var_name] = val

        return result_vals[0] if result_vals else undefined, False

    # ========== 普通变量 name ==========
    elif left['type'] == 'name':
        var_name = left['value']
        var_hint = left.get('hint')

        # 沿环境链查找
        target_env = env
        found = False
        while target_env is not None:
            if var_name in target_env:
                found = True
                break
            target_env = target_env.get('__parent__')
        if not found:
            target_env = env

        current_val = target_env.get(var_name, undefined)

        if op == '+=':
            result = current_val + right_val
        elif op == '-=':
            result = current_val - right_val
        elif op == '*=':
            result = current_val * right_val
        elif op == '/=':
            result = current_val / right_val
        else:
            raise KeiError("TypeError", f"不支持的复合运算符: {op}")

        if var_hint is not None:
            result, _ = node_typeassert_typecheck(result, var_hint, env)

        target_env[var_name] = result
        return result, False

    # ========== 索引赋值 ==========
    elif left['type'] == 'index':
        obj, _ = runtoken(left['obj'], env)
        index, _ = runtoken(left['index'], env)

        if isinstance(obj, KeiList):
            idx = index.value if isinstance(index, KeiInt) else index
            current_val = obj.items[idx]
        elif isinstance(obj, KeiDict):
            current_val = obj.get(index, undefined)
        else:
            raise KeiError("TypeError", f"不支持对 {type(obj)} 进行索引复合赋值")

        if op == '+=':
            result = current_val + right_val
        elif op == '-=':
            result = current_val - right_val
        elif op == '*=':
            result = current_val * right_val
        elif op == '/=':
            result = current_val / right_val
        else:
            raise KeiError("TypeError", f"不支持的复合运算符: {op}")

        if isinstance(obj, KeiList):
            obj.items[idx] = result
        elif isinstance(obj, KeiDict):
            obj[index] = result
        else:
            raise KeiError("TypeError", f"不支持对 {type(obj)} 进行索引复合赋值")

        return result, False

    # ========== 属性赋值 ==========
    elif left['type'] == 'attr':
        obj, _ = runtoken(left['obj'], env)
        attr = left['attr']

        if isinstance(obj, KeiBase):
            try:
                current_val = obj[attr]
            except (KeyError, AttributeError, TypeError):
                current_val = undefined
        elif isinstance(obj, dict):
            current_val = obj.get(attr, undefined)
        else:
            current_val = getattr(obj, attr, undefined)

        if op == '+=':
            result = current_val + right_val
        elif op == '-=':
            result = current_val - right_val
        elif op == '*=':
            result = current_val * right_val
        elif op == '/=':
            result = current_val / right_val
        else:
            raise KeiError("TypeError", f"不支持的复合运算符: {op}")

        if isinstance(obj, KeiBase):
            obj[attr] = result
        elif isinstance(obj, dict):
            obj[attr] = result
        else:
            setattr(obj, attr, result)

        return result, False

    # ========== 切片赋值 ==========
    elif left['type'] == 'slice':
        obj, _ = runtoken(left['obj'], env)
        start_node = left.get('start')
        end_node = left.get('end')
        step_node = left.get('step')

        start = runtoken(start_node, env)[0] if start_node else None
        end = runtoken(end_node, env)[0] if end_node else None
        step = runtoken(step_node, env)[0] if step_node else None

        if isinstance(start, KeiInt):
            start = start.value
        if isinstance(end, KeiInt):
            end = end.value
        if isinstance(step, KeiInt):
            step = step.value

        if isinstance(obj, KeiList):
            length = len(obj.items)
            if start is None:
                start = 0
            if end is None:
                end = length
            if start < 0:
                start = length + start
            if end < 0:
                end = length + end

            current_slice = obj.items[start:end:step]

            if isinstance(right_val, KeiList):
                for i, idx in enumerate(range(start, end, step or 1)):
                    if i < len(right_val.items):
                        if op == '+=':
                            obj.items[idx] = current_slice[i] + right_val.items[i]
                        elif op == '-=':
                            obj.items[idx] = current_slice[i] - right_val.items[i]
                        elif op == '*=':
                            obj.items[idx] = current_slice[i] * right_val.items[i]
                        elif op == '/=':
                            obj.items[idx] = current_slice[i] / right_val.items[i]
            else:
                for idx in range(start, end, step or 1):
                    if op == '+=':
                        obj.items[idx] = obj.items[idx] + right_val
                    elif op == '-=':
                        obj.items[idx] = obj.items[idx] - right_val
                    elif op == '*=':
                        obj.items[idx] = obj.items[idx] * right_val
                    elif op == '/=':
                        obj.items[idx] = obj.items[idx] / right_val

            return obj, False
        else:
            raise KeiError("TypeError", f"不支持对 {type(obj)} 进行切片复合赋值")

    else:
        raise KeiError("TypeError", f"无效的复合赋值目标: {left.get('type')}")

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
                try:
                    result = left.__eq__(right)
                except:
                    result = true if left == right else false
            elif op == '!=':
                try:
                    result = left.__ne__(right)
                except:
                    result = true if left != right else false
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

                result = true if left is right else false

                return result, (l_flag or r_flag)

            elif op == 'isa':
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
            raise KeiError("TypeError", f"{content(left)} 和 {content(right)} 无法 {op} 运算")
        except TypeError:
            raise KeiError("TypeError", f"{content(left)} 和 {content(right)} 无法 {op} 运算")

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

    return None, False

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

        func_obj = get_from_env(name, env)

        if func_obj is not undefined:
            func_obj = unwrap_prop(func_obj)

            if func_obj is stdlib.kei.super:
                if 'self' not in env:
                    raise KeiError("NameError", "super 只能在类方法中使用")
                instance = env['self']
                if not isinstance(instance, KeiInstance):
                    raise KeiError("NameError", "super 需要 self 实例")

                if hasattr(instance, '_parent_instance') and instance._parent_instance is not None:
                    return instance._parent_instance, False

                raise KeiError("TypeError", "此类没有父类")

            if isinstance(func_obj, KeiInstance) and hasattr(func_obj, '__call__'):
                result = func_obj.__call__(*args, **kwargs)
                return result, False

            if isinstance(func_obj, KeiClass):
                instance = func_obj(*args, **kwargs)
                init_method = find_method(func_obj.class_obj, '__init__', env)
                if init_method:
                    new_env = KeiDict({'__parent__': KeiDict(init_method['closure']), 'self': instance})
                    new_env.update({k: v for k, v in init_method['closure'].items() if k != '__parent__'})
                    for i, p in enumerate(init_method['params'][1:]):
                        if i < len(args):
                            new_env[p] = args[i]
                        elif p in kwargs:
                            new_env[p] = kwargs[p]

                return instance, False

            if isinstance(func_obj, KeiFunction):
                return func_obj(linecode=call_source, name=get_from_env('__caller__', env, '<global>'), *args, **kwargs), False

            if isinstance(func_obj, KeiNamespace):
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
        method = unwrap_prop(method)

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

    # 如果有类型注解 hint，先进行类型断言
    if left.get('hint') is not None:
        # 构造一个临时的 typeassert 节点
        typeassert_node = {
            'type': 'typeassert',
            'expr': {'type': 'name', 'value': left['value']},
            'hint': left['hint'],
            'linenum': left.get('linenum', node.get('linenum', 0))
        }
        # 先断言值的类型（注意：这里用 val 而不是从 env 取值）
        # 因为变量还没赋值，需要检查 val 是否符合类型
        val, flag = node_typeassert_typecheck(val, typeassert_node['hint'], env)

    elif left['type'] == 'multiassign':
        vars_list = left['vars']  # 现在是 list of dict: [{'name': 'x', 'hint': node, 'linenum': 1}, ...]
        rest_var = left.get('rest')
        kwargs_var = left.get('kwargs')

        # 获取右边的值
        if isinstance(val, KeiList):
            right_items = val.items
        elif isinstance(val, (list, tuple)):
            right_items = list(val)
        else:
            right_items = [val]

        # 赋值给 vars
        for i, var_info in enumerate(vars_list):
            # var_info 是 dict，不是字符串！
            if isinstance(var_info, dict):
                var_name = var_info['name']
                var_hint = var_info.get('hint')
            else:
                # 兼容旧格式（字符串）
                var_name = var_info
                var_hint = None

            if var_name == '_':
                continue

            if i < len(right_items):
                var_val = right_items[i]
            else:
                var_val = undefined

            # 如果有类型注解，先检查
            if var_hint is not None:
                var_val, _ = node_typeassert_typecheck(var_val, var_hint, env)

            env[var_name] = var_val

        # 处理 *rest
        if rest_var:
            rest_items = right_items[len(vars_list):]
            env[rest_var] = KeiList(rest_items)

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
        var_name = left['value']
        nonlocal_list = get_from_env('__nonlocal__', env, [])

        # global 检查
        if var_name in get_from_env('__globals__', env, []):
            target = env
            while target.get('__parent__') is not None:
                target = target['__parent__']
            target[var_name] = val

        # nonlocal 检查
        elif var_name in get_from_env('__nonlocal__', env, []):
            current = env.get('__parent__', None)
            while current is not None:
                if var_name in current:
                    current[var_name] = val
                    break
                current = current.get('__parent__', None)
        else:
            env[var_name] = val

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
        # 根据 left 的类型生成友好的错误信息
        if left['type'] == 'star_target':
            msg = f"*{left['name']} 不能单独使用，只能在多变量赋值中使用"
        elif left['type'] == 'starstar_target':
            msg = f"**{left['name']} 不能单独使用，只能在多变量赋值中使用"
        else:
            msg = f"无效的赋值目标: {left.get('value', left.get('name', '?'))}"

        raise KeiError("TypeError", msg)

    return val, flag

def node_typeassert_typecheck(val, hint_node, env):
    """独立的类型检查函数，供 node_assign 使用"""
    hint = runtoken(hint_node, env)[0]

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
            return val, False

        if not isinstance(hint, type):
            hint = type(hint)

        if not (isinstance(val, hint) or (isinstance(val, type) and issubclass(val, hint))):
            raise KeiError("TypeError", f"类型错误: 期望 {content(hint)}, 得到 {content(type(val))}")

    return val, False

def node_return(node, env) -> tuple: # if node['type'] == 'return':
    if node['value'] is None:
        return null, True
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

def node_for(node, env) -> tuple:
    vars_list = node['vars']
    iterable_val, _ = runtoken(node['iterable'], env)

    if iterable_val is None or iterable_val is undefined:
        return None, False

    if isinstance(iterable_val, KeiList):
        items = iterable_val.items
    elif isinstance(iterable_val, KeiString):
        items = [KeiString(c) for c in iterable_val.value]
    elif isinstance(iterable_val, KeiDict):
        items = [(k, v) for k, v in iterable_val.items.items()]
    elif hasattr(iterable_val, '__iter__'):
        try:
            items = list(iterable_val)
        except:
            items = [iterable_val]
    else:
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
        # ✅ 对于 KeiDict，直接遍历键值对
        if isinstance(iterable_val, KeiDict):
            for k, v in items:
                env[vars_list[0]] = k
                env[vars_list[1]] = v
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

def node_function(node, env) -> tuple:
    global_names = []
    for stmt in node['body']:
        if stmt['type'] == 'global':
            global_names.extend(stmt['names'])

    func_obj = {
        'type': 'user_function',
        'name': node['name'],
        'params': node['params'],
        'defaults': node.get('defaults', {}),
        'body': node['body'],
        'globals': global_names,
        'closure': env,
        'typeassert': node.get('hint', None),
        'typehints': node.get('typehints', {}),
        'decorators': node.get('decorators', [])
    }

    kei_func = KeiFunction(func_obj, env, filename=__kei__.file)

    # 应用装饰器
    if node.get('decorators'):
        # 1. 先找所有装饰器，记录是否有 prop/static
        has_prop = False
        has_static = False
        decorators = []
        for dec_node in node['decorators']:
            decorator, _ = runtoken(dec_node, env)
            decorators.append(decorator)
            if decorator is stdlib.kei.prop:
                has_prop = True
            elif decorator is stdlib.kei.static:
                has_static = True

        # 2. 执行所有装饰器
        for decorator in decorators:
            if callable(decorator):
                kei_func = decorator(kei_func)

        # 3. 最后设置标志
        if has_prop:
            setattr(kei_func, 'is_property', True)
        if has_static:
            setattr(kei_func, 'is_static', True)

    if node['name']:
        env[node['name']] = kei_func
    else:
        return kei_func, False

    return None, False

def node_class(node, env) -> tuple:
    class_obj = {
        'type': 'class',
        'name': node['name'],
        'parent': node.get('parent'),
        'body': node['body'],
        'methods': [],
        'attrs': {},
        'methods_map': {},
        'decorated_methods': {}
    }

    py_parent = None

    if class_obj['parent']:
        parent = env.get(class_obj['parent'])
        if parent is None or parent is undefined:
            raise KeiError("NameError", f"父类 '{class_obj['parent']}' 未定义")

        if not isinstance(parent, (KeiClass, type)):
            raise KeiError("TypeError", f"'{class_obj['parent']}' 不是类")

        if isinstance(parent, KeiClass):
            class_obj['attrs'] = parent._class_attrs.copy()
            class_obj['methods_map'] = parent.class_obj['methods_map'].copy()
            class_obj['decorated_methods'] = parent.class_obj.get('decorated_methods', {}).copy()
        else:
            py_parent = parent

    for stmt in node['body']:
        if stmt['type'] == 'function':
            original_method_obj = {
                'type': 'user_function',
                'name': stmt['name'],
                'params': stmt['params'],
                'body': stmt['body'],
                'defaults': stmt.get('defaults', {}),
                'decorators': stmt.get('decorators', []),
                'closure': env
            }

            exec_method_obj = {
                'type': 'user_function',
                'name': stmt['name'],
                'params': stmt['params'],
                'body': stmt['body'],
                'defaults': stmt.get('defaults', {}),
                'decorators': stmt.get('decorators', []),
                'closure': env
            }

            kei_func = KeiFunction(exec_method_obj, env, filename=__kei__.file)

            if stmt.get('decorators'):
                has_prop = False
                has_static = False
                decorators = []
                for decorator_node in stmt['decorators']:
                    decorator, _ = runtoken(decorator_node, env)
                    decorators.append(decorator)
                    if decorator is stdlib.kei.prop:
                        has_prop = True
                    elif decorator is stdlib.kei.static:
                        has_static = True

                # 执行所有装饰器（prop 和 static 也会执行，但它们的 __call__ 返回原函数）
                for decorator in decorators:
                    if callable(decorator):
                        kei_func = decorator(kei_func)

                # 最后设置标志
                if has_prop:
                    object.__setattr__(kei_func, 'is_property', True)
                if has_static:
                    object.__setattr__(kei_func, 'is_static', True)

            class_obj['methods_map'][stmt['name']] = original_method_obj
            class_obj['decorated_methods'][stmt['name']] = kei_func

        elif stmt['type'] == 'assign':
            # 创建一个新环境，把 class_obj['attrs'] 作为存储
            attr_env = KeiDict({'__parent__': env} | class_obj['decorated_methods'])
            attr_env.update(class_obj['attrs'])  # 把已有属性放进去

            # 执行赋值（会修改 attr_env）
            node_assign(stmt, attr_env)

            # 把修改后的属性存回 class_obj['attrs']
            for key, value in attr_env.items.items():
                if not key.startswith('_'):
                    class_obj['attrs'][key] = value

    kei_class = KeiClass(class_obj, env)
    if py_parent:
        setattr(kei_class, 'py_parent', py_parent)

    env[node['name']] = kei_class
    return None, False

def node_import(node, env) -> tuple:
    for module_info in node['modules']:
        full_module_name = module_info['module']
        alias = module_info.get('alias')
        is_wildcard = module_info.get('type') == 'wildcard'

        __path__ = get_from_env("__path__", env, KeiList([])).items
        module_path = full_module_name.replace('.', '/')
        module_short_name = module_path.split("/")[-1]

        # 1. 尝试加载 .kei 模块
        exported_dict, module_env, is_kei = _load_kei_module(
            module_path, module_short_name, env, __path__
        )

        if is_kei:
            # 只有 .kei 模块才执行 __import__ 钩子
            _call_import_hook(exported_dict)

            if exported_dict is not None:  # ← 添加检查
                if is_wildcard:
                    for name, value in exported_dict.items.items():
                        env[name] = value
                else:
                    name = alias or module_short_name
                    env[name] = KeiNamespace(name, exported_dict)
            else:
                # 处理 None 的情况
                if is_wildcard:
                    pass  # 没有东西可以导入
                else:
                    name = alias or module_short_name
                    env[name] = KeiNamespace(name, KeiDict({}))  # 空字典

                return None, False

        # 2. 尝试加载 .py 模块
        module_env, is_py = _load_py_module(module_path, __path__)

        if is_py:
            module_dict = KeiDict({}.copy())
            exported_dict = _get_exported_dict(module_env, module_dict)
            # Python 模块不执行 __import__ 钩子

            if is_wildcard:
                for name, value in exported_dict.items.items():
                    env[name] = value
            else:
                name = alias or module_short_name
                env[name] = KeiNamespace(name, exported_dict)

            return None, False

        raise KeiError("ImportError", f"找不到模块: {full_module_name}")

    return None, False

def node_fromimport(node, env) -> tuple:
    module_name = node['module']
    imports = node['imports']

    __path__ = get_from_env("__path__", env, KeiList([])).items
    module_path = module_name.replace('.', '/')
    module_short_name = module_path.split("/")[-1]

    exported_dict = None
    is_kei = False

    # 1. 尝试加载 .kei 模块
    exported_dict, module_env, is_kei = _load_kei_module(
        module_path, module_short_name, env, __path__
    )

    # 2. 如果不是 .kei，尝试加载 .py 模块
    if not is_kei:
        module_env, is_py = _load_py_module(module_path, __path__)
        if is_py:
            module_dict = {}
            exported_dict = _get_exported_dict(module_env, module_dict)

    if exported_dict is None:
        raise KeiError("ImportError", f"找不到模块: {module_name}")

    # 只有 .kei 模块才执行 __import__ 钩子
    if is_kei:
        _call_import_hook(exported_dict)

    # 获取模块的完整导出（包括内置变量）
    module_dict = {}
    full_exported = _get_exported_dict(module_env, module_dict)

    for imp in imports:
        if imp['type'] == 'wildcard':
            for name, value in full_exported.items.items():
                env[name] = value
        else:
            name = imp['name']
            alias = imp.get('alias') or name

            # 优先从 exported_dict（公开导出），再从 module_env（内置）
            if name in exported_dict:
                env[alias] = exported_dict[name]
            elif name in module_env:
                if module_env is not None and name in module_env:
                    env[alias] = module_env[name]
                else:
                    # 处理找不到的情况
                    raise KeiError("ImportError", f"无法从模块导入 '{name}'")
            else:
                raise KeiError("ImportError", f"无法从 {module_name} 导入 {name}")

    return None, False

def node_del(node, env) -> tuple:
    for target in node['names']:
        if target['type'] == 'name':
            name = target['value']
            # 向上查找变量
            current = env
            found = False
            while current is not None:
                if name in current:
                    obj = current[name]
                    # 删除对象本身，调用 __delete__
                    if hasattr(obj, '__delete__') and callable(obj.__delete__):
                        obj.__delete__()
                    del current[name]
                    found = True
                    break
                current = current.get('__parent__', None)
            if not found:
                raise KeiError("NameError", f"名称 '{name}' 未定义")

        elif target['type'] == 'attr':
            obj, _ = runtoken(target['obj'], env)
            attr = target['attr']          # Python str

            # 转成 KeiString 传给 __delattr__
            if hasattr(obj, '__delattr__') and callable(obj.__delattr__):
                obj.__delattr__(KeiString(attr))
            elif isinstance(obj, KeiBase):
                if attr in obj._props:
                    del obj._props[attr]
                else:
                    raise KeiError("AttributeError", f"对象没有属性 '{attr}'")
            elif isinstance(obj, dict):
                if attr in obj:
                    del obj[attr]
                else:
                    raise KeiError("AttributeError", f"字典没有键 '{attr}'")
            elif hasattr(obj, attr):
                delattr(obj, attr)
            else:
                raise KeiError("AttributeError", f"对象没有属性 '{attr}'")

        elif target['type'] == 'index':
            obj, _ = runtoken(target['obj'], env)
            index, _ = runtoken(target['index'], env)

            if hasattr(obj, '__delitem__') and callable(obj.__delitem__):
                obj.__delitem__(index)   # index 已经是 KeiInt/KeiString，不用再转
            elif isinstance(obj, KeiList):
                idx = index.value if isinstance(index, KeiInt) else int(index)
                if 0 <= idx < len(obj.items):
                    del obj.items[idx]
                else:
                    raise KeiError("IndexError", f"索引 {idx} 超出范围")
            elif isinstance(obj, KeiDict):
                key = index
                if key in obj.items:
                    del obj.items[key]
                else:
                    raise KeiError("KeyError", f"键 '{key}' 不存在")
            elif isinstance(obj, (list, dict)):
                del obj[index]
            else:
                raise KeiError("TypeError", f"不支持对 {type(obj)} 使用 del 索引删除")

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

def node_use(node, env) -> tuple:
    for target in node['names']:
        ns, _ = runtoken(target, env)
        if isinstance(ns, KeiNamespace):
            env.update(ns.nsenv)
        else:
            raise KeiError("TypeError", f"use 需要 namespace，得到 {type(ns)}")
    return None, False

def node_namespace(node, env) -> tuple:
    ns_data = KeiDict({}.copy())
    ns_env = NamespaceEnv(env, ns_data)

    for stmt in node['body']:
        runtoken(stmt, ns_env)

    ns = env
    ns[node['name']] = ns_data.copy()
    env[node['name']] = KeiNamespace(node['name'], ns, isns=True)
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
                    if node['var'] is not None and env[node['var']]:
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
            linenum = globals().get('linenum', node.get('linenum', -1))
            source  = globals().get('source', node.get('source', '未知行'))

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
            env['__globals__'] = KeiList([])

        (env['__globals__'].append(var_name)) if var_name not in env['__globals__'] else ...

    return None, False

def node_typeassert(node, env) -> tuple: # if node['type'] == 'typeassert':
    val, flag = runtoken(node['expr'], env)
    return node_typeassert_typecheck(val, node['hint'], env)

def node_nonlocal(node, env) -> tuple:
    """处理 nonlocal 声明"""
    for name_node in node['names']:
        var_name = name_node['value']

        if '__nonlocal__' not in env:
            env['__nonlocal__'] = KeiList([])

        (env['__nonlocal__'].append(var_name)) if var_name not in env['__nonlocal__'] else ...

    return None, False

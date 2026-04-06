from stdlib import kei as stdlib
from lib.object import *

def render_tree(obj, prefix=KeiString(""), style=KeiString("╰")):
    lines = []

    if isinstance(obj, dict):
        keys = sorted(obj.keys())
        for i, k in enumerate(keys):
            is_last_key = (i == len(keys) - 1)
            connector = "{style}─ " if is_last_key else "├─ "
            v = obj[k]

            if isinstance(v, (dict, list)):
                lines.append(f"{prefix}{connector}{k}")
                new_prefix = prefix + ("   " if is_last_key else "│  ")
                lines.extend(render_tree(v, new_prefix, style))
            else:
                lines.append(f"{prefix}{connector}{k}: {v}")

    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            is_last_item = (i == len(obj) - 1)
            connector = f"{style}─ " if is_last_item else "├─ "

            if isinstance(v, (dict, list)):
                lines.append(f"{prefix}{connector}{i}")
                new_prefix = prefix + ("   " if is_last_item else "│  ")
                lines.extend(render_tree(v, new_prefix, style))
            else:
                lines.append(f"{prefix}{connector}{v}")

    else:
        lines.append(f"{prefix}{style}─ {obj}")

    return lines

def tree(obj):
    obj = stdlib.topy(obj)
    print("\n".join(render_tree(obj)))

def box(*text, name='', style=KeiList(["╭", "╮", "╰", "╯", "─", "│"])):
    old = text
    text = []
    for t in old:
        text.append(stdlib.topy(t))

    name = stdlib.topy(name)
    style = stdlib.topy(style)

    maxlong = stdlib.cnlen(max(text, key=len))

    print(style[0]+style[4]+(" " if name else style[4] )+name+(" " if name else style[4] )+ style[4] * (namelong := maxlong - stdlib.cnlen(name) - 2) + style[4]+style[1])

    if namelong <= 0:
        maxlong = stdlib.cnlen(name) + 2

    for t in text:
        long = stdlib.cnlen(t)
        print(f"{style[5]} {t} " + " " * (maxlong-long) + style[5])
    print(f"{style[2]}{style[4]}" + style[4] * maxlong + f"{style[4]}{style[3]}")

__all__ = ["tree", "box"]

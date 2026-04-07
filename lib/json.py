#!/usr/bin/env python

import json as _json
from object import *
from lib.kei2py import *

def dump(obj, indent=0):
    try:
        obj = to_list(obj)
    except:
        obj = to_dict(obj)

    return KeiString(_json.dumps(to_python(obj), ensure_ascii=False, indent=indent))

def load(string):
    string = to_str(string)

    data = _json.loads(string)
    return KeiDict(data) if isinstance(data, dict) else KeiList(data)

__all__ = ['load', 'dump']

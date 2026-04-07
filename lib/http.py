#!/usr/bin/env python
# lib/http.py

import requests
from typing import Any, Union
from object import *
from lib.kei2py import *

def _to_python(obj: Any) -> Any:
    """KeiLang → Python 转换"""
    if obj is None:
        return None
    if isinstance(obj, KeiString):
        return obj.value
    if isinstance(obj, KeiInt):
        return obj.value
    if isinstance(obj, KeiFloat):
        return obj.value
    if isinstance(obj, KeiBool):
        return obj.value
    if isinstance(obj, KeiList):
        return [_to_python(item) for item in obj.items]
    if isinstance(obj, KeiDict):
        return {_to_python(k): _to_python(v) for k, v in obj.items.items()}
    return obj

def _to_kei(obj: Any) -> Any:
    """Python → KeiLang 转换"""
    if obj is None:
        return null
    if isinstance(obj, bool):
        return true if obj else false
    if isinstance(obj, int):
        return KeiInt(obj)
    if isinstance(obj, float):
        return KeiFloat(obj)
    if isinstance(obj, str):
        return KeiString(obj)
    if isinstance(obj, list):
        return KeiList([_to_kei(item) for item in obj])
    if isinstance(obj, dict):
        # 关键修复：键保持 Python 类型（str/int），值转成 Kei 对象
        return KeiDict({k: _to_kei(v) for k, v in obj.items()})
    return obj

def get(url: Union[str, KeiString], headers: Any = None, params: Any = None) -> KeiDict:
    """GET 请求"""
    url = to_str(url)

    py_headers = _to_python(headers) if headers is not None else None
    py_params = _to_python(params) if params is not None else None

    resp = requests.get(url, headers=py_headers, params=py_params)

    return KeiDict({
        "status": KeiInt(resp.status_code),
        "text": KeiString(resp.text),
        "json": lambda: _to_kei(resp.json()),
        "headers": KeiDict(resp.headers),
    })

def post(
    url: Union[str, KeiString],
    data: Any = None,
    json: Any = None,
    headers: Any = None
) -> KeiDict:
    """POST 请求"""
    url = to_str(url)

    py_headers = _to_python(headers) if headers is not None else None
    py_data = _to_python(data) if data is not None else None
    py_json = _to_python(json) if json is not None else None

    resp = requests.post(url, data=py_data, json=py_json, headers=py_headers)

    return KeiDict({
        "status": KeiInt(resp.status_code),
        "text": KeiString(resp.text),
        "json": lambda: _to_kei(resp.json()),
        "headers": KeiDict(resp.headers),
    })

def put(
    url: Union[str, KeiString],
    data: Any = None,
    json: Any = None,
    headers: Any = None
) -> KeiDict:
    """PUT 请求"""
    url = to_str(url)

    py_headers = _to_python(headers) if headers is not None else None
    py_data = _to_python(data) if data is not None else None
    py_json = _to_python(json) if json is not None else None

    resp = requests.put(url, data=py_data, json=py_json, headers=py_headers)

    return KeiDict({
        "status": KeiInt(resp.status_code),
        "text": KeiString(resp.text),
        "json": lambda: _to_kei(resp.json()),
        "headers": KeiDict(resp.headers),
    })

def delete(
    url: Union[str, KeiString],
    headers: Any = None
) -> KeiDict:
    """DELETE 请求"""
    url = to_str(url)

    py_headers = _to_python(headers) if headers is not None else None

    resp = requests.delete(url, headers=py_headers)

    return KeiDict({
        "status": KeiInt(resp.status_code),
        "text": KeiString(resp.text),
        "headers": KeiDict(resp.headers),
    })

__all__ = ['get', 'post', 'put', 'delete']

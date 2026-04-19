#!/usr/bin/env python
from object import true

__log__ = true

def enable(e=None):
    global __log__
    if e is not None:
        __log__ = e

    return __log__

def _log(level, text):
    """内部日志函数"""

    if not enable():
        return

    print(f"[{level}] {text}")

def debug(text):
    _log("DEBUG", text)

def info(text):
    _log("INFO", text)

def notice(text):
    _log("NOTICE", text)

def success(text):
    _log("SUCCESS", text)

def warning(text):
    _log("WARNING", text)

def error(text):
    _log("ERROR", text)

def critical(text):
    _log("CRITICAL", text)

def fatal(text):
    _log("FATAL", text)

def trace(text):
    _log("TRACE", text)

def verbose(text):
    _log("VERBOSE", text)

def ok(text):
    _log("OK", text)

def fail(text):
    _log("FAIL", text)

__all__ = [
    'enable',
    'debug',
    'info',
    'notice',
    'success',
    'warning',
    'error',
    'critical',
    'fatal',
    'trace',
    'verbose',
    'ok',
    'fail'
]
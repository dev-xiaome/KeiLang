#!/bin/bash

import kei
from lib.object import *
from lib.kei2py import *

def tokenize(codes):
    return KeiList(kei.token(to_str(codes)))

def ast(tokens):
    return KeiList(kei.ast(to_list(tokens)))

# def runtime(...): ... 不添加,runtime不属于parser

__all__ = ["tokenize", "ast"]

import random as _random
from object import *
from lib.kei2py import *

def random():
    return _random.random()

def randint(a, b):
    a = to_int(a)
    b = to_int(b)
    return _random.randint(a, b)

def uniform(a, b):
    a = to_float(a)
    b = to_float(b)
    return _random.uniform(a, b)

def choice(seq):
    # seq 可能是 KeiList
    if hasattr(seq, 'items'):
        seq = seq.items
    return _random.choice(seq)

def shuffle(seq):
    if hasattr(seq, 'items'):
        items = seq.items
        _random.shuffle(items)
        return seq
    _random.shuffle(seq)
    return seq

__all__ = ['random', 'randint', 'uniform', 'choice', 'shuffle']

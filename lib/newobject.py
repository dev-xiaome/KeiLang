#!/usr/bin/env python

def nullobj(name):
    class nullobj_class:
        def __init__(self, name):
            self.__name__ = name

        def __content__(self):
            return f"<nullobj {self.__name__}>"

    return nullobj_class(name)

def ns(name="namespace", **datas):
    from object import KeiNamespace
    return KeiNamespace(name, datas)

__all__ = ['nullobj', 'ns']
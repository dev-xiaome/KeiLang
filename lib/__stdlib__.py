import stdlib

for k, v in stdlib.func.items():
    globals()[k] = v

def __dir__():
    return list(stdlib.func.keys())

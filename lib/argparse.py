#!/usr/bin/env python

from object import false, undefined, KeiString

class parser:
    def __init__(self, argv):
        self.argv = argv
        self.args = {}
        self.help_text = {}

    def add(self, short, long=None, args=false, help=""):
        """添加参数"""
        self.help_text[short] = help
        if long:
            self.help_text[long] = help

        # 解析参数
        i = 1
        while i < len(self.argv):
            arg = self.argv[i]

            if arg == short or (long and arg == long):
                if args:
                    # 需要参数值
                    if i + 1 < len(self.argv):
                        self.args[short] = self.argv[i + 1]
                        if long:
                            self.args[long] = self.argv[i + 1]
                        i += 2
                    else:
                        self.args[short] = None
                        if long:
                            self.args[long] = None
                        i += 1
                else:
                    # 布尔标志
                    self.args[short] = True
                    if long:
                        self.args[long] = True
                    i += 1
            else:
                i += 1

    def __getitem__(self, key):
        return self.args.get(key, undefined)

    def get(self, key):
        return self.args.get(key, undefined)

    def __contains__(self, key):
        return key in self.args

    def help(self):
        """返回帮助字符串（带颜色和对齐）"""
        script_name = str(self.argv[0] if self.argv else "script.kei")

        lines = []
        lines.append(f"\033[36m用法:\033[0m {script_name} [选项]")
        lines.append("")
        lines.append(f"\033[36m选项:\033[0m")

        # 收集所有参数
        params = {}
        for key, text in self.help_text.items():
            params[str(key)] = str(text)

        # 找出最长参数名（用于对齐）
        max_len = max((len(key) for key in params.keys()), default=0)

        for key in sorted(params.keys()):
            color = "\033[33m"  # 黄色

            key = str(key)

            lines.append(f"  {color}{key:<{max_len}}\033[0m  {params[key]}")

        return KeiString("\n".join(lines))
#!/usr/bin/env python
# repl.py - KeiLang REPL

import os
import atexit

# 白嫖 readline（优雅降级）
try:
    readline = __import__('readline')

    READLINE_AVAILABLE = True
except:
    READLINE_AVAILABLE = False

import kei

class KeiREPL:
    def __init__(self):
        self.env = None
        self.history_file = os.path.expanduser("~/.keilang_history")
        if READLINE_AVAILABLE:
            self.setup_history()

    def setup_history(self):
        """设置历史记录"""
        try:
            readline.read_history_file(self.history_file)
        except FileNotFoundError:
            pass

        atexit.register(readline.write_history_file, self.history_file)

        # 设置补全
        readline.set_completer(self.completer)
        readline.parse_and_bind("tab: complete")
        readline.set_history_length(1000)

    def completer(self, text, state):
        """智能自动补全"""
        line = readline.get_line_buffer()
        cursor = readline.get_endidx()
        before_cursor = line[:cursor]

        # 1. 对象属性补全 (obj.)
        if '.' in before_cursor:
            last_dot = before_cursor.rfind('.')
            obj_name = before_cursor[:last_dot].strip()

            # 尝试获取对象
            if self.env and obj_name in self.env:
                obj = self.env[obj_name]
                # 获取对象的所有方法/属性
                if hasattr(obj, '_methods'):
                    attrs = list(obj._methods.keys())
                elif hasattr(obj, '__dict__'):
                    attrs = list(obj.__dict__.keys())
                else:
                    attrs = dir(obj)

                # 过滤掉私有属性
                attrs = [a for a in attrs if not a.startswith('_')]
                matches = [a for a in attrs if a.startswith(text)]
                try:
                    return matches[state]
                except IndexError:
                    return None

        # 2. 函数定义补全 (fn 后面)
        words = before_cursor.split()
        if len(words) >= 1 and words[-1] == 'fn':
            # 建议函数名
            suggestions = ['main', 'handler', 'callback', 'init']
            matches = [s for s in suggestions if s.startswith(text)]
            try:
                return matches[state]
            except IndexError:
                return None

        # 3. 导入补全 (import 后面)
        if len(words) >= 1 and words[0] == 'import':
            # 获取可用模块
            import sys
            modules = [m for m in sys.modules.keys() if not m.startswith('_')]
            # 加上你的 lib 目录下的模块
            lib_path = os.path.join(os.path.dirname(__file__), 'lib')
            if os.path.exists(lib_path):
                for f in os.listdir(lib_path):
                    if f.endswith('.py'):
                        modules.append(f[:-3])
                    elif f.endswith('.kei'):
                        modules.append(f[:-4])

            modules = list(set(modules))  # 去重
            matches = [m for m in modules if m.startswith(text)]
            try:
                return matches[state]
            except IndexError:
                return None

        # 4. 默认补全（关键词、标准库、用户变量）
        import kei
        import lib.stdlib as stdlib

        user_vars = []
        if self.env:
            user_vars = []
            if self.env and isinstance(self.env, dict):
                user_vars = [k for k in self.env.keys()
                             if not k.startswith('__') and k != 'env']

        all_completions = (kei.keywords if hasattr(kei, 'keywords') else []) + \
                          [f for f, _ in stdlib.func.items()] + user_vars

        if text:
            matches = [c for c in all_completions if c.startswith(text)]
        else:
            matches = all_completions

        try:
            return matches[state]
        except IndexError:
            return None

    def clear_screen(self):
        """清屏"""
        print('\033[2J\033[H', end='', flush=True)

    def print_banner(self):
        """打印欢迎信息"""
        banner = f"""\033[36m=========================================
      KeiLang REPL 交互式解释器 {kei.__version__}
=========================================
\033[0m输入 .help 查看帮助
"""
        print(banner)

    def show_help(self):
        """显示帮助"""
        help_text = """\033[33m命令:\033[0m
  .exit - 退出 REPL
  .help - 显示此帮助
"""
        print(help_text)

    def run_line(self, line):
        """运行一行代码"""
        line = line.strip()

        # 处理特殊命令
        if line.startswith('.'):
            cmd = line[1:].lower()
            if cmd in 'exit':
                return False

            elif cmd == 'help':
                self.show_help()
                return True

            else:
                print(f"未知命令: {cmd}，输入 .help 查看帮助")
                return True

        # 空行直接返回
        if not line:
            return True

        # 执行代码
        try:
            if self.env is None:
                self.env = {}

            # 执行代码
            self.env = kei.exec(line, self.env)[0]

        except KeyboardInterrupt:
            pass

        return True

    def run(self):
        """主循环"""
        self.print_banner()
        self.env = {}

        while True:
            try:
                # 读取输入
                line = input("\033[32m>>> \033[0m")

                if READLINE_AVAILABLE:
                    readline.redisplay()

                # 处理多行输入（检测花括号）
                if line.strip() and '{' in line and line.count('{') > line.count('}'):
                    lines = [line]
                    brace_count = line.count('{') - line.count('}')

                    while brace_count > 0:
                        try:
                            next_line = input("\033[32m... \033[0m")
                            if not next_line.strip():
                                break
                            lines.append(next_line)
                            brace_count += next_line.count('{') - next_line.count('}')
                        except KeyboardInterrupt:
                            break

                    line = '\n'.join(lines)

                if not self.run_line(line):
                    break

            except KeyboardInterrupt:
                print("\n输入 .exit 退出")
                continue
            except EOFError:
                break

def main():
    repl = KeiREPL()
    repl.run()

if __name__ == "__main__":
    main()

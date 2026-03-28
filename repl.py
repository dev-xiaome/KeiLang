#!/usr/bin/env python
# repl.py - KeiLang REPL

import os
import atexit
import sys

from lib.object import *

try:
    readline = __import__('readline')
    READLINE_AVAILABLE = True
except:
    READLINE_AVAILABLE = False

import kei

class KeiREPL:
    def __init__(self, single=False):
        self.env = None
        self.single = single  # True: 执行一次就退出
        self.history_file = os.path.expanduser("~/.keilang_history")
        self.line = "未知行"

        if READLINE_AVAILABLE and not single:
            self.setup_history()

    def setup_history(self):
        try:
            readline.read_history_file(self.history_file)
        except FileNotFoundError:
            pass
        atexit.register(readline.write_history_file, self.history_file)
        readline.set_completer(self.completer)
        readline.parse_and_bind("tab: complete")
        readline.set_history_length(1000)

    def completer(self, text, state):
        if self.single:
            return None

        line = readline.get_line_buffer()
        cursor = readline.get_endidx()
        before_cursor = line[:cursor]

        if '.' in before_cursor:
            last_dot = before_cursor.rfind('.')
            obj_name = before_cursor[:last_dot].strip()
            if self.env and obj_name in self.env:
                obj = self.env[obj_name]
                if hasattr(obj, '_methods'):
                    attrs = list(obj._methods.keys())
                elif hasattr(obj, '__dict__'):
                    attrs = list(obj.__dict__.keys())
                else:
                    attrs = dir(obj)
                attrs = [a for a in attrs if not a.startswith('_')]
                matches = [a for a in attrs if a.startswith(text)]
                try:
                    return matches[state]
                except IndexError:
                    return None

        words = before_cursor.split()
        if len(words) >= 1 and words[-1] == 'fn':
            suggestions = ['main', 'handler', 'callback', 'init']
            matches = [s for s in suggestions if s.startswith(text)]
            try:
                return matches[state]
            except IndexError:
                return None

        if len(words) >= 1 and words[0] == 'import':
            modules = [m for m in sys.modules.keys() if not m.startswith('_')]
            lib_path = os.path.join(os.path.dirname(__file__), 'lib')
            if os.path.exists(lib_path):
                for f in os.listdir(lib_path):
                    if f.endswith('.py'):
                        modules.append(f[:-3])
                    elif f.endswith('.kei'):
                        modules.append(f[:-4])
            modules = list(set(modules))
            matches = [m for m in modules if m.startswith(text)]
            try:
                return matches[state]
            except IndexError:
                return None

        import kei
        import lib.stdlib as stdlib
        user_vars = []
        if self.env and isinstance(self.env, dict):
            user_vars = [k for k in self.env.keys() if not k.startswith('__') and k != 'env']
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

    def print_banner(self):
        if self.single:
            return
        banner = f"""\033[36m=========================================
    KeiLang REPL 交互式解释器 {kei.__version__}
=========================================
\033[0m输入 .help 查看帮助
"""
        print(banner)

    def show_help(self):
        help_text = """\033[33m命令:\033[0m
  .exit - 退出 REPL
  .help - 显示此帮助
"""
        print(help_text)

    def run_line(self, line):
        line = line.strip()
        if not self.single:
            if line.startswith('.'):
                cmd = line[1:].lower()
                if cmd == 'exit':
                    return False
                elif cmd == 'help':
                    self.show_help()
                    return True
                else:
                    print(f"未知命令: {cmd}，输入 .help 查看帮助")
                    return True

        self.line = line

        if not line:
            return True
        try:
            if self.env is None:
                self.env = {}
            try:
                tokens = kei.ast(kei.token(line))
            except:
                return True
            for t in tokens:
                try:
                    self.env = kei.runtoken(t, self.env)[0]
                except:
                    kei.__kei__.code = line
                    raise

        except KeyboardInterrupt:
            pass
        return True

    def run(self):
        self.print_banner()
        self.env = {}

        # 单行模式：只读取一次
        if self.single:
            try:
                # 读取一行
                line = input("\033[32m>>> \033[0m")
                if READLINE_AVAILABLE:
                    readline.redisplay()

                # 处理多行输入（括号不匹配时继续读）
                paren_count = line.count('(') - line.count(')')
                brace_count = line.count('{') - line.count('}')
                bracket_count = line.count('[') - line.count(']')

                if paren_count > 0 or brace_count > 0 or bracket_count > 0:
                    lines = [line]
                    while paren_count > 0 or brace_count > 0 or bracket_count > 0:
                        try:
                            next_line = input("\033[32m... \033[0m")
                            if not next_line.strip() and (paren_count > 0 or brace_count > 0 or bracket_count > 0):
                                break
                            lines.append(next_line)
                            paren_count += next_line.count('(') - next_line.count(')')
                            brace_count += next_line.count('{') - next_line.count('}')
                            bracket_count += next_line.count('[') - next_line.count(']')
                        except KeyboardInterrupt:
                            break
                    line = '\n'.join(lines)

                self.run_line(line)
            except KeyboardInterrupt:
                pass
            except EOFError:
                pass
            return

        # 正常 REPL 模式：循环
        while True:
            try:
                line = input("\033[32m>>> \033[0m")
                if READLINE_AVAILABLE:
                    readline.redisplay()

                paren_count = line.count('(') - line.count(')')
                brace_count = line.count('{') - line.count('}')
                bracket_count = line.count('[') - line.count(']')

                if paren_count > 0 or brace_count > 0 or bracket_count > 0:
                    lines = [line]
                    while paren_count > 0 or brace_count > 0 or bracket_count > 0:
                        try:
                            next_line = input("\033[32m... \033[0m")
                            if not next_line.strip() and (paren_count > 0 or brace_count > 0 or bracket_count > 0):
                                break
                            lines.append(next_line)
                            paren_count += next_line.count('(') - next_line.count(')')
                            brace_count += next_line.count('{') - next_line.count('}')
                            bracket_count += next_line.count('[') - next_line.count(']')
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

def main(single=False):
    kei.__kei__.repl = True

    repl: KeiREPL = KeiREPL(single=single)

    try:
        repl.run()
    except KeiError as e:
        e.code = repl.line
        raise

if __name__ == "__main__":
    main()

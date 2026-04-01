#!/usr/bin/env python
# type: ignore

"""KeiLang tkinter 包装库 - 自动转换 KeiLang ↔ Python 类型"""

from typing import Any, Callable, Optional, Union, Dict
from lib.object import *
from lib.python import topy, tokei
import tkinter as _tkinter
from tkinter import ttk as _ttk

class tk:
    """tkinter 主模块包装"""

    def __init__(self) -> None:
        self._tk = _tkinter
        self._root: Optional[_tkinter.Tk] = None

    def _get_root(self) -> _tkinter.Tk:
        """获取或创建 Tk 实例"""
        if self._root is None:
            self._root = self._tk.Tk()
        return self._root

    def _wrap_callback(self, func: Callable) -> Callable:
        """包装回调函数，自动转换参数"""
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            py_args = [tokei(a) if not isinstance(a, KeiBase) else a for a in args]
            py_kwargs = {k: tokei(v) if not isinstance(v, KeiBase) else v for k, v in kwargs.items()}
            result = func(*py_args, **py_kwargs)
            return topy(result) if result is not None else None
        return wrapper

    # ========== 窗口 ==========

    def Tk(self) -> Any:
        """创建主窗口"""
        return _wrap_widget(self._tk.Tk())

    def Toplevel(self, master: Any = None) -> Any:
        """创建顶级窗口"""
        master = _unwrap_widget(master) if master else None
        return _wrap_widget(self._tk.Toplevel(master))

    # ========== 组件 ==========

    def Label(self, master: Any = None, **kwargs: Any) -> Any:
        """标签"""
        master = _unwrap_widget(master) if master else None
        py_kwargs = {k: topy(v) for k, v in kwargs.items()}
        return _wrap_widget(self._tk.Label(master, **py_kwargs))

    def Button(self, master: Any = None, **kwargs: Any) -> Any:
        """按钮"""
        master = _unwrap_widget(master) if master else None
        py_kwargs = {k: topy(v) for k, v in kwargs.items()}
        if 'command' in py_kwargs and callable(py_kwargs['command']):
            py_kwargs['command'] = self._wrap_callback(py_kwargs['command'])
        return _wrap_widget(self._tk.Button(master, **py_kwargs))

    def Entry(self, master: Any = None, **kwargs: Any) -> Any:
        """输入框"""
        master = _unwrap_widget(master) if master else None
        py_kwargs = {k: topy(v) for k, v in kwargs.items()}
        return _wrap_widget(self._tk.Entry(master, **py_kwargs))

    def Text(self, master: Any = None, **kwargs: Any) -> Any:
        """文本框"""
        master = _unwrap_widget(master) if master else None
        py_kwargs = {k: topy(v) for k, v in kwargs.items()}
        return _wrap_widget(self._tk.Text(master, **py_kwargs))

    def Frame(self, master: Any = None, **kwargs: Any) -> Any:
        """框架"""
        master = _unwrap_widget(master) if master else None
        py_kwargs = {k: topy(v) for k, v in kwargs.items()}
        return _wrap_widget(self._tk.Frame(master, **py_kwargs))

    def Canvas(self, master: Any = None, **kwargs: Any) -> Any:
        """画布"""
        master = _unwrap_widget(master) if master else None
        py_kwargs = {k: topy(v) for k, v in kwargs.items()}
        return _wrap_widget(self._tk.Canvas(master, **py_kwargs))

    # ========== 对话框 ==========

    def messagebox(self) -> Any:
        """消息框"""
        import tkinter.messagebox as mb
        return _MessageBox(mb)

    def filedialog(self) -> Any:
        """文件对话框"""
        import tkinter.filedialog as fd
        return _FileDialog(fd)

    def colorchooser(self) -> Any:
        """颜色选择器"""
        import tkinter.colorchooser as cc
        return _ColorChooser(cc)

    # ========== 常量 ==========

    @property
    def END(self) -> KeiString:
        return KeiString("end")

    @property
    def INSERT(self) -> KeiString:
        return KeiString("insert")

    @property
    def CURRENT(self) -> KeiString:
        return KeiString("current")

    @property
    def ANCHOR(self) -> KeiString:
        return KeiString("anchor")

    # ========== 事件绑定 ==========

    def bind_all(self, sequence: Any, func: Callable) -> None:
        """全局绑定"""
        self._get_root().bind_all(topy(sequence), self._wrap_callback(func))

    # ========== 主循环 ==========

    def mainloop(self) -> None:
        """主循环"""
        self._get_root().mainloop()

    def quit(self) -> None:
        """退出"""
        self._get_root().quit()

    def update(self) -> None:
        """更新"""
        self._get_root().update()


class _MessageBox(KeiBase):
    """消息框"""

    def __init__(self, mb: Any) -> None:
        super().__init__("messagebox")
        self._mb = mb

    def showinfo(self, title: Any, message: Any) -> Any:
        """信息框"""
        return tokei(self._mb.showinfo(topy(title), topy(message)))

    def showwarning(self, title: Any, message: Any) -> Any:
        """警告框"""
        return tokei(self._mb.showwarning(topy(title), topy(message)))

    def showerror(self, title: Any, message: Any) -> Any:
        """错误框"""
        return tokei(self._mb.showerror(topy(title), topy(message)))

    def askquestion(self, title: Any, message: Any) -> KeiString:
        """提问框"""
        return KeiString(self._mb.askquestion(topy(title), topy(message)))

    def askokcancel(self, title: Any, message: Any) -> KeiBool:
        """OK/取消"""
        return KeiBool(self._mb.askokcancel(topy(title), topy(message)))

    def askyesno(self, title: Any, message: Any) -> KeiBool:
        """是/否"""
        return KeiBool(self._mb.askyesno(topy(title), topy(message)))

    def askretrycancel(self, title: Any, message: Any) -> KeiBool:
        """重试/取消"""
        return KeiBool(self._mb.askretrycancel(topy(title), topy(message)))


class _FileDialog(KeiBase):
    """文件对话框"""

    def __init__(self, fd: Any) -> None:
        super().__init__("filedialog")
        self._fd = fd

    def askopenfilename(self, **kwargs: Any) -> KeiString:
        """打开文件"""
        py_kwargs = {k: topy(v) for k, v in kwargs.items()}
        return KeiString(self._fd.askopenfilename(**py_kwargs))

    def asksaveasfilename(self, **kwargs: Any) -> KeiString:
        """保存文件"""
        py_kwargs = {k: topy(v) for k, v in kwargs.items()}
        return KeiString(self._fd.asksaveasfilename(**py_kwargs))

    def askdirectory(self, **kwargs: Any) -> KeiString:
        """选择目录"""
        py_kwargs = {k: topy(v) for k, v in kwargs.items()}
        return KeiString(self._fd.askdirectory(**py_kwargs))

    def askopenfilenames(self, **kwargs: Any) -> KeiList:
        """打开多个文件"""
        py_kwargs = {k: topy(v) for k, v in kwargs.items()}
        files = self._fd.askopenfilenames(**py_kwargs)
        return KeiList([KeiString(f) for f in files])


class _ColorChooser(KeiBase):
    """颜色选择器"""

    def __init__(self, cc: Any) -> None:
        super().__init__("colorchooser")
        self._cc = cc

    def askcolor(self, **kwargs: Any) -> Any:
        """选择颜色"""
        py_kwargs = {k: topy(v) for k, v in kwargs.items()}
        color = self._cc.askcolor(**py_kwargs)
        if color and color[0]:
            return KeiDict({
                "rgb": KeiList([KeiInt(c) for c in color[0]]),
                "hex": KeiString(color[1])
            })
        return null


class _Widget(KeiBase):
    """组件包装"""

    def __init__(self, widget: Any) -> None:
        super().__init__("widget")
        self._widget  = widget
        self.__name__ = "Tk"

    def _wrap_callback(self, func: Callable) -> Callable:
        """包装回调函数"""
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            py_args = [tokei(a) if not isinstance(a, KeiBase) else a for a in args]
            py_kwargs = {k: tokei(v) if not isinstance(v, KeiBase) else v for k, v in kwargs.items()}
            result = func(*py_args, **py_kwargs)
            return topy(result) if result is not None else None
        return wrapper

    def __getattr__(self, name: str) -> Any:
        """动态获取组件方法"""
        attr = getattr(self._widget, name)
        if callable(attr):
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                py_args = [topy(a) for a in args]
                py_kwargs = {k: topy(v) for k, v in kwargs.items()}
                if 'command' in py_kwargs and callable(py_kwargs['command']):
                    py_kwargs['command'] = self._wrap_callback(py_kwargs['command'])
                result = attr(*py_args, **py_kwargs)
                if result is None:
                    return null
                return tokei(result)
            return wrapper
        return tokei(attr)

    def __setitem__(self, key: Any, value: Any) -> None:
        """设置属性"""
        setattr(self._widget, key, to_python(value))

    def __getitem__(self, key: Any) -> Any:
        """获取属性"""
        return tokei(getattr(self._widget, key))

class _Event(KeiBase):
    """事件包装"""

    def __init__(self, event: Any) -> None:
        super().__init__("event")
        self._event = event

    def __getattr__(self, name: str) -> Any:
        return tokei(getattr(self._event, name))

    def __repr__(self) -> str:
        return f"<event {self._event}>"


def _wrap_widget(widget: Any) -> Any:
    """包装组件"""
    if widget is None:
        return null
    return _Widget(widget)


def _unwrap_widget(widget: Any) -> Any:
    """解包组件"""
    if widget is null or widget is undefined:
        return None
    if isinstance(widget, _Widget):
        return widget._widget
    return to_python(widget)


def _wrap_event(event: Any) -> Any:
    """包装事件"""
    return _Event(event)


def to_python(value: Any) -> Any:
    """KeiLang → Python（不递归转换）"""
    if value is null or value is undefined:
        return None
    if isinstance(value, KeiInt):
        return value.value
    if isinstance(value, KeiFloat):
        return value.value
    if isinstance(value, KeiString):
        return value.value
    if isinstance(value, KeiBool):
        return value.value
    if isinstance(value, _Widget):
        return value._widget
    return value

# ========== 创建默认实例 ==========
_default = tk()

# 暴露所有公开方法
Tk = _default.Tk
Toplevel = _default.Toplevel
Label = _default.Label
Button = _default.Button
Entry = _default.Entry
Text = _default.Text
Frame = _default.Frame
Canvas = _default.Canvas
messagebox = _default.messagebox
filedialog = _default.filedialog
colorchooser = _default.colorchooser
mainloop = _default.mainloop
quit = _default.quit
update = _default.update
bind_all = _default.bind_all
END = _default.END
INSERT = _default.INSERT
CURRENT = _default.CURRENT
ANCHOR = _default.ANCHOR

# 也保留 tk 类本身（如果需要创建多个实例）
tk = _default

# ========== 导出 ==========
__all__ = [
    'Tk', 'Toplevel', 'Label', 'Button', 'Entry', 'Text', 'Frame', 'Canvas',
    'messagebox', 'filedialog', 'colorchooser', 'mainloop', 'quit', 'update',
    'bind_all', 'END', 'INSERT', 'CURRENT', 'ANCHOR', 'tk'
]
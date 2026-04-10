# **KeiLang**
## 欢迎来到`KeiLang`
### `KeiLang`是一个我自制的图灵完备的编程语言
### 语法参照了`Python`的语法规则
### 加入了一些我喜欢的特点:
### &nbsp;&nbsp;**·** 大括号
### &nbsp;&nbsp;**·** undefined
### &nbsp;&nbsp;**·** 语法糖
### &nbsp;&nbsp;**·** main入口点
### &nbsp;&nbsp;**·** 分号分隔语句 _(这是被迫的)_
> **undefined会让不存在的变量或索引不报错，而是返回undefined**
### 一些例子:
#### Hello World
```kei
fn main() {
    print("Hello,World!");
};
```

#### 箭头函数 VS 普通函数
```kei
fn add() => x + y;

fn add() {
    return x + y;
};

# 效果完全一样
```
#### 空值合并
```kei
fn main() {
    print(msg ?? "Hi"); # msg 为 undefined
};

```
#### 类型断言
```kei
fn main() {
    a = 42;
    print(a -> int); # 值 -> 类型
    print(a -> string); # 报错, 因为42不是string对象
};
```
## **安装**
### 克隆仓库
#### $ git clone https://github.com/dev-xiaome/KeiLang.git
#### $ cd KeiLang
#### $ python3 kei.py --help
### 可选: 添加path
#### 在.bashrc中添加(或你的shell配置文件中)
#### export PATH="$PATH:/path/to/kei/" # bash/zsh
#### set -gx PATH $PATH /path/to/kei/ # fish
## **使用**
### $ kei.py --help # 不需要python kei.py!

---

# Updata Logs

> 此部分采用英语 | This part is in English

## 1.8 - Backtick Multiline Strings

### Added
> _Oh, no. Markdown can't create complex mixed effects._
- Multiline strings using \` (backtick)
  - Same-line: \`text\`
  - Cross-line: \`line1\nline2\`
  - Prefixes: f\`, r\`, fr\`, rf\`

### Fixed
- F-string empty `{}` now shows correct line number
- KDB no longer spams `static`/`prop` changes
- Recursion depth properly tracked

### Changed
- Tokenizer now handles `0xFF`, `0b1010`, `1e-5` numbers
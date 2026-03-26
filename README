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
# expr_codegen 符号表达式代码生成器

一个将表达式转成其它代码的工具

## 项目背景

`polars`语法不同于`pandas`,也不同于常见的表达式，导致学习难度大，转译还容易出错。所以创建此项目为解决以下问题：

1. 提取公共表达式，减少代码量和重复计算
2. 对表达式进行化简，便于人理解
3. 时序与横截面表达式自动进行分离，解决人难于处理多层嵌套表达式问题

第一阶段开发完成后，发现此项目其实也可以用于生成其它库的代码或语言。所以又重新更名和调整代码。目前已经支持

1. Polars
2. Pandas

还有很多算子还没实现完全，欢迎贡献代码

## 在线演示

https://exprcodegen0710.streamlit.app (可能地址有变更，新地址请参考置顶issue)

初级用户可以直接访问此链接进行表达式转译，不需要另外安装软件。
此工具免费部署在国外，打开可能有些慢

## 使用方法

由于每位用户的使用场景都各有不同，所以不提供安装包，更多是教会大家如何进行二次开发。

1. 通过`git clone --depth=1 https://github.com/wukan1986/expr_codegen.git` 或 `手工下载zip` 到本地
2. 进入到目录中，通过`pip install -r requirements.txt`安装依赖
3. 使用IDE(例如PyCharm或VSCode)，打开项目，按需定制
4. 运行`demo_cn.py`生成`output.py`，将此文件复制到其它项目中，修改数据读取和保存等部分即可

## 目录结构

```commandline
│  requirements.txt # 通过`pip install -r requirements.txt`安装依赖
├─examples
│      alpha101.py # WorldQuant Alpha101示例
│      demo_cn.py # 中文注释示例。主要修改此文件。建议修改前先备份
│      demo_exec.py # 演示表达式不生成文件直接生成结果画图
│      output_polars.py # 结果输出。之后需修改数据加载和保存等部分
│      show_tree.py # 画表达式树形图。可用于分析对比优化结果
│      sympy_define.py # 符号定义，由于太多地方重复使用到，所以统一提取到此处
├─expr_codegen
│   │  expr.py # 表达式处理基本函数
│   │  tool.py # 核心工具代码。一般不需修改
│   ├─polars
│   │  │  code.py # 针对polars语法的代码生成功能
│   │  │  template.py.j2 # `Jinja2`模板。用于生成对应py文件，一般不需修改
│   │  │  printer.py # 继承于`Sympy`中的`StrPrinter`，添加新函数时需修改此文件
├─gp
│   遗传算法相关代码

```

## 工作原理

本项目主于依赖于`sympy`项目。所用到的主要函数如下：

1. `simplify`: 对复杂表达式进行化简
2. `cse`: Common Subexpression Elimination公共子表达式消除
3. `StrPrinter`: 根据不同的函数输出不同字符串。定制此代码可以支持其它语种或库

因为`groupby`,`sort`都比较占用时间。如果提前将公式分类，不同的类别使用不同的`groupby`，可以减少计算时间。

1. `ts_xxx(ts_xxx)`: 可在同一`groupby`中进行计算
2. `cs_xxx(cs_xxx)`: 可在同一`groupby`中进行计算
3. `ts_xxx(cs_xxx)`: 需在不同`groupby`中进行计算
4. `cs_xxx(ts_xxx(cs_xxx))`: 需三不同`groupby`中进行计算
5. `gp_xxx(aa, )+gp_xxx(bb, )`: 因`aa`,`bb`不同，需在两不同`groupby`中进行计算

所以

1. 需要有一个函数能获取当前表达式的类别(`get_current`)和子表达式的类别(`get_children`)
2. 如果当前类别与子类别不同就可以提取出短公式(`extract`)。不同层的同类别表达式有先后关系，不能放同一`groupby`
3. 利用`cse`的特点，将长表达式替换成前期提取出来的短表达式。然后输入到有向无环图(`DAG`)
4. 利用有向无环图的流转，进行分层。同一层的`ts`,`cs`,`gp`不区分先后
5. 同一层对`ts`,`cs`,`gp`分组，然后生成代码(`codegen`)即可

隐含信息

1. `ts`: sort(by=[ASSET, DATE]).groupby(by=[ASSET], maintain_order=True)
2. `cs`: sort(by=[DATE]).groupby(by=[DATE], maintain_order=False)
3. `gp`: sort(by=[DATE, GROUP]).groupby(by=[DATE, GROUP], maintain_order=False)

即

1. 时序函数隐藏了两个字段`ASSET, DATE`，横截面函数了隐藏了一个字段`DATE`
2. 分组函数转入了一个字段`GROUP`，同时隐藏了一个字段`DATE`

两种分类方法

1. 根据算子前缀分类(`get_current_by_prefix`)，限制算子必需以`ts_`、`cs_`、`gp_`开头
2. 根据算子全名分类(`get_current_by_name`), 不再限制算子名。比如`cs_rank`可以叫`rank`

## 二次开发

1. 备份后编辑`demo_cn.py`,先修改`exprs_src`的定义，添加多个公式，并设置好相应的输出列名
2. 观察`exprs_src`中是否有还未定义的函数，须在前面定义，否则`python`直接报`NameError`
3. 然后`printer.py`添加对应函数的打印代码。
    - 注意：需要留意是否要加`()`，不加时可能优先级混乱，可以每次都加括号，也可用提供的`parenthesize`简化处理

## 贡献代码

1. 还有很多函数没有添加，需要大家提交代码一起完善
2. 目前表达式样式优先向WorldQuant 的 Alpha101 靠齐

## 小技巧

`sympy`不支持`==`，而是当成两个对象比较。例如：

1. `if_else(OPEN==CLOSE, HIGH, LOW)`, 一开始就变成了`if_else(False, HIGH, LOW)`
2. 可以用`Eq`来代替，`if_else(Eq(OPEN, CLOSE), HIGH, LOW)`。具体示例请参考`Alpha101`中的`alpha_021`

`sympy`不支持`bool`转`int`。例如：

1. `(OPEN < CLOSE) * -1`报错 `TypeError: unsupported operand type(s) for *: 'StrictLessThan' and 'int'`
2. 可以用`if_else`代替。`if_else(OPEN<CLOSE, -1, 0)`。具体示例请参考`Alpha101`中的`alpha_064`

## 示例片段

需要转译的部分公式，详细代码请参考 [Demo](examples/demo_cn.py)

```python
exprs_src = {
    "expr_1": -ts_corr(cs_rank(ts_mean(OPEN, 10)), cs_rank(ts_mean(CLOSE, 10)), 10),
    "expr_2": cs_rank(ts_mean(OPEN, 10)) - abs(log(ts_mean(CLOSE, 10))) + gp_rank(sw_l1, CLOSE),
    "expr_3": ts_mean(cs_rank(ts_mean(OPEN, 10)), 10),
    "expr_4": cs_rank(ts_mean(cs_rank(OPEN), 10)),
    "expr_5": -ts_corr(OPEN, CLOSE, 10),
}
```

转译后的代码片段，详细代码请参考[Polars版](examples/output_polars.py)

```python
def func_2_cs__date(df: pl.DataFrame):
    df = df.with_columns(
        # expr_4 = cs_rank(x_7)
        expr_4=(expr_rank_pct(pl.col("x_7"))),
    )
    return df


def func_3_ts__asset__date(df: pl.DataFrame):
    df = df.with_columns(
        # expr_5 = -ts_corr(OPEN, CLOSE, 10)
        expr_5=(-pl.rolling_corr(pl.col("OPEN"), pl.col("CLOSE"), window_size=10)),
    )
    return df


df = df.sort(by=["asset", "date"]).groupby(by=["asset"], maintain_order=True).apply(func_0_ts__asset__date)
df = df.sort(by=["date"]).groupby(by=["date"], maintain_order=False).apply(func_0_cs__date)
df = func_0_cl(df)
```

转译后的代码片段，详细代码请参考[Pandas版](examples/output_pandas.py)

```python
def func_2_cs__date(df: pd.DataFrame) -> pd.DataFrame:
    # expr_4 = cs_rank(x_7)
    df["expr_4"] = (df["x_7"]).rank(pct=True)
    return df


def func_3_ts__asset__date(df: pd.DataFrame) -> pd.DataFrame:
    # expr_5 = -ts_corr(OPEN, CLOSE, 10)
    df["expr_5"] = -(df["OPEN"]).rolling(10).corr(df["CLOSE"])
    # expr_6 = ts_delta(OPEN, 10)
    df["expr_6"] = df["OPEN"].diff(10)
    return df


df = df.sort_values(by=["asset", "date"]).groupby(by=["asset"], group_keys=False).apply(func_0_ts__asset__date)
df = df.groupby(by=["date"], group_keys=False).apply(func_0_cs__date)
df = func_0_cl(df)
```

## 生成代码不写文件直接执行
参考示例中的`demo_exec.py`, 它提前准备了数据，然后将表达式转成代码，直接通过`exec`执行，可以在之后的代码中直接使用结果

## 遗传算法
请参考`gp`目录
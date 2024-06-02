# expr_codegen 符号表达式代码生成器

表达式转代码工具

## 项目背景

在本人新推出[polars_ta](https://github.com/wukan1986/polars_ta)这个库后，再回头反思`expr_codegen`是什么。

> `expr_cdegen`本质是`DSL`，领域特定语⾔(Domain Specific Language)。但它没有定义新的语法

它解决了两个问题:

1. `polars_ta`已经能很方便的写出特征计算表达式，但遇到`混用时序与截面`的表达式，利用`expr_codegen`能自动分组大大节省工作
2. `expr_codegen`利用了`Common Subexpression Elimination`公共子表达式消除，大量减少重复计算，提高效率

就算在量化领域，初级研究员局限于时序指标，仅用`polars_ta`即可，中高级研究员使用截面指标，推荐用`expr_codegen`

虽然现在此项目与`polars_ta`依赖非常紧密，但也是支持翻译成其它库,如`pandas / cudf.pandas`，只是目前缺乏一个比较简易的库

## 在线演示

https://exprcodegen.streamlit.app

初级用户可以直接访问此链接进行表达式转译，不需要另外安装软件。(此工具免费部署在国外，打开可能有些慢)

更完整示例访问[alpha_examples](https://github.com/wukan1986/alpha_examples)

## 使用示例

```python
import sys

# from polars_ta.prefix.talib import *  # noqa
from polars_ta.prefix.cdl import *  # noqa
from polars_ta.prefix.ta import *  # noqa
from polars_ta.prefix.tdx import *  # noqa
from polars_ta.prefix.wq import *  # noqa

from expr_codegen.tool import codegen_exec


def _code_block_1():
    # 因子编辑区，可利用IDE的智能提示在此区域编辑因子
    LOG_MC_ZS = cs_mad_zscore(log1p(market_cap))


def _code_block_2():
    # 模板中已经默认导入了from polars_ta.prefix下大量的算子，但
    # talib在模板中没有默认导入。这种写法可实现在生成的代码中导入
    from polars_ta.prefix.talib import ts_LINEARREG_SLOPE  # noqa

    # 1. 下划线开头的变量只是中间变量,会被自动更名，最终输出时会被剔除
    # 2. 下划线开头的变量可以重复使用。多个复杂因子多行书写时有重复中间变时不再冲突
    _avg = ts_mean(corr, 20)
    _std = ts_std_dev(corr, 20)
    _beta = ts_LINEARREG_SLOPE(corr, 20)

    # 3. 下划线开头的变量有环循环赋值。在调试时可快速用注释进行切换
    _avg = cs_mad_zscore_resid(_avg, LOG_MC_ZS, ONE)
    _std = cs_mad_zscore_resid(_std, LOG_MC_ZS, ONE)
    # _beta = cs_mad_zscore_resid(_beta, LOG_MC_ZS, ONE)

    _corr = cs_zscore(_avg) + cs_zscore(_std)
    CPV = cs_zscore(_corr) + cs_zscore(_beta)


df = None  # 替换成真实的polars数据
df = codegen_exec(df, _code_block_1, _code_block_2, output_file=sys.stdout)  # 打印代码
df = codegen_exec(df, _code_block_1, _code_block_2, output_file="output.py")  # 保存到文件
df = codegen_exec(df, _code_block_1, _code_block_2)  # 只执行，不保存代码

```

## 目录结构

```commandline
│  requirements.txt # 通过`pip install -r requirements.txt`安装依赖
├─data
│      prepare_date.py # 准备数据
├─examples
│      demo_express.py # 速成示例。演示如何将表达式转换成代码
│      demo_exec_pl.py # 演示调用转换后代码并绘图
│      demo_transformer.py # 演示将第三方表达式转成内部表达式
│      output.py # 结果输出。可不修改代码，直接被其它项目导入
│      show_tree.py # 画表达式树形图。可用于分析对比优化结果
│      sympy_define.py # 符号定义，由于太多地方重复使用到，所以统一提取到此处
├─expr_codegen
│   │  expr.py # 表达式处理基本函数
│   │  tool.py # 核心工具代码。一般不需修改
│   ├─polars
│   │  │  code.py # 针对polars语法的代码生成功能
│   │  │  template.py.j2 # `Jinja2`模板。用于生成对应py文件，一般不需修改
│   │  │  printer.py # 继承于`Sympy`中的`StrPrinter`，添加新函数时可能需修改此文件
```

## 工作原理

本项目依赖于`sympy`项目。所用到的主要函数如下：

1. `simplify`: 对复杂表达式进行化简
2. `cse`: `Common Subexpression Elimination`公共子表达式消除
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

1. 备份后编辑`demo_express.py`, `import`需要引入的函数
2. 然后`printer.py`有可能需要添加对应函数的打印代码
    - 注意：需要留意是否要加括号`()`，不加时可能优先级混乱，可以每次都加括号，也可用提供的`parenthesize`简化处理

## `expr_codegen`局限性

1. `DAG`只能增加列无法删除。增加列时，遇到同名列会覆盖
2. 不支持`删除行`，但可以添加删除标记列，然后在外进行删除行。删除行影响了所有列，不满足`DAG`
3. 不支持`重采样`，原理同不支持删除行。需在外进行
4. 可以将`删除行`与`重采样`做为分割线，一大块代码分成多个`DAG`串联。复杂不易理解，所以最终没有实现

## 小技巧

1. `sympy`不支持`==`，而是当成两个对象比较。例如：
    1. `if_else(OPEN==CLOSE, HIGH, LOW)`, 一开始就变成了`if_else(False, HIGH, LOW)`
    2. 可以用`Eq`来代替，`if_else(Eq(OPEN, CLOSE), HIGH, LOW)`。具体示例请参考`Alpha101`中的`alpha_021`

2. `sympy`不支持`bool`转`int`。例如：
    1. `(OPEN < CLOSE) * -1`报错 `TypeError: unsupported operand type(s) for *: 'StrictLessThan' and 'int'`
    2. 可以用`if_else`代替。`if_else(OPEN<CLOSE, 1, 0)*-1`。具体示例请参考`Alpha101`中的`alpha_064`
3. Python不支持`?:`三元表达式，只支持`if else`, 而在本项目中需要转成`if_else`

以上三种问题本项目都使用`ast`进行了处理，可以简化使用

## 转译结果示例

转译后的代码片段，详细代码请参考[Polars版](examples/output_polars.py)

```python
def func_0_ts__asset(df: pl.DataFrame) -> pl.DataFrame:
    df = df.sort(by=[_DATE_])
    # ========================================
    df = df.with_columns(
        _x_0=1 / ts_delay(OPEN, -1),
        LABEL_CC_1=(-CLOSE + ts_delay(CLOSE, -1)) / CLOSE,
    )
    # ========================================
    df = df.with_columns(
        LABEL_OO_1=_x_0 * ts_delay(OPEN, -2) - 1,
        LABEL_OO_2=_x_0 * ts_delay(OPEN, -3) - 1,
    )
    return df
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

```

## 本地部署交互网页

只需运行`streamlit run streamlit_app.py`

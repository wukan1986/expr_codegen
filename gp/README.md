# 遗传算法编程

本项目演示如何在遗传算法中使用表达式转代码工具。本人很早就用`deap`做过遗传算法，没用过`gplearn`，所以这次继续沿用`deap`

## 安装

```commandline
pip install -r requirements.txt # 安装遗传编程依赖
```

# 快速运行最简示例

1. 运行`data/prepare_date.py`准备数据
2. 运行`gp/main.py`，观察打印输出，结果生成在`log`下
3. 运行`gp/out_of_sample.py`，得到名人堂的样本外适应度，默认会生成`codes_9999.py`，可导入到其它项目中直接使用

## 本项目特点

1. 种群中有大量相似表达式，而`expr_codegen`中的`cse`公共子表达式消除可以减少大量重复计算
2. `polars`支持并发，可同一种群所有个体一起计算

所以

1. 鼓励`Rust`高手能向`Polars`贡献常用函数代码，提高效率、方便投研
2. 鼓励大家向`polars_ta`贡献代码
3. 建议使用大内存，如`>=64G`

## 目录

1. `check_codes.py` # 当发现生成的代码有误或太慢时，可在此调试
2. `check_exprs.py` # 当发现生成的表达式有误时，可在此对表达式进行调试。**可显示LATEX，可绘制表达式树**
3. `custom.py` # 导入算子、因子、和常数
4. `helper.py` # 一些辅助函数
5. `main.py` # 入口函数，可在这调整参数或添加功能
6. `out_of_sample.py` # 计算样本外适应度
7. `primitives.py` # 自动生成的算子，仅用于参考
8. `../log/` # 记录每代种群的表达式，生成的代码
9. `../tools/` # 自动生成辅助脚本

## 使用进阶

1. 根据自己的需求，修改`custom.py`,添加算子、因子和常数
2. `log`目录提前备份并清空一下
3. `prepare_date.py`参考准备数据，一定要注意准备标签字段用于计算IC等指标。直接执行生成测试数据
4. `main.py`中修改遗传算法种群、代数、随机数种子等参数，运行

## Q&A

Q: 为何生成的表达式无法直接使用?

A: 项目涉及到几个模块`sympy`、`deap`、`LaTeX`，`polars_ta`，需要取舍。以`max`为例

1. `polar_ta`，为了不与`buildins`冲突，所以命名为`max_`
2. `deap`中，为了按参数类型生成表达式更合理，所以定义了`imax(OPEN, 1)`与`fmax(OPEN, CLOSE)`
3. `deap`生成后通过`convert_inverse_prim`生成`sympy`进行简化提取公共子表达式
4. `sympy`有`Max`内部可通过`LatexPrinter`转到`LaTeX`后是`max`，`LaTeX`支持的好处是Notebook中更直观
5. 建议参考`main.py`中最后一行，通过`safe_eval(stringify_for_sympy(e), globals().copy())`将表达式转换成可执行版。
    - 注意：使用`globals()`的地方都要小心，防止变量名冲突
6. `log`下生成的表达式有对应的源代码，可以直接`import`
from polars_ta.prefix.wq import *

from expr_codegen import codegen_exec


def _code_block_1():
    A = cs_rank(CLOSE, pct=True)


df = codegen_exec(None, _code_block_1, over_null="partition_by", function_mapping=globals())
print(df)

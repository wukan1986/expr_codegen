from analysis.reports import ipynb_to_html

# 从main中导入，可以大大减少代码
ipynb_to_html('template.ipynb',
              output='demo.html',
              no_input=True,
              no_prompt=False,
              open_browser=True,
              TEST1='123456')

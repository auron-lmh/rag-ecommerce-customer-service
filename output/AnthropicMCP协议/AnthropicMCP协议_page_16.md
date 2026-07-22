## 第16页

if not (is_python or is_js):

raise ValueError("服务器脚本必须是 .py 或 .js 文件")

# 根据脚本类型设置命令，sys.executable获取当前 python解释器的可执行文件的绝对路径

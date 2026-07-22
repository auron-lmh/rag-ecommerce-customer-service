## 第14页

Checking the Weather in Beijing

北京天气如何?

您想了解北京的天气情况。我可以帮您查询北京当前的天气，请稍等。

get_weather

根据查询，北京当前天气情况如下：

- 天气状况：晴

- 当前温度：22.94°C

- 体感温度：21.55°C

- 湿度：10%

- 风速：3.83米/秒

- 气压：1013百帕

今天北京天气晴朗，温度适宜，但空气较为干燥，湿度只有10%。如果您计划外出，建议带些水，并注意防晒和保湿。

Claude can make mistakes. Please double-check responses.

Reply to Claude...

Claude 3.7 Sonnet

# 3.3. MCP Client开发

MCP Client开发中，我们会使用到Claude模型。所以进入到创建的python环境中，安装如下依赖：

#切换python环境
conda activate python-mcp
#安装依赖 anthropic==0.50.0
pip install anthropic==0.50.0

## 3.3.1. 编写MCP Client代码

MCP Client代码中会与MCP Server进行通信，通信流程如下：

- 1) 初始化连接：MCP Client 启动后，通过指定的脚本路径（.py 或 .js）启动 MCP Server，并建立通信通道。

- 2) 工具发现：Client 向 Server 发送请求，获取可用的工具列表，包括工具名称、描述和输入参数的模式（schema）。

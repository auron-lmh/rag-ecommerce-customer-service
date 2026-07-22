## 第24页

if len(sys.argv) < 2:
    print("在参数中指定 server脚本完整路径！")
    sys.exit(1)

client = MCPClient()
try:
    await client.connect_to_server(sys.argv[1])
    await client.chat_loop()
finally:
    await client.cleanup()

if __name__ == "__main__":
    import sys

    asyncio.run(main())

以上代码注意：

- 在.env文件中配置各LLM模型的key

- available_tools中需要加上 “"type": "function"” ，这是 OpenAI 方式格式要求

以上通用MCP Client代码编写完成后，运行前将MCP Server对应的python代码路径作为参数进行设置，运行后测试如下：

已连接到服务器，可用工具: ['get_weather']

MCP 客户端已启动!

输入你的查询或 'quit' 退出。

查询: 上海天气如何？

[调用工具 get_weather，参数 {'city': 'Shanghai'}]

当前上海的天气是晴朗的，温度适宜。以下为详细信息：

- - **天气描述**: 晴

- - **当前温度**: 22.92°C

- - **体感温度**: 21.79°C

- - **最低温度**: 22.92°C

- - **最高温度**: 22.92°C

- - **湿度**: 20% （湿度较低，可能会感觉比较干燥）

- - **气压**: 1019 hPa

- - **风速**: 4 m/s

总体来说，今天的天气非常适合外出活动，但湿度较低，建议多喝水并注意保湿。如果风速较大，记得带一件轻便

# 4. Java API-MCP开发及使用

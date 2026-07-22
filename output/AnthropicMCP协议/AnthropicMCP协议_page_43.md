## 第43页

## 4.3.2. Stdio方式集成MCP Server

MCP Client通过Stadio方式连接到MCP Server需要在项目的resources/application.properties文件中配置如下内容，指定的文件中需要进行MCP Server配置。

$$
spring.ai.mcp.client.stadio.servers-configuration=classpath:/mcp-servers-config.json
$$

resources/mcp-servers-config.json文件内容如下：

运行“McpCommonClientApplication.java”后，输入如下对话内容，可以看到模型自动调用工具：

我是你的AI助手。

用户: 上海天气如何？

助手: 上海当前的天气情况如下：

- 天气描述: 晴

- 体感温度: 15.4°C

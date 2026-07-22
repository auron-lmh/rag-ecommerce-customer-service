## 第43页

//

// };

}

}

## 4.3.2. Stdio方式集成MCP Server

MCP Client通过Stadio方式连接到MCP Server需要在项目的resources/application.properties文件中配置如下内容，指定的文件中需要进行MCP Server配置。

spring.ai.mcp.client.stdio.servers-configuration=classpath:/mcp-servers-config.json

resources/mcp-servers-config.json文件内容如下：

{
  "mcpServers": {
    "spring-ai-mcp-weather": {
      "command": "D:\\Program Files\\Java\\jdk17\\jdk\\bin\\java.exe",
      "args": [
        "-Dspring.ai.mcp.server.transport=STDIO",
        "-jar",
        "D:\\idea_space\\AIModeCode\\McpServer\\target\\McpServer-0.0.1-SNAPSHOT.jar"
      ]
    }
  }
}

运行“McpCommonClientApplication.java”后，输入如下对话内容，可以看到模型自动调用工具：

我是你的AI助手。

用户: 上海天气如何？

助手: 上海当前的天气情况如下：

- - 天气描述: 晴

- - 当前温度: 16.9°C

- - 体感温度: 15.4°C

- - 最低温度: 16.9°C

- - 最高温度: 16.9°C

- - 气压: 1021 hPa

- - 湿度: 29%

- - 风速: 4.0 m/s

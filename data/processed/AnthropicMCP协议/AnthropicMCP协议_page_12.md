## 第12页

# Settings

×

General

Claude can receive information like prompts and attachments from specialized servers using Model Context Protocol. Learn more

Developer

MCP is a protocol that enables secure connections between clients, such as the Claude Desktop app, and local services.

Edit Config

Get Started

在 “claude_desktop_config.json” 文件中添加MCP Server配置，写入如下内容：

{
  "mcpServers": {
    "weather": {
      "command": "D:\\ProgramData\\Anaconda3\\envs\\python-mcp\\python.exe",
      "args": ["D:\\PyCharmSpace\\MCPCode\\mcp_server_client\\server_weather.py"]
    }
  }
}

以上命令解释如下：

- mcpServers:这是一个顶层字段，表示你要在 Claude Desktop 中注册的一组 MCP 服务器，里面可以配置多个。

- weather:用户自定义的 MCP 服务器的名称（对应代码中mcp = FastMCP("weather")），可以起任何名字，比如 "weather_server"、"data_tools" 等。

- command:启动Server的命令名称，用于指定你用哪个命令来运行你的工具服务。

- args:启动命令时用到的参数列表，是一个数组，每一项就是命令行的一部分参数。

以上配置完成后，重启Claude Desktop，然后在Claude Desktop主页面可以看到发现Server定义的工具：

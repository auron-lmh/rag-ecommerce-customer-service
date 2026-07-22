## 第34页

# What's new, zs?

How can I help you today?

## Settings

General

Developer

Claude can receive information like prompts and attachments from specialized servers using Model Context Protocol. Learn more

MCP is a protocol that enables secure connections between clients, such as the Claude Desktop app, and local services.

Edit Config

Get Started

在“claude_desktop_config.json”文件中添加MCP Server配置，写入如下内容：

$$
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
$$

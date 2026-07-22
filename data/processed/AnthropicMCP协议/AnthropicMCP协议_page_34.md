## 第34页

File >

New Conversation Ctrl+N

Edit >

Settings... Ctrl+逗号

View >

Close Ctrl+W

Help >

Exit

Free plan · Upgrade

# What's new, zs?

How can I help you today?

Claude 3.7 Sonnet v

Write

Learn

Code

Life stuff

Claude's choice

## Settings

## General

Claude can receive information like prompts and attachments from specialized servers using Model Context Protocol. Learn more

## Developer

MCP is a protocol that enables secure connections between clients, such as the Claude Desktop app, and local services.

Edit Config

Get Started

在“claude_desktop_config.json” 文件中添加MCP Server配置，写入如下内容：

{

"mcpServers": {

"spring-ai-mcp-weather": {

"command": "D:\\Program Files\\Java\\jdk17\\jdk\\bin\\java.exe",

"args": [

"-Dspring.ai.mcp.server.transport=STDIO",

"-jar",

"D:\\idea_space\\AIModeCode\\McpServer\\target\\McpServer-0.0.1-SNAPSHOT.jar"

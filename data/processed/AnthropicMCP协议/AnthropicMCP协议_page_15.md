## 第15页

- 3) 处理用户查询：用户输入查询后，Client 将其发送给 LLM（如 Claude），并附带可用工具的信息。

- 4) 工具调用：如果 LLM 决定使用某个工具，Client 会根据 LLM 的指示，调用对应的工具，并将结果返回给 LLM。

- 5) 生成响应：LLM 根据工具返回的数据，生成最终的响应，并由 Client 显示给用户。

MCP Client 代码如下：

import asyncio

import os

from typing import Optional

from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters

from mcp.client.stdio import stdio_client

from dotenv import load_dotenv

from anthropic import Anthropic

# 导入 dotenv 模块，加载 .env 文件中的环境变量

load_dotenv()

# 获取环境变量中的 ANTHROPIC_API_KEY

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# 定义 MCPClient 类

class MCPClient:

def __init__(self):

# 初始化会话 session 对象

self.session: Optional[ClientSession] = None

# 创建 exit_stack 用于管理异步上下文

self.exit_stack = AsyncExitStack()

# 使用 API 密钥初始化 Anthropic 客户端

self.anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)

# 定义异步方法，连接到 MCP 服务器

async def connect_to_server(self, server_script_path: str):

"""连接到 MCP 服务器

参数：

server_script_path: 服务器脚本路径 (.py 或 .js)

"""

# 判断服务器脚本是否为 Python 或 JavaScript 文件

is_python = server_script_path.endswith('.py')

is_js = server_script_path.endswith('.js')

# 如果不是 Python 或 JavaScript 文件，抛出异常

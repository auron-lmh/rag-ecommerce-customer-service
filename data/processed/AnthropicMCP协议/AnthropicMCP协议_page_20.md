## 第20页

- - 天气状况:晴天

- - 当前温度:23.94°C

- - 体感温度:22.73°C

- - 温度范围:23.94°C - 23.94°C

- - 气压:1011 hPa

- - 湿度:13%

- - 风速:3.9 m/s

总的来说,北京现在属于晴朗干燥的天气,温度适中,风速较轻,总体舒适宜人。这样的天气非常适合户外活动和旅游观光

## 3.4. LLM通用MCP Client开发

以上MCP Client使用Claude模型调用MCP Server工具，如果客户端使用各类LLM大模型使用MCP Server工具可以通过Open AI 类实现。只要LLM支持OpenAI方式调用就可以使用如下通用Client调用MCP Sever工具。

进入到创建的python环境中，安装如下依赖：

#切换python环境

conda activate python-mcp

#安装依赖 openai==1.75.0

pip install openai

通用MCP Client代码如下：

# 所有LLM 通用的 Client ,通过Open API 方式连接LLM

import asyncio

import os

from typing import Optional

from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters

from mcp.client.stdio import stdio_client

from openai import OpenAI

from dotenv import load_dotenv

from anthropic import Anthropic

# 加载 .env 文件中的环境变量

load_dotenv()

# 获取环境变量

# Claude

# LLM_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# LLM_URL = "https://api.anthropic.com/v1/"

# LLM_MODEL = "claude-3-haiku-20240307"

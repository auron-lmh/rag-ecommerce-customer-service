## 第9页

## 3.2.1. 编写MCP Server代码

下面我们创建MCP Server代码，在该代码中创建一个get_weather()工具，该工具通过OpenWeather可以查询某个城市天气情况。具体代码如下：

from typing import Any

import httpx

from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP

import os

# 初始化 FastMCP server

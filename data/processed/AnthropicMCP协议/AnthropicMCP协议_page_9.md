## 第9页

# 3.2.1. 编写MCP Server代码

下面我们创建MCP Server代码，在该代码中创建一个get_weather()工具，该工具通过OpenWeather可以查询某个城市天气情况。具体代码如下：

from typing import Any

import httpx

from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP

import os

# 初始化 FastMCP server

mcp = FastMCP("weather")

# 加载 .env 文件中的环境变量

load_dotenv()

# 获取环境变量

OPEN_WEATHER_API_KEY = os.getenv("OPEN_WEATHER_API_KEY")

async def make_openweather_request(url: str) -> dict[str, Any] | None:

"""向 OpenWeather API 发出 GET 请求，处理错误并返回 JSON 响应。"""

async with httpx.AsyncClient() as client:

try:

response = await client.get(url, timeout=30.0)

response.raise_for_status()

return response.json()

except Exception:

return None

@mcp.tool()

async def get_weather(city: str) -> str:

"""

获取指定城市的当前天气情况。

Args:

city: 城市名称，必须是英文格式，比如 London 或 Beijing

Returns:

格式化后的天气报告字符串。

"""

base_url = "http://api.openweathermap.org/data/2.5/weather"

params = {

"q": city,

"appid": OPEN_WEATHER_API_KEY,

"units": "metric",

"lang": "zh_cn"

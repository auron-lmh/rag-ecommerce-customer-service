## 第10页

data = await make_openweather_request(url)

if not data or data.get("cod") == 404:

return "未找到该城市的天气信息。"

try:

main = data["main"]

weather = data["weather"][0]

wind = data["wind"]

# 提取天气主要信息

## 第10页

}

query = "&".join(f"{k}={v}" for k, v in params.items())

url = f"{base_url}?{query}"

data = await make_openweather_request(url)

print(f"data:{data}")

if not data or data.get("cod") == 404:

return "未找到该城市的天气信息。"

try:

main = data["main"]

weather = data["weather"][0]

wind = data["wind"]

# 提取天气主要信息

weather_description = weather.get("description", "无描述") #天气描述

temperature = main.get("temp") #当前温度

feels_like = main.get("feels_like") #体感温度

temp_min = main.get("temp_min") #最低温度

temp_max = main.get("temp_max") #最高温度

pressure = main.get("pressure") #气压

humidity = main.get("humidity") #湿度

sea_level = main.get("sea_level", "未知") #海平面气压

grnd_level = main.get("grnd_level", "未知") #地面气压

wind_speed = wind.get("speed") #风速

# 生成天气报告

weather_report = f"""

城市: {data.get('name', '未知')}

天气描述: {weather_description.capitalize()}

当前温度: {temperature}°C

体感温度: {feels_like}°C

最低温度: {temp_min}°C

最高温度: {temp_max}°C

气压: {pressure} hPa

湿度: {humidity}%

海平面气压: {sea_level} hPa

地面气压: {grnd_level} hPa

风速: {wind_speed} m/s

""".strip()

return weather_report

except Exception as e:

return f"处理天气数据时出错：{e}"

if __name__ == "__main__":

# 测试 get_weather方法

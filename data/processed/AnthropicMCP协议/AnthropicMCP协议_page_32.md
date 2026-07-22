## 第32页

JSONObject wind = data.getJSONObject("wind");

String weatherDescription = weather.optString("description", "无描述");

double temperature = main.optDouble("temp", Double.NaN);

double feelsLike = main.optDouble("feels_like", Double.NaN);

double tempMin = main.optDouble("temp_min", Double.NaN);

double tempMax = main.optDouble("temp_max", Double.NaN);

int pressure = main.optInt("pressure", 0);

int humidity = main.optInt("humidity", 0);

double windSpeed = wind.optDouble("speed", Double.NaN);

return String.format("""

城市: %s

天气描述: %s

当前温度: %.1f°C

体感温度: %.1f°C

最低温度: %.1f°C

最高温度: %.1f°C

气压: %d hPa

湿度: %d%%

风速: %.1f m/s

""","

data.optString("name", city),

weatherDescription,

temperature,

feelsLike,

tempMin,

tempMax,

pressure,

humidity,

windSpeed

);

} catch (Exception e) {

return "获取天气信息时出错: " + e.getMessage();

}

}

public static void main(String[] args) {

//测试方法

WeatherService client = new WeatherService();

String beijing = client.getWeather("Beijing");

System.out.println(beijing);

}

}

注意如下两点：

- • 如上代码中使用“@Tool”标记了方法getWeather为工具。

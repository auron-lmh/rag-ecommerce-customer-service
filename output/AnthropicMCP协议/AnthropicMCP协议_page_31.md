## 第31页

private static final Logger logger = LoggerFactory.getLogger(WeatherService.class);

private static final String BASE_URL = "http://api.openweathermap.org/data/2.5/weather";

private String OPEN_WEATHER_API_KEY;

/**

* 根据城市名称获取天气信息（使用 OpenWeatherMap）

* @param city 城市名称，如 "Beijing"

* @return 天气信息文本

*/

@Tool(description = "获取指定城市的当前天气情况，格式化后的天气报告字符串。")

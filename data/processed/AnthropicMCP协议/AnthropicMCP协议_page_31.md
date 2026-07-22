## 第31页

private static final Logger logger = LoggerFactory.getLogger(WeatherService.class);

private static final String BASE_URL = "http://api.openweathermap.org/data/2.5/weather";

@Value("${OPEN_WEATHER_API_KEY}")

private String OPEN_WEATHER_API_KEY;

/**

* 根据城市名称获取天气信息（使用 OpenWeatherMap ）

* @param city 城市名称，如 "Beijing"

* @return 天气信息文本

*/

@Tool(description = "获取指定城市的当前天气情况，格式化后的天气报告字符串。")

public String getWeather(@ToolParam(description = "城市名称，必须是英文格式，比如 London 或 Beijin

logger.info("====== 调用了getWeather工具 ======");

try {

String charset = "UTF-8";

String query = String.format(

"q=%s&appid=%s&units=metric&lang=zh_cn",

URLEncoder.encode(city, charset),

URLEncoder.encode(OPEN_WEATHER_API_KEY, charset)

);

URL url = new URL(BASE_URL + "?" + query);

logger.info("====== 访问URL： ======"+url.toString());

HttpURLConnection connection = (HttpURLConnection) url.openConnection();

connection.setRequestMethod("GET");

BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStrea

StringBuilder response = new StringBuilder();

String line;

while ((line = reader.readLine()) != null) {

response.append(line);

}

reader.close();

JSONObject data = new JSONObject(response.toString());

if (data.getInt("cod") == 404) {

return "未找到该城市的天气信息。";

}

JSONObject main = data.getJSONObject("main");

JSONArray weatherArray = data.getJSONArray("weather");

JSONObject weather = weatherArray.getJSONObject(0);

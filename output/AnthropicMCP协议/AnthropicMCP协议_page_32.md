## 第32页

JSONObject wind = data.getJSONObject("wind");

String weatherDescription = weather.optString("description", "无描述");

double temperature = main.optDouble("temp", Double.NaN);

double feelsLike = main.optDouble("feels_like", Double.NaN);

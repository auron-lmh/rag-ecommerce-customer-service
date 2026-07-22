## 第36页

Checking the Weather in Shenzhen

深圳天气如何?

我可以帮您查询深圳的天气情况。请稍等，我会获取最新的天气信息。

getWeather

Request

{

`city`: `Shenzhen`

}

Response

“城市：Shenzhen\n天气描述：阴，多云\n当前温度：26.0°C\n体感温度：26.0°C\n最低温度：24.9°C\n最高温度：26.2°C\n气压：1011 hPa\n湿度：93%\n风速：2.4 m/s\n”

深圳当前天气情况如下：

- 天气状况：阴，多云

- 当前温度：26.0°C

- 体感温度：26.0°C

- 温度范围：24.9°C 至 26.2°C

Reply to Claude...

Claude 3.7 Sonnet

可以在MCP Server端配置的日志路径中找到对应的日志，查看到日志中会有相应工具调用：

INFO [McpSever] [boundedElastic-1] com.example.mcpserver.WeatherService : ====== 调用了getWea

INFO [McpSever] [boundedElastic-1] com.example.mcpserver.WeatherService : ====== 访问URL： ==

## 4.3. MCP Client开发

## 4.3.1. 编写MCP Client代码

按照如下步骤创建MCP Client的SpringBoot项目。该MCP Client 项目中可以使用不同的LLM模型，只需要在对应配置文件中引入不同的模型对应的apikey及相关依赖即可。

## 1) 创建SpringBoot项目

SpringBoot项目命名为McpCommonClient，设置使用的JDK为17版本。

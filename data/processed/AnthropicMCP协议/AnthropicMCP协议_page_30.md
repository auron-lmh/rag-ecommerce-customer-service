## 第30页

#配置应用监听的端口为 8086

server.port=8086

#禁用 Spring Boot 启动时的横幅 ( Banner ) 显示，对于使用 STDIO 传输的 MCP 服务器，禁用横幅有助于避免输

spring.main.banner-mode=off

#如下参数启用并设置为空，将禁用控制台日志输出格式，减少输出干扰

logging.pattern.console=

#配置日志文件的输出路径，将日志写入指定的文件中

logging.file.name=./McpServer/model-context-protocol/mcp-weather-stdio-server.log

#访问 OpenWeather API 的密钥

OPEN_WEATHER_API_KEY=your_open_weather_api_key

#设置日志的根级别为 INFO

#logging.level.root=INFO

特别注意：以上配置中logging.file.name指定了MCP Server运行过程中日志输出的位置，可以

通过该日志查看Server端运行情况（如：工具是否被调用）。

## 4) 创建 WeatherService.java构建查询天气工具

package com.example.mcpserver;

import java.io.BufferedReader;

import java.io.InputStreamReader;

import java.net.HttpURLConnection;

import java.net.URL;

import java.net.URLEncoder;

import org.json.JSONArray;

import org.json.JSONObject;

import org.springframework.ai.tool.annotation.Tool;

import org.springframework.ai.tool.annotation.ToolParam;

import org.springframework.beans.factory.annotation.Value;

import org.springframework.stereotype.Component;

import org.springframework.stereotype.Service;

import org.slf4j.Logger;

import org.slf4j.LoggerFactory;

/**

* 天气服务类，用于获取指定城市的天气信息

* @Service 标记为 Spring 服务层组件

*/

@Service

public class WeatherService {

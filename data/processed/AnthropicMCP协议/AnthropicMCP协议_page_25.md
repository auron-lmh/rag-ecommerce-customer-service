## 第25页

要使用 Java API 开发 MCP（Model Context Protocol）服务器和客户端，可以借助 Spring

Boot 和 Spring AI 提供的工具，快速构建MCP Server和MCP Client。

Spring AI MCP地址：https://docs.spring.io/spring-ai/reference/api/mcp/mcp-overview.

html

## 4.1. Java环境准备

Java API 开发MCP要求使用JDK17及以上版本、SpringBoot 3.3.x及以上版本、Maven3.6及以上版本。

这里在Windows中下载并安装JDK17。使用如下链接下载JDK 17后进行安装，这里安装在D盘“D:\Program Files\Java\jdk17\jdk”中，不需要配置环境变量，只需要在相应的SpringBoot项目中设置使用的JDK17版本即可。

JDK17下载地址：https://www.oracle.com/cn/java/technologies/downloads/#java17

## 4.2. MCP Server开发

## 4.2.1. 编写MCP Server代码

下面我们创建MCP Server代码，在该代码中创建一个getWeather工具，该工具通过OpenWeather可以查询某个城市天气情况。按照如下步骤创建SpringBoot项目、编写具体代码及配置。

- 1) 创建SpringBoot项目

SpringBoot项目命名为McpServer，设置使用的JDK为17版本。

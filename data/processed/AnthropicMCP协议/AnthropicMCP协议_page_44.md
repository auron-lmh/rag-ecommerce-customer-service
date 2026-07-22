## 第44页

可以在MCP Server端配置的日志路径中找到对应的日志，查看到日志中会有相应工具调用：

INFO [McpSever] [boundedElastic-1] com.example.mcpserver.WeatherService : ====== 调用了getWea

INFO [McpSever] [boundedElastic-1] com.example.mcpserver.WeatherService : ====== 访问URL : ==

## 4.4. Client通过SSE方式连接Server

按照如下步骤实现MCP Client通过SSE方式连接MCP Server。

- 1) MCP Client中设置resources/application.properties配置文件

该配置文件中加入如下内容：

#SSE 模式，配置名为 server1 的 MCP 服务器连接，远程连接到指定的服务器地址

spring.ai.mcp.client.sse.connections.server1=http://localhost:8086

- 2) MCP Server端修改pom.xml

在pom.xml中导入“spring-ai-starter-mcp-server-webflux”依赖，该依赖支持SSE传输，并注释掉“spring-ai-starter-mcp-server”和“spring-web”依赖。

<!-- 只支持 STDIO 传输，使用如下两个依赖 -->

<!-- <dependency>-->

<!-- <groupId>org.springframework.ai</groupId>-->

<!-- <artifactId>spring-ai-starter-mcp-server</artifactId>-->

<!-- </dependency>-->

<!-- <dependency>-->

<!-- <groupId>org.springframework</groupId>-->

<!-- <artifactId>spring-web</artifactId>-->

<!-- </dependency>-->

<!-- 支持 SSE 传输，使用如下依赖 -->

<dependency>

<groupId>org.springframework.ai</groupId>

<artifactId>spring-ai-starter-mcp-server-webflux</artifactId>

</dependency>

- 3) 启动MCP Server和MCP Client对应的SpringBoot项目

MCP Server和MCP Client 两个SpringBoot项目启动后，直接在MCP Client端输入如下内容，可以通过日志文件看到工具被调用：

我是你的AI助手。

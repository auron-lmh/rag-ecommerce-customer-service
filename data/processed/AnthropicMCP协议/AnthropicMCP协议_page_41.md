## 第41页

#使用 通义千问 LLM，需要在pom.xml中引入对应依赖

spring.ai.dashscope.api-key=your_dashscope_api_key

spring.ai.dashscope.chat.options.model=qwen-plus

#STDIO 模式，指定 MCP 客户端的服务器配置文件路径

spring.ai.mcp.client.stdio.servers-configuration=classpath:/mcp-servers-config.json

#SSE 模式，配置名为 server1 的 MCP 服务器连接，远程连接到指定的服务器地址

#spring.ai.mcp.client.sse.connections.server1=http://localhost:8086

## 4) 主应用类中构建聊天客户端

主应用类为McpCommonClientApplication.java，内容如下：

package com.example.mcpcommonclient;

import io.modelcontextprotocol.client.McpSyncClient;

import org.springframework.ai.chat.client.ChatClient;

import org.springframework.ai.chat.client.advisor.MessageChatMemoryAdvisor;

import org.springframework.ai.chat.memory.InMemoryChatMemory;

import org.springframework.ai.mcp.SyncMcpToolCallbackProvider;

import org.springframework.boot.CommandLineRunner;

import org.springframework.boot.SpringApplication;

import org.springframework.boot.autoconfigure.SpringBootApplication;

import org.springframework.context.annotation.Bean;

import java.util.List;

import java.util.Scanner;

@SpringBootApplication

public class McpCommonClientApplication {

public static void main(String[] args) {

SpringApplication.run(McpCommonClientApplication.class, args);

}

/**

* @Bean 注解用于将方法的返回值作为 Spring Bean 注册到 Spring 容器中。

* Spring 容器在启动过程中会扫描并执行所有带有 @Bean 注解的方法，以将其返回的对象注册到应用上下

*

* CommandLineRunner：Spring Boot 提供的接口，实现了 CommandLineRunner 接口的 Bean 会在 Sprin

* chatClientBuilder：ChatClient.Builder 用于构建聊天客户端的构建器

* mcpSyncClients：SpringAI 根据 spring-ai-starter-mcp-client 依赖注入的 McpSyncClient 列表，用于调用

*

*/

@Bean

public CommandLineRunner chatbot(ChatClient.Builder chatClientBuilder, List<McpSyncClient> mcpSy

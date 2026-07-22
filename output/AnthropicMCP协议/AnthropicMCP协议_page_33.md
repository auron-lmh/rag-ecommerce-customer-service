## 第33页

• 代码中不要System输出任何内容，会影响返回结果的处理。

## 5) 主应用类中加入工具

主应用类为McpServerApplication.java，内容如下：

package com.example.mcpserver;

import org.springframework.ai.tool.ToolCallbackProvider;

import org.springframework.ai.tool.method.MethodToolCallbackProvider;

import org.springframework.boot.SpringApplication;

import org.springframework.boot.autoconfigure.SpringBootApplication;

import org.springframework.context.annotation.Bean;

@SpringBootApplication

SpringApplication.run(McpServerApplication.class, args);

/**

* @Bean 注解用于将方法的返回值作为 Spring Bean 注册到 Spring 容器中。

* Spring 容器在启动过程中会扫描并执行所有带有 @Bean 注解的方法，以将其返回的对象注册到应用上下文中。

*

* ToolCallbackProvider 接口:Spring AI 提供的接口，其实现类负责将带有 @Tool 注解的方法注册为可供 AI 调用的工具。

* /

@Bean

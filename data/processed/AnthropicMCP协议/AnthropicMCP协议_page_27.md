## 第27页

New Module

Spring Boot: 3.4.4

Download pre-built shared indexes for JDK and Maven libraries

Dependencies:

Developer Tools

GraalVM Native Support

GraphQL DGS Code Generation

Spring Boot DevTools

Lombok

Spring Configuration Processor

Docker Compose Support

Spring Modulith

Web

Template Engines

Security

SQL

NoSQL

Messaging

I/O

Ops

Observability

Testing

GraalVM Native Support

Support for compiling Spring applications to native executables using the GraalVM native-image compiler.

Added dependencies:

No dependencies added

Previous

Create

Cancel

## 2) 在项目中加入如下Maven依赖

<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-
xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0
<modelVersion>4.0.0</modelVersion>
<parent>
<groupId>org.springframework.boot</groupId>
<artifactId>spring-boot-starter-parent</artifactId>
<version>3.4.4</version>
<relativePath/> <!-- lookup parent from repository -->
</parent>
<groupId>com.example</groupId>
<artifactId>McpServer</artifactId>
<version>0.0.1-SNAPSHOT</version>
<name>McpServer</name>
<description>McpServer</description>

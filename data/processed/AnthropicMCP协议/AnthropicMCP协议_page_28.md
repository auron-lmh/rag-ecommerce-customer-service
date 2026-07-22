## 第28页

<dependencyManagement>

<dependencies>

<dependency>

<groupId>org.springframework.ai</groupId>

<artifactId>spring-ai-bom</artifactId>

<version>1.0.0-M7</version>

<type>pom</type>

<scope>import</scope>

</dependency>

</dependencies>

</dependencyManagement>

<dependencies>

<!-- 只支持 STDIO 传输，使用如下两个依赖 -->

<dependency>

<groupId>org.springframework.ai</groupId>

<artifactId>spring-ai-starter-mcp-server</artifactId>

</dependency>

<dependency>

<groupId>org.springframework</groupId>

<artifactId>spring-web</artifactId>

</dependency>

<!-- 支持 SSE 传输，使用如下依赖 -->

<!--    <dependency>-->

<!--        <groupId>org.springframework.ai</groupId>-->

<!--        <artifactId>spring-ai-starter-mcp-server-webflux</artifactId>-->

<!--    </dependency>-->

<!-- 依赖的json 包-->

<dependency>

<groupId>org.json</groupId>

<artifactId>json</artifactId>

<version>20210307</version>

</dependency>

</dependencies>

<build>

<plugins>

<plugin>

<groupId>org.springframework.boot</groupId>

<artifactId>spring-boot-maven-plugin</artifactId>

<version>3.4.4</version>

<configuration>

<mainClass>com.example.mcpserver.McpServerApplication</mainClass>

</configuration>

<executions>

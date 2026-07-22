## 第39页

<artifactId>spring-ai-bom</artifactId>

<version>1.0.0-M7</version>

<type>pom</type>

<scope>import</scope>

</dependency>

</dependencies>

</dependencyManagement>

<dependencies>

<dependency>

<groupId>org.springframework.ai</groupId>

<artifactId>spring-ai-starter-mcp-client</artifactId>

</dependency>

<!-- 导入 Spring AI - Anthropic 依赖-->

<!--    <dependency>-->

<!--        <groupId>org.springframework.ai</groupId>-->

<!--        <artifactId>spring-ai-starter-model-anthropic</artifactId>-->

<!--    </dependency>-->

<!-- 导入 Spring AI - OpenAI 依赖-->

<!--    <dependency>-->

<!--        <groupId>org.springframework.ai</groupId>-->

<!--        <artifactId>spring-ai-starter-model-openai</artifactId>-->

<!--    </dependency>-->

<!-- 导入Spring AI Alibaba - 通义千问依赖 -->

<dependency>

<groupId>com.alibaba.cloud.ai</groupId>

<artifactId>spring-ai-alibaba-starter</artifactId>

<version>1.0.0-M6.1</version>

</dependency>

</dependencies>

<build>

<plugins>

<plugin>

<groupId>org.springframework.boot</groupId>

<artifactId>spring-boot-maven-plugin</artifactId>

</plugin>

</plugins>

</build>

<repositories>

<repository>

<name>Central Portal Snapshots</name>

<id>central-portal-snapshots</id>

## 第40页

<url>https://central.sonatype.com/repository/maven-snapshots/</url>

<releases>

<enabled>false</enabled>

</releases>

<snapshots>

<enabled>true</enabled>

</snapshots>

</repository>

<repository>

<id>spring-milestones</id>

<name>Spring Milestones</name>

<url>https://repo.spring.io/milestone</url>

<snapshots>

<enabled>false</enabled>

</snapshots>

</repository>

<repository>

<id>spring-snapshots</id>

<name>Spring Snapshots</name>

<url>https://repo.spring.io/snapshot</url>

<releases>

<enabled>false</enabled>

</releases>

</repository>

</repositories>

</project>

注意：以上依赖中使用哪个LLM ，那么引入对应的依赖。支持的模型以及引入的包查看：https://docs.spring.io/spring-ai/reference/api/chat/openai-chat.html。

## 3) 配置resources/application.properties

#设置应用程序的名称

spring.application.name=McpCommonClient

#指定应用类型为非 Web 应用，适用于命令行工具、批处理任务或仅作为客户端运行的场景

spring.main.web-application-type=none

#使用 Claude LLM，需要在pom.xml中引入对应依赖

#spring.ai.anthropic.api-key=your_anthropic_api_key

#spring.ai.anthropic.chat.options.model=claude-3-haiku-20240307

#使用 Deepseek LLM，需要在pom.xml中引入对应依赖

#spring.ai.openai.api-key=your_deepseek_api_key

#spring.ai.openai.base-url=https://api.deepseek.com

#spring.ai.openai.chat.options.model=deepseek-chat

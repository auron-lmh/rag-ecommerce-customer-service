## 第29页

<execution>

<goals>

<goal>repackage</goal>

</goals>

</execution>

</executions>

</plugin>

</plugins>

</build>

<repositories>

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

<repository>

<id>central-portal-snapshots</id>

<name>Central Portal Snapshots</name>

<url>https://central.sonatype.com/repository/maven-snapshots/</url>

<releases>

<enabled>false</enabled>

</releases>

<snapshots>

<enabled>true</enabled>

</snapshots>

</repository>

</repositories>

</project>

## 3) 配置resources/application.properties

#设置 Spring Boot 应用的名称为 McpSever

spring.application.name=McpSever

#指定 MCP 服务器的名称为 spring-ai-mcp-weather

spring.ai.mcp.server.name=spring-ai-mcp-weather

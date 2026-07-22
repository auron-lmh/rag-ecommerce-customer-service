## 第14页

## 3.2. JDBC Connector

- https://nightlies.apache.org/flink/flink-docs-release-1.15/docs/connectors/table/jdbc/

- JDBC 连接器允许使用 JDBC 驱动向任意类型的关系型数据库读取或者写入数据。

- 如果在 DDL 中定义了主键，JDBC sink 将以 upsert 模式与外部系统交换 UPDATE/DELETE 消息；否则，它将以 append 模式与外部系统交换消息且不支持消费 UPDATE/DELETE 消息。

- maven依赖

<dependency>

<groupId>org.apache.flink</groupId>

<artifactId>flink-connector-jdbc</artifactId>

<version>1.15.2</version>

</dependency>

<dependency>

<artifactId>mysql-connector-java</artifactId>

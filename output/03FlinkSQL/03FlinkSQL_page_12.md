## 第12页

## 3. FlinkSQL Connector

- Connector 通常是用于对接外部存储建表（源表或目标表）时的映射器、桥接器

- Connector 本质上是对 Flink 的 Table Source /Table Sink 算子的封装;

- 连接器使用的核心要素

- 导入连接器 jar 包依赖

- 指定连接器类型名

- 指定连接器所需的参数（不同连接器有不同的参数配置需求）

- 获取连接器所提供的元数据

- FlinkSQL目前支持的 Format

https://nightlies.apache.org/flink/flink-docs-release-1.15/zh/docs/connectors/table/overview/

| Name | Version | Source | Sink |
|---|---|---|---|
| Filesystem |  | Bounded and Unbounded Scan, Lookup | Streaming Sink, Batch Sink |
| Elasticsearch | 6 x &amp; 7 x | Not supported | Streaming Sink, Batch Sink |
| Apache Kafka | 0.10+ | Unbounded Scan | Streaming Sink, Batch Sink |
| Amazon Kinesis Data Streams |  | Unbounded Scan | Streaming Sink |
| JDBC |  | Bounded Scan, Lookup | Streaming Sink, Batch Sink |
| Apache HBase | 1.4 x &amp; 2.2 x | Bounded Scan, Lookup | Streaming Sink, Batch Sink |
| Apache Hive | Supported Versions | Unbounded Scan, Bounded Scan, Lookup | Streaming Sink, Batch Sink |

## 3.1. Kafka Connector

- https://nightlies.apache.org/flink/flink-docs-release-1.15/zh/docs/connectors/table/kafka/

- Kafka 连接器提供从 Kafka topic 中消费和写入数据的能力。

- maven依赖

$$
<dependency>
<groupId>org.apache.flink</groupId>
<artifactId>flink-connector-kafka</artifactId>
<version>1.15.2</version>
</dependency>
$$

- 代码实现

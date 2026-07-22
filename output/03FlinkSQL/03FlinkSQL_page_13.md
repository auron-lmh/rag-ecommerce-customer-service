## 第13页

$$
CREATE TABLE flink_kafka_source (\n +
$$

$$
'deptno' : INT,\n +
$$

$$
'dname' STRING,\n +
$$

$$
'loc' STRING\n +
$$

$$
) WITH (\n +
$$

$$
'connector' = 'kafka', \n +
$$

$$
'topic' = 'topic_kafka_source',\n +
$$

$$
'properties.bootstrap.servers' =
$$

$$
'node01:9092,node02:9092,node03:9092',\n +
$$

$$
) ;
$$

## • 可用元数据

| 键 | 数据类型 | 描述 | R/W |
|---|---|---|---|
| topic | STRING NOT NULL | Kafka 记录的 Topic 名。 | R |
| partition | INT NOT NULL | Kafka 记录的 partition ID。 | R |
| headers | MAP NOT NULL | 二进制 Map 类型的 Kafka 记录头（Header）。 | R/W |
| Leader-epoch | INT NULL | Kafka 记录的 Leader epoch（如果可用）， | R |
| offset | BIGINT NOT NULL | Kafka 记录在 partition 中的 offset, | R |
| timestamp | TIMESTAMP_LTZ(3) NOT NULL | Kafka 记录的时间戳。 | R/W |
| timestamp-type | STRING NOT NULL | Kafka 记录的时间戳类型。可能的类型有“NoTimestampType”，“CreateTime”（会在写入元数据时设置），或“LogAppendTime”。 | R |

## • 配置参数

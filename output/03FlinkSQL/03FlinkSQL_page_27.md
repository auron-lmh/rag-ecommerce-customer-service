## 第27页

## 5. FlinkSQL Format

- connector 连接器: 对接外部存储时, 根据外部存储中的数据格式不同, 需要用到不同的 format 组件;

- format 组件: 作用就是告诉连接器, 如何解析外部存储中的数据及映射到表 schema;

- format 组件的使用要点

- 导入 format 组件的 jar 包依赖

- 指定 format 组件的名称

- 设置 format 组件所需的参数 (不同 format 组件有不同的参数配置需求)

- FlinkSQL目前支持的 Format

https://nightlies.apache.org/flink/flink-docs-release-1.15/docs/connectors/table/formats/overview/

| Formats | Supported Connectors |
|---|---|
| CSV | Apache Kafka, Upsert Kafka, Amazon Kinesis Data Streams, Filesystem |
| JSON | Apache Kafka, Upsert Kafka, Amazon Kinesis Data Streams, Filesystem, Elasticsearch |
| Apache Avro | Apache Kafka, Upsert Kafka, Amazon Kinesis Data Streams, Filesystem |
| Confluent Avro | Apache Kafka, Upsert Kafka |
| Debezium CDC | Apache Kafka, Filesystem |
| Canal CDC | Apache Kafka, Filesystem |
| Maxwell CDC | Apache Kafka, Filesystem |
| Ogg CDC | Apache Kafka, Filesystem |
| Apache Parquet | Filsystem |
| Apache ORC | Filsystem |
| Raw | Apache Kafka, Upsert Kafka, Amazon Kinesis Data Streams, Filesystem |

$$
+ '' 'topic' = 'mytopic',
+ '' 'properties.bootstrap.servers' = 'hdp01:9092', ''
+ '' 'properties.group.id' = 'g1',
''
+ '' 'scan.startup.mode' = 'earliest-offset',
+ '' 'format' = 'json',
''
+ '' 'json.fail-on-missing-field' = 'false',
''
+ '' 'json.ignore-parse-errors' = 'true'
+ '' )
);
tenv.executeSql("desc t_person").print();
tenv.executeSql("select * from t_person where id>2").print();
$$

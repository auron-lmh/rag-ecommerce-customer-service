## 第20页

用表来类比，changelog 流中的数据记录被解释为 UPSERT，也称为 INSERT/UPDATE，因为任何具有相同 key 的现有行都被覆盖。

- 另外value 为空的消息将会被视作为 DELETE 消息。

作为 sink

upsert-kafka Connector会消费一个changelog流。

将INSERT / UPDATE_AFTER数据作为正常的Kafka消息值写入(即INSERT和UPDATE操作，都会进行正常写入

如果是更新，则同一个key会存储多条数据，但在读取该表数据时，只保留最后一次更新的值

并将 DELETE 数据以 value 为空的 Kafka 消息写入

Flink 将根据主键列的值对数据进行分区，从而保证主键上的消息有序，因此同一主键上的更新/删除消息将落在同一分区中。

代码实现

CREATE TABLE pageviews_per_region (

userid STRING,

pv BIGINT,

uv BIGINT,

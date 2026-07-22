## 第21页

○

## 3.5. FileSystem Connector

• https://nightlies.apache.org/flink/flink-docs-release-1.15/zh/docs/connectors/table/filesystem/

m/

| 参数 | 是否必选 | 默认值 | 数据类型 | 描述 |
|---|---|---|---|---|
| connector | 必选 | (none) | String | 指定要使用的连接器，Upsert Kafka 连接器使用：'upsert-kafka'。 |
| topic | 必选 | (none) | String | 用于读取和写的 Kafka topic 名称。 |
| properties.bootstrap.servers | 必选 | (none) | String | 以逗号分隔的 Kafka brokers 列表。 |
| properties.* | 可选 | (none) | String | 该选项可以传递任意的 Kafka 参数。选项的后缀名必须匹配定义在 Kafka 参数文档中的参数名。Flink 会自动移除选项名中的 'properties.' 前缀，并将转换后的键名以及值传入 KafkaClient。例如，你可以通过 'properties.allow.auto.create.topics' = 'false' 来禁止自动创建 topic。但是，某些选项，例如 'key.deserializer' 和 'value.deserializer' 是不允许通过该方式传递参数，因为 Flink 会重写与这些参数的值。 |
| key.format | 必选 | (none) | String | 用于对 Kafka 消息中 key 部分序列化和反序列化的格式。key 字段由 PRIMARY KEY 语法指定。支持的格式包括 'csv'、'json'、'avro'。请参考格式页面以获取更多详细信息和格式参数。 |
| key.fields-prefix | optional | (none) | String | Defines a custom prefix for all fields of the key format to avoid name clashes with fields of the value format. By default, the prefix is empty. If a custom prefix is defined, both the table schema and 'key.fields' will work with prefixed names. When constructing the data type of the key format, the prefix will be removed and the non-prefixed names will be used within the key format. Please note that this option requires that 'value.fields.include' must be set to 'EXCEPT_KEY' . |
| value.format | 必选 | (none) | String | 用于对 Kafka 消息中 value 部分序列化和反序列化的格式。支持的格式包括 'csv'、'json'、'avro'。请参考格式页面以获取更多详细信息和格式参数。 |
| value.fields.include | 必选 | 'ALL' | String | 控制哪些字段应该出现在 value 中。可取值：ALL：消息的 value 部分将包含 schema 中所有的字段，包括定义为主键的字段。EXCEPT_KEY：记录的 value 部分包含 schema 的所有字段，定义为主键的字段除外。 |
| sink.parallelism | 可选 | (none) | Integer | 定义 upsert-kafka sink 算子的并行度。默认情况下，由框架确定并行度，与上游链接算子的并行度保持一致。 |
| sink.buffer.flush.max-rows | 可选 | 0 | Integer | 缓存刷新前，最多能缓存多少条记录。当 sink 收到很多同 key 上的更新时，缓存将保留同 key 的最后一条记录，因此 sink 缓存能帮助减少发往 Kafka topic 的数据量，以及避免发送潜在的 tombstone 消息。可以通过设置为 '0' 来禁用它。默认，该选项是未开启的。注意，如果要开启 sink 缓存，需要同时设置 'sink.buffer.flush.max-rows' 和 'sink.buffer-flush.interval' 两个选项为大于零的值。 |
| sink.buffer.flush.interval | 可选 | 0 | Duration | 缓存刷新的间隔时间，超过该时间后异步线程将刷新缓存数据。当 sink 收到很多同 key 上的更新时，缓存将保留同 key 的最后一条记录，因此 sink 缓存能帮助减少发往 Kafka topic 的数据量，以及避免发送潜在的 tombstone 消息。可以通过设置为 '0' 来禁用它。默认，该选项是未开启的。注意，如果要开启 sink 缓存，需要同时设置 'sink.buffer.flush.max-rows' 和 'sink.buffer-flush.interval' 两个选项为大于零的值。 |

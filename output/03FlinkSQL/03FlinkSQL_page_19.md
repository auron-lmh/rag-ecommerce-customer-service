## 第19页

- 配置参数

| 参数 | 是否必选 | 默认值 | 数据类型 | 描述 |
|---|---|---|---|---|
| connector | 必须 | (none) | String | 指定要使用的连接器，这里是'datagen'。 |
| rows-per-second | 可选 | 10000 | Long | 每秒生成的行数，用以控制数据发出速率。 |
| fields.#.kind | 可选 | random | String | 指定'#'字段的生成器。可以是'sequence'或'random'。 |
| fields.#.min | 可选 | (Minimumvalue oftype) | (Type offield) | 随机生成器的最小值，适用于数字类型。 |
| fields.#.max | 可选 | (Maximumvalue oftype) | (Type offield) | 随机生成器的最大值，适用于数字类型。 |
| fields.#.max-past | 可选 | 0 | Duration | 随机生成器生成相对当前时间向过去偏移的最大值，适用于timestamp类型。 |
| fields.#.length | 可选 | 100 | Integer | 随机生成器生成字符的长度，适用于char、varchar、binary、varbinary、string。 |
| fields.#.start | 可选 | (none) | (Type offield) | 序列生成器的起始值。 |
| fields.#.end | 可选 | (none) | (Type offield) | 序列生成器的结束值。 |

## 3.4. Upsert Kafka Connector

- Upsert Kafka Connector允许用户以upsert的方式从Kafka主题读取数据或将数据写入Kafka主题。

- 在某些场景中输出（更新）结果的时候，需要将Kafka消息记录的key当成主键处理，用来确定一条数据是应该作为插入、删除还是更新记录来处理。

- 使用upsert-kafka connector，必须在创建表时定义主键，并为键（key.format）和值（value.format）指定序列化反序列化格式。

- 作为 source

- ○ upsert-kafka Connector会生产一个changelog流，其中每条数据记录都表示一个更新或删除事件。

- ○ 如果不存在对应的key，则视为INSERT操作。

- ○ 如果已经存在了相对应的key，则该key对应的value值为最后一次更新的值。

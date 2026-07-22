## 第5页

- 临时表（Temporary Table）

- 与单个 Flink 会话（session）的生命周期相关。

- 临时表通常保存于内存中并且仅在创建它们的 Flink 会话持续期间存在。这些表对于其它会话是不可见的。

- 永久表（Permanent Table）

- 在多个 Flink 会话和群集（cluster）中可见。

- 永久表需要 catalog（例如 Hive Metastore）以维护表的元数据。一旦永久表被创建，它将对任何连接到 catalog 的 Flink 会话可见且持续存在，直至被明确删除。

- 屏蔽特性（Shadowing）

- 使用与已存在的永久表相同的标识符去注册临时表。临时表会屏蔽永久表，并且只要临时表存在，永久表就无法访问。所有使用该标识符的查询都将作用于临时表。

- 例如只有一个子集的数据，或者数据是不确定的。一旦验证了查询的正确性，就可以对实际的生产表进行查询。

## 2.2.2. fromDataStream

- 之前的所有学习都是基于流，如果能将流转换成表就比较润了！

- 想要将一个 DataStream 转换成表也很简单，可以通过调用表环境的 fromDataStream() 方法来实现，返回的就是一个 Table 对象

$$
StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
$$

$$
// 获取表环境
$$

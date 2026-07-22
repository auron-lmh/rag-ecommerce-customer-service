## 第34页

## 6.2.2. DataStream定义时间

- 事件时间属性也可以在将 DataStream 转换为表的时候来定义。

- 调用 fromDataStream()方法创建表时，可以追加参数来定义表中的字段结构；这时可以给某个字段加上 .rowtime() 后缀，就表示将当前字段指定为事件时间属性。

- 字段可以是数据中本不存在、额外追加上去的“逻辑字段”，就像之前 DDL 中定义的第二种情况；

- 字段可以是本身固有的字段，那么这个字段就会被事件时间属性所覆盖，类型也会被转换为 TIMESTAMP。

- 不论那种方式，时间属性字段中保存的都是事件的时间戳（TIMESTAMP 类型）

- 需要注意的是，这种方式只负责指定时间属性，而时间戳的提取和水位线的生成应该之前就在 DataStream 上定义好了。

- 由于 DataStream 中没有时区概念，因此 Flink 会将事件时间属性解析成不带时区的 TIMESTAMP 类型，所有的时值都被当作 UTC 标准时间

// 1. 创建一个表执行环境

StreamExecutionEnvironment env =

StreamExecutionEnvironment.getExecutionEnvironment();

StreamTableEnvironment tableEnv = StreamTableEnvironment.create(env);

env.setParallelism(1);

SingleOutputStreamOperator<Event> streamOperator = env.addSource(new

// 乱序流的WaterMark生成

assignTimestampsAndWatermarks(watermarkStrategy

.<Event>forBoundedOutOfForderness(Duration.ofSeconds(2)) //

延迟2秒保证数据正确

.withTimestampAssigner(new

@Override // 时间戳的提取器

return event.getTimestamp();

)

tableEnv.fromDataStream(streamOperator,$("user_name"),$("url"),$("timestamp")

).as ("ts")

,$("et").rowtime());

## 6.3. 处理时间

- 定义处理时间属性时，必须要额外声明一个字段，专门用来保存当前的处理时间

## 6.3.1. SQL中定义时间

## 第27页

//启动一个线程专门发送消息给Kafka，这样我们才有数据消费

KafkaUtil.sendMsg("yjxxt",

LocalDateTime.now().format(DateTimeFormatter.ISO_DATE_TIME));

Thread.sleep(100);

e.printStackTrace();

）

//获取环境

StreamExecutionEnvironment environment =

StreamExecutionEnvironment.getExecutionEnvironment();

//设置Kafka连接

KafkaSource<String> source = KafkaSource.<String>builder()

.setStartingOffsets(OffsetsInitializer.earliest())

.setValueOnlyDeserializer(new SimpleStringSchema())

.build();

//读取数据源

DataStreamSource<String> kafkaSource =

environment.fromSource(source, WatermarkStrategy.nowatermarks(),

"kafka Source");

kafkaSource.map(word -> "kafkaSource_" + word).print();

//执行环境

environment.execute();

）

## 4.5. 自定义Source:

Flink 的 DataStream API 可以让开发者根据实际需要，灵活的自定义 Source。

本质上就是定义一个类,

o 可以实现 SourceFunction 或者 RichSourceFunction, 这两者都是非并行的 source 算子

o 也可实现 ParallelSourceFunction 或者 RichParallelSourceFunction, 这两者都是可并行执

行的 source 算子

■ 带 Rich 的，都拥有 open(),close(),getRuntimeContext() 方法

■ 带 Parallel 的，都可多实例并行执行

要解析的数据

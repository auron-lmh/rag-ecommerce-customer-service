## 第19页

StreamExecutionEnvironment environment =

StreamExecutionEnvironment.getExecutionEnvironment();

environment.setParallelism(2);

//获取数据源

DataStreamSource<String> goodInfoSource =

environment.fromSource(Kafkautils.getKafkaSource("t_goodinfo", "liyi"),

WatermarkStrategy.nowatermarks(), "Kafka Source Info");

DataStreamSource<String> goodPriceSource =

environment.fromSource(Kafkautils.getKafkaSource("t_goodprice", "liyi"),

WatermarkStrategy.nowatermarks(), "Kafka Source Price");

//添加水位线

SingleOutputStreamOperator<Tuple3<String, String, Long>>

String[] split = record.split(":");

return Tuple3.of(split[0], split[1],

Long.parseLong(split[2]));

.assignTimestampsAndWatermarks(watermarkStrategy);

<Tuple3<String, String,

Long>>forBoundedOutOfOrderness(Duration.ofSeconds(3))

.withTimestampAssigner((element, recordTime) ->

return element.f2;

SingleOutputStreamOperator<Tuple3<String, String, Long>>

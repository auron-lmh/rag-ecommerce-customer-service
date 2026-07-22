## 第22页

$$
e.printStackTrace();
$$

//运行环境

StreamExecutionEnvironment environment =

StreamExecutionEnvironment.getExecutionEnvironment();

environment.setParallelism(2);

//获取数据源

DataStreamSource<String> goodInfoSource =

environment.fromSource(KafkaUtil.getKafkaSource("t_goodinfo", "liyi"),

watermarkStrategy.nowatermarks(), "Kafka Source Info");

DataStreamSource<String> goodPriceSource =

environment.fromSource(KafkaUtil.getKafkaSource("t_goodprice", "liyi"),

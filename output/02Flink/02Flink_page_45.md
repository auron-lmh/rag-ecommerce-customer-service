## 第45页

## 4. Flink 集群部署

Flink的部署有三种模式，分别是Local，Standalone Cluster和Yarn Cluster

## 4.1. 环境搭建

SingleOutputStreamOperator<String> transformation = kafkaSource.keyBy(word -> word)

.map(new RichMapFunction<String, String>() { private ValueState<Integer> valueState; private int countBuffer;

@Override

public String map(String value) throws Exception { // 累加器叠加 this.countBuffer++; // 更新状态 this.valueState.update(countBuffer); // 返回结果 return "value:" + this.countBuffer; }

@Override

public void open(Configuration parameters) throws Exception { // 初始化 new ValueStateDescriptor<Integer>("countBuffer", Types.INT); this.valueState = getRuntimeContext().getState(valueStateDescriptor); // 恢复默认值 this.countBuffer = this.valueState.value(); System.out.println("HelloEosUseKFK.open[" + this.valueState + "][" + this.valueState + "]"); }

//KafkaSink

KafkaSink<String> kafkaSinkSetting = KafkaSink.<String>builder() .setBootstrapServers("node01:9092,node02:9092,node03:9092")

.setRecordSerializer(KafkaRecordSerializationSchema.builder() .setTopic("t_kafka_sink") .setValueSerializationSchema(new SimpleStringSchema()) .build())

//运行环境

environment.execute();

Exception {

//初始化

ValueStateDescriptor<Integer> valueStateDescriptor = new ValueStateDescriptor<Integer>("countBuffer", Types.INT);

this.valueState =

getRuntimeContext().getState(valueStateDescriptor);

//恢复默认值

this.countBuffer = this.valueState.value();

System.out.println("HelloEosUseKFK.open[" +

this.valueState + "][" + this.valueState + "]");

};

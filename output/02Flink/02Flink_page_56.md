## 第56页

○

<dependency>

<groupId>org.apache.flink</groupId>

<artifactId>flink-cep</artifactId>

</dependency>

○

DataStream<Event> input = ...;

Pattern<Event, ?> pattern = Pattern.<Event>begin("start").where(

@override

## 第21页

## 2.3.3. 代码实现

间隔联结在代码中，是基于KeyedStream的联结（join）操作。

DataStream在keyBy得到KeyedStream之后，可以调用.intervalJoin()来合并两条流，传入的参数同样是一个KeyedStream，两者的key类型应该一致；得到的是一个IntervalJoin类型。后续的操作同样是完全固定的：先通过.between()方法指定间隔的上下界，再调用.process()方法，定义对匹配数据对的处理操作。调用.process()需要传入一个处理函数，这是处理函数家族的最后一员：“处理联结函数”ProcessJoinFunction。

import com.yjxxt.util.KafkaUtil;

import org.apache.flink.api.common.eventtime.WatermarkStrategy;

import org.apache.flink.api.common.typeinfo.Types;

import org.apache.flink.api.java.tuple.Tuple3;

import org.apache.flink.streaming.api.datastream.DataStreamSource;

import org.apache.flink.streaming.api.datastream.SingleOutputStreamOperator;

import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;

import org.apache.flink.streaming.api.functions.co.ProcessJoinFunction;

import org.apache.flink.streaming.api.windowing.time.Time;

import org.apache.flink.util.Collector;

import java.time.Duration;

/**

* @description :

* @School:优极限学堂

* @Teacher:李毅大帝

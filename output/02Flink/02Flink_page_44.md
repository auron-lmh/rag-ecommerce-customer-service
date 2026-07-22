## 第44页

import org.apache.flink.streaming.api.checkpointingMode;

import org.apache.flink.streaming.api.datastream.DataStreamSource;

import org.apache.flink.streaming.api.datastream.SingleOutputStreamOperator;

import

org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;

import java.util.concurrent.TimeUnit;

/**

* @Description : Source Kafka -->Flink -->Sink Kafka

* @School: 优极限学堂

* @Official-website: http://www.yjxxt.com

* @Teacher: 李毅大帝

* @Mail:863159469@qq.com

*

//运行环境并设置CheckPoint【开启】【最小间隔】【错误容忍】【精确一次】【超时时间

】【并行度】【重启策略】

StreamExecutionEnvironment environment =

StreamExecutionEnvironment.getExecutionEnvironment();

environment.setParallelism(2);

environment.enableCheckpointing(5000);

environment.getCheckpointConfig().setMinPauseBetweenCheckpoints(1000);

environment.getCheckpointConfig().setTolerableCheckpointFailureNumber(0);

environment.getCheckpointConfig().setCheckpointingMode(CheckpointingMode.EX

ACTLY_ONCE);

environment.getCheckpointConfig().setCheckpointTimeout(30000);

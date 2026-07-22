## 第18页

一个TaskManager可以同时执行多个任务（tasks）

这些任务可以是同一个算子的子任务（数据并行）

这些任务可以是来自不同算子（任务并行）

这些任务可以是另一个不同应用程序（作业并行）

2.8.2. 任务的执行计划

获取任务执行的Json串

import org.apache.flink.api.common.typeinfo.Types;

import org.apache.flink.api.java.tuple.Tuple2;

import org.apache.flink.configuration.Configuration;

import org.apache.flink.streaming.api.datastream.DataStreamSource;

import

org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;

import java.util.Arrays;

/**

@Description :

@School: 优极限学堂

@Official-website: http://www.yjxxt.com

@Teacher: 李毅大帝

@Mail:863159469@qq.com

*

//获取程序运行的环境

StreamExecutionEnvironment environment =

StreamExecutionEnvironment.createLocalEnvironmentWithWebUI(new

Configuration());

//调用Source方法创建DataStream

DataStreamSource<String> lineStream =

//开始进行计算

lineStream.<String>flatMap((line, collector) ->

).forEach(collector::collect)).returns(Types.STRING)

.map(word -> new Tuple2(word,

1)).returns(Types.TUPLE(Types.STRING, Types.INT))

.keyBy(tuple2 -> tuple2.f0)

.sum(1)

.print();

//获取执行计划

System.out.println(environment.getExecutionPlan());

//执行

// environment.execute();

## 第62页

import org.apache.flink.api.common.typeinfo.Types;

import org.apache.flink.api.java.tuple.Tuple2;

import org.apache.flink.streaming.api.datastream.DataStreamSource;

import

org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;

import org.apache.flink.streaming.api.windowing.assigners.GlobalWindows;

import org.apache.flink.streaming.api.windowing.triggers.CountTrigger;

import org.apache.flink.streaming.api.windowing.triggers.PurgingTrigger;

/**

@Description :

@School:优极限学堂

@Official-Website: http://www.yjxxt.com

@Teacher:李毅大帝

@Mail:863159469@qq.com

*

//运行环境

StreamExecutionEnvironment environment =

StreamExecutionEnvironment.getExecutionEnvironment();

//获取数据源-admin:3

DataStreamSource<String> source =

//Globalwindow

.keyBy(tuple2 -> tuple2.f0)

.window(Globalwindows.create())

.trigger(PurgingTrigger.of(CountTrigger.of(5)))

t1.f1 = t1.f1 + t2.f1;

return t1;

.windowAll(Globalwindows.create())

.trigger(PurgingTrigger.of(CountTrigger.of(5)))

t1.f1 = t1.f1 + t2.f1;

time

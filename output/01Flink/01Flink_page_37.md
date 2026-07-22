## 第37页

6. Flink Sink类算子

Data sinks 使用 DataStream 并将它们转发到文件、套接字、外部系统或打印它们。

6.1. 输出到控制台

print

将计算结果打印到控制台，通常是用来做实验和测试时使用。

6.2. 输出到文件

这些方法已经被@Deprecated,请谨慎使用

writeAsText

将计算结果输出成text文件

writeAsCsv

写出的数据格式必须为Tuple，否则就会报错

将计算结果输出成csv文件

writeUsingOutputFormat

自定义输出方式。

尝试自己实现将一段话通过DES加密

代码实现

import org.apache.flink.api.common.typeinfo.Types;

import org.apache.flink.api.java.tuple.Tuple2;

import org.apache.flink.core.fs.FileSystem;

import org.apache.flink.streaming.api.datastream.DataStreamSource;

import

org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;

/**

@Description :

@School:优极限学堂

@Official-website: http://www.yjxxt.com

@Teacher:李毅大帝

@Mail:863159469@qq.com

*

## 第24页

# Apache Flink Dashboard

Overview

Jobs

Running Jobs:

Completed Jobs:

Task Managers

Job Manager

Submit New Job

Available Task Slots

0

Total Task Slots 8 Task Managers 1

Running Job List

Job Name

Flink Streaming Job

Start Time

2022-10-14 15:06:10

Duration

2m 3s

End Time

Tasks

Status

RUNNING

Completed Job List

Job Name

Start Time

Duration

End Time

Tasks

Status

No Data

## 4. Flink Source类算子

通过 StreamExecutionEnvironment 可以访问多种预定义的 stream source:

## 4.1. 基于文件:

readTextFile(path) - 读取文本文件，例如遵守 TextInputFormat 规范的文件，逐行读取并将

它们作为字符串返回。

readFile(fileInputFormat, path) - 按照指定的文件输入格式读取（一次）文件。

readFile(fileInputFormat, path, watchType, interval, pathFilter, typeInfo) - 这

是前两个方法内部调用的方法。

DataSet<String> source =

## 4.2. 基于套接字:

socketTextStream - 从套接字读取。元素可以由分隔符分隔。

在启动 Flink 程序之前，必须先启动一个 Socket 服务

DataStreamSource<String> lineStream =

## 4.3. 基于集合:

fromCollection(Collection) - 从 Java java.util.Collection 创建数据流。集合中的所有元素必

须属于同一类型。

fromCollection(Iterator, Class) - 从迭代器创建数据流。class 参数指定迭代器返回元素的

数据类型。

fromElements(T ...)-从给定的对象序列中创建数据流。所有的对象必须属于同一类型。

fromParallelCollection(SplittableIterator, Class) - 从迭代器并行创建数据流。class

参数指定迭代器返回元素的数据类型。

generateSequence(from, to) - 基于给定间隔内的数字序列并行生成数据流。

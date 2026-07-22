## 第35页

## 6.3.2. DataFrame定义时间

- 处理时间属性同样可以在将DataFrame转换为表的时候来定义。我们调用fromDataStream()方法创建表时，可以用.proctime()后缀来指定处理时间属性字段。

- 由于处理时间是系统时间，原始数据中并没有这个字段，所以处理时间属性一定不能定义在一个已有字段上，只能定义在表结构所有字段的最后，作为额外的逻辑字段出现

- 代码实现

DataStream<Tuple2<String, String>> stream = ...;

// 声明一个额外的字段作为处理时间属性字段

$$
Table table = tEnv.fromDataStream(stream, $("user"), $("url"), $("ts").proctime());
$$

## 7. FlinkSQL 窗口TVF

- https://nightlies.apache.org/flink/flink-docs-release-1.15/zh/docs/dev/table/sql/queries/window-tvf/

TVF[Windowing table-valued functions] 窗口化表值函数

- 目前 Flink 提供了以下几个窗口 TVF:

- 滚动窗口 (Tumbling Windows)

- 滑动窗口 (Hop Windows, 跳跃窗口)

- 累积窗口 (Cumulate Windows)

- 会话窗口 (Session Windows, 目前尚未完全支持)

- 在窗口 TVF 的返回值中，除去原始表中的所有列，还增加了用来描述窗口的额外 3 个列：

- “窗口起始点” (window_start)

- “窗口结束点” (window_end)

- “窗口时间” (window_time)

- 起始点和结束点比较好理解，这里的“窗口时间”指的是窗口中的时间属性，它的值等于 window_end - 1ms，所以相当于于是窗口中能够包含数据的最大时间戳

## 7.1. TUMBLE

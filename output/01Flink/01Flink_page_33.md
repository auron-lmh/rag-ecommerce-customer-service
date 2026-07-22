## 第33页

max(): 在输入流上对指定的字段求最大值。

minBy(): 在输入流上针对指定字段求最小值，并返回最小值字段所在的那条数据。

maxBy(): 在输入流上针对指定字段求最大值，并返回最大值字段所在的那条数据。

## 5.6. reduce

在相同 key 的数据流上“滚动”执行 reduce。将当前元素与最后一次 reduce 得到的值组合然后输出
新值。

import org.apache.flink.api.common.typeinfo.Types;
import org.apache.flink.api.java.tuple.Tuple2;
import org.apache.flink.streaming.api.datastream.DataStreamSource;
import
org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;

import java.util.ArrayList;
import java.util.Arrays;

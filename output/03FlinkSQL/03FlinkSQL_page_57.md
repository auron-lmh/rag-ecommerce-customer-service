## 第57页

AggregateFunction 有两个泛型参数<T, ACC>，T 表示聚合输出的结果类型，ACC 则表示聚合的中间状态类型

- 每个 AggregateFunction 都必须实现以下几个方法:

- createAccumulator()

这是创建累加器的方法。没有输入参数，返回类型为累加器类型 ACC

accumulate()

这是进行聚合计算的核心方法，每来一行数据都会调用。它的第一个参数是确定的，就是当前的累加器，类型为 ACC，表示当前聚合的中间状态；

后面的参数则是聚合函数调用时传入的参数，可以有多个，类型也可以不同。这个方法主要是更新聚合状态，所以没有返回类型

- getValue()

这是得到最终返回结果的方法。输入参数是 ACC 类型的累加器，输出类型为 T。在遇到复杂类型时，Flink 的类型推导可能会无法得到正确的结果。

所以AggregateFunction也可以专门对累加器和返回结果的类型进行声明，这是通过 getAccumulatorType()和getResultType()两个方法来指定的

- 代码实现

import org.apache.flink.api.java.tuple.Tuple2;

import org.apache.flink.table.annotation.DatatypeHint;

import org.apache.flink.table.annotation.FunctionHint;

import org.apache.flink.table.functions.AggregateFunction;

* @Description :

* @School:优极限学堂

* @Official-website: http://www.yjxxt.com

* @Teacher:李毅大帝

* @Mail:863159469@qq.com

@Override

return Tuple2.of(0, 0);

@FunctionHint(

)

acc.f0 += weight * price;

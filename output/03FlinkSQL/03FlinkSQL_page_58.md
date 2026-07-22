## 第58页

## 11.3.4. UDF表值聚合函数

| id | name | price |
|---|---|---|
| 1 | Latte | 6 |
| 2 | Milk | 3 |
| 3 | Breve | 5 |
| 4 | Mocha | 8 |
| 5 | Tea | 4 |

UDTAGG represents its state using accumulator

$$
createAccumulator()
$$

$$
accumulate(ACC accumulator, ..user defined params..)
$$

$$
accumulator (ACC)
$$

$$
groupedTab.flatAggregate("top2(price) as v")
$$

$$
emitValue(ACC accumulator)
$$

- 用户自定义表聚合函数（UDTAGG）可以把一行或多行数据（也就是一个表）聚合成另一张表，结果表中可以有多行多列。

- 自定义方式：

- 自定义表聚合函数需要继承抽象类 TableAggregateFunction。TableAggregateFunction 的结构和原理与 AggregateFunction 非常类似，同样有两个泛型参数<t, acc>, 用一个 ACC 类型的累加器（accumulator）来存储聚合的中间结果。聚合函数中必须实现的三个方法，在 TableAggregateFunction 中也必须对应实现:

- createAccumulator()

- 创建累加器的方法，与 AggregateFunction 中用法相同

- accumulate()

- 聚合计算的核心方法，与 AggregateFunction 中用法相同

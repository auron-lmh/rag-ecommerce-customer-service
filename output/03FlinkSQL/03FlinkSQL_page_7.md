## 第7页

## 2.3. 数据类型

## 2.3.1. 原子类型

- DataStream 中支持的数据类型，Table 中也是都支持的

- 在 Flink 中，基础数据类型 (Integer、Double、String) 和通用数据类型（不可再拆分的数据类型）统一称作“原子类型”。

- 原子类型的 DataStream，转换之后就成了只有一列的 Table，列字段（field）的数据类型可以由原子类型推断出。

- 另外还可以在 fromDataStream()方法里增加参数，用来重新命名列字段

$$
StreamTableEnvironment tableEnv = ...;
$$

$$
DataStream<Long> stream = ...;
$$

$$
// 将数据流转换成动态表，动态表只有一个字段，重命名为 myLong
$$

$$
Table table = tableEnv.fromDataStream(stream, $("myLong"));
$$

## 2.3.2. Tuple 类型

- 当原子类型不做重命名时，默认的字段名就是 "f0"，容易想到，这其实就是将原子类型看作了一元组 Tuple1 的处理结果

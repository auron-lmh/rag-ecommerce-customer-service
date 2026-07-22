## 第56页

## 11.3.3. UDF聚合函数

| id | name | price |
|---|---|---|
| 1 | Latte | 6 |
| 2 | Milk | 3 |
| 3 | Breve | 5 |
| 4 | Mocha | 8 |
| 5 | Tea | 4 |

UDAGG represents its state using accumulator

accumulate(ACC accumulator,

..[user defined params]..)

accumulator

(ACC)

8

getValue(ACC accumulator)

• 用户自定义聚合函数（User Defined AGGregate function，UDAGG）会把一行或多行数据（也就是一个表）聚合成一个标量值。这是一个标准的“多对一”的转换

• 自定义方式:

○ 自定义聚合函数需要继承抽象类 AggregateFunction.

// 注册函数

env.createTemporarySystemFunction("SplitFunction",

SplitFunction.class);

// 在 Table API 里调用注册好的函数

env

.from("MyTable")

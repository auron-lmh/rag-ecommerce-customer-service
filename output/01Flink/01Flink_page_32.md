## 第32页

## 5.5. aggregation

- 滚动聚合算子由 KeyedStream 调用，并生成一个聚合以后的DataStream
滚动聚合算子是多个聚合算子的统称，有 sum、min、minBy、max、maxBy;
滚动聚合方法:
sum(): 在输入流上对指定的字段做滚动相加操作。
min(): 在输入流上对指定的字段求最小值。

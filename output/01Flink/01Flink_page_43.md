## 第43页

7.5. BroadcastPartitioner

广播分区会将上游数据输出到下游算子的每个实例中。适合于大数据集和小数据集做ion的场景。

发送到下游对应的第一个task。它要求上下游算子并行度一样。

## 7.7. KeyGroupStreamPartitioner

分区器。会将数据按Key的Hash值输出到下游算子实例中。

Hash分区器。会将数据按 Key 的 Hash 值输出到下游算子实例中。

## 7.8. CustomPartitioner

用户自定义分区器。需要用户自己实现Partitioner接口，来定义自己的分区逻辑

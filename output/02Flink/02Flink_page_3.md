## 第3页

- 托管状态是由Flink的运行时（Runtime）来托管的；在配置容错机制后，状态会自动持久化保存，并在发生故障时自动恢复。

- 当应用发生横向扩展时，状态也会自动地重组分配到所有的子任务实例上。

- Flink提供了值状态（ValueState）、列表状态（ListState）、映射状态（MapState）、聚合状态（AggregateState）等多种结构，内部支持各种数据类型。

## 1.3. 状态类型

- 在Flink中，一个算子任务会按照并行度分为多个并行子任务执行，而不同的子任务会占据不同的任务槽（task slot）。

- 由于不同的slot在计算资源上是物理隔离的，所以Flink能管理的状态在并行任务间是无法共享的，每个状态只能针对当前子任务的实例有效。

- 而很多有状态的操作（比如聚合、窗口）都是要先做keyBy进行按键分区的。

- 按键分区之后，任务所进行的所有计算都应该只针对当前key有效，所以状态也应该按照key彼此隔离。在这种情况下，状态的访问方式又会有所不同。

- 基于这样的想法，我们又可以将托管状态分为两类：算子状态和按键分区状态。

| 分类区别 | Keyed State | Operator State |
|---|---|---|
| 使用范围 | 只能用于KeyedStream算子中使用，每个Key对应一个state | 可以用于所有算子，常用与Source，比如FlinkKafkaConsumer，一个Operator实例对应一个state |
| 扩缩容模式 | Flink把所有键值分为不同的 Key Group，Key Group 是 Flink 重新分配 Keyed State 的最小单元。并改变时，Flink会以Key Group为单位将键值分配给不同的任务。 | 当并发改变时，有多种方式来进行重分配，比如ListState使用均匀分配模式，BroadcastState会把状态拷贝到全部新任务上。 |
| 访问方式 | 实现Rich Function，通过getRuntimeContext () 返回的RuntimeContext进行获取 | 实现CheckpointedFunction或者ListCheckpoint的接口 |
| 数据结构 | ValueState、ListState、ReducingState、AggregatingState、MapState | ListState、BroadcastState等 |

## 1.3.1. 算子状态(Operator State)

状态作用范围限定为当前的算子任务实例，也就是只对当前并行子任务实例有效。

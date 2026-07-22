## 第37页

## 3.5. Flink Operator

- 算子状态的EOS语义保证

- 基于分布式快照算法: (Chandy-Lamport), flink实现了整个数据流中各算子的状态数据快照统一;

- 既：一次checkpoint后所持久化的各算子的状态数据，确保是经过了相同数据的影响；

- 如果这条（批）数据在中间任何过程失败，则重启恢复后，所有算子的state数据都能回到这条数据从未处理过时的状态

- 同Spark相比，Spark仅仅是针对Driver的故障恢复Checkpoint。而Flink的快照可以到算子级别，并且对全局数据也可以做快照。

- 检查点协调器线程

Checkpoint Coordinator

确认完成备份

barrier 棚栏

快照snapshot存储

确认完成备份

barrier

快照snapshot存储

barrier

确认完成备份

快照snapshot存储

存储 (HDFS)

## 3.6. Flink Sink

- Sink端主要的问题是，作业失败重启时，数据重放可能造成最终目标存储中被写入了重复数据；

- Flink中也设计了相应机制来确保EOS

- 采用幕等写入方式

- 采用事务写入方式

- 采用预写日志提交方式

- 2PC提交方式

| Exactly Once实现方式 | 优点 | 缺点 |
|---|---|---|
| At least once + 去重 | • 故障对性能的影响是局部的• 故障的影响不一定会随着拓扑的大小而增加 | • 可能需要大量的存储和基础设施来支持每个算子的每个事件的性能开销 |
| At least once + 幂等 | • 实现简单，开销较低 | • 依赖存储特性和数据特征 |
| 分布式快照 | • 较小的性能和资源开销 | • barrier 同步• 任何算子发生故障，都需要发生全局暂停和状态回滚（Region Failover: FLINK-4256）• 拓扑越大，对性能的潜在影响越大 |

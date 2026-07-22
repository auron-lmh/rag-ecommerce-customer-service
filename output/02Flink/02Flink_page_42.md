## 第42页

- 本例中的 Data Source 和窗口操作无外部状态，因此在该阶段，这两个 Opeartor 无需执行任何逻辑，但是 Data Sink 是有外部状态的，此时我们 必须提交外部事务，当 Sink 任务收到确认通知，就会正式提交之前的 事务，Kafka 中未确认的数据就改为“已确认”，数据就真正可以被消费 了，如下图所示:

- 总结

- 注：Flink 由 JobManager 协调各个 TaskManager 进行 Checkpoint 存储，Checkpoint 保存在 StateBackend（状态后端）中，默认 StateBackend 是内存级 的，也可以改为文件级的进行持久化保存

- Flink 消费到 Kafka 数据之后，就会开启一个 Kafka 的事务，正常写入 Kafka 分区日志标记但未提交，也就是预提交（Per-commit)

- 一旦所有的 Operator 完成各自的 Per-commit，他们会发起一个 commit 操作

- 如果有任意一个 Per-commit 失败，所有其他的 Per-commit 必须停止，并且 Flink 会回滚到最近成功完成的 CheckPoint

- 当所有的 Operator 完成任务时，Sink 端就收到 checkpoint barrier（检查点分界线），Sink 保存当前状态，存入 Checkpoint，通知 JobManager，并提交外部事物，用于提交外部检查点的数据

- JobManager 收到所有任务通知，发出确认信息，表示 Checkpoint 已经完成，Sink 收到 JobManager 的确认信息，正式提交这段时间的数据

- 外部系统（Kafka）关闭事务，提交的数据可以正常消费了

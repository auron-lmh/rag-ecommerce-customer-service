## 第41页

## 当 Checkpoint 启动时

- JobManager 会将检查点分界线（checkpoint barrier）注入数据流，checkpoint barrier 会在算子间传递下去

Pre-commit (checkpoint starts)

## Source 端

- Flink Kafka Source 负责保存 Kafka 消费 offset，当 Checkpoint 成功时 Flink 负责提交这些写入，否则就终止取消掉它们，当 Checkpoint 完成位移保存，它会将 checkpoint barrier（检查点分界线）传给下一个 Operator，然后每个算子会对当前的状态做个快照，保存到状态后端（State Backend）。

- 对于 Source 任务而言，就会把当前的 offset 作为状态保存起来。下次从 Checkpoint 恢复时，Source 任务可以重新提交偏移量，从上次保存的位置 开始重新消费数据，如下图所示：

Pre-commit without external state

## Slink 端：

- 从 Source 端开始，每个内部的 transform 任务遇到 checkpoint barrier 时，都会把状态存到 Checkpoint 里。

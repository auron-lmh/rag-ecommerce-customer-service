## 第31页

Checkpoint 2

- 缓存数据

- 当task接收到所有上游发送来的barrier, 即可以认为当前task收到了本次 Checkpoint 的所有数据。之后 task 会将 barrier 继续发送给下游, 然后处理缓存的数据, 比如这里 sum_even 会处理 Source1 发送来的数据4. 而且, 在这个过程中 Source 会继续读取数据发送给下游, 并不会中断。

Checkpoint 2

- Sink端

- 当sink收到barrier后, 会向JobManager上报本次Checkpoint完成。至此, 本次Checkpoint结束, 各阶段的状态均进行了持久化, 可以用于后续的故障恢复。

Checkpoint 2

## 3.2.4. 机制革新

- 反压时无法做出 Checkpoint :

保存状态的外部存储,如: HDFS, RocksDB

当接收到所有上游发送来的barrier消息后, 会进行两件事:

1. 对task 的状态进行checkpoint.

比如这里 sum_even 的状态为sum=8.

2. 将barrier消息发送给下游

对每个task 的状态进行checkpoint

将barrier发送给下游

checkpoint过程中, Source会持续拉取数据并发送给你task

缓存数据只有

8+4=12

随后sum_odd收到了Source1的数据5和Source2的数据8, 依次累加得到结果13和18, 发送给下游Sink

当sink接收到barrier消息, 会向JobManager上报checkpoint完成.

至此, 本次checkpoint结束, 各阶段的状态进行了持久化, 用于故障恢复.

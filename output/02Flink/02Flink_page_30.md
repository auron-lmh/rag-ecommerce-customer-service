## 第30页

JobManager启动Checkpoint,会给每个Source发送一个barrier信息(图中的三角形)

这里的编号*2*可以理解为checkpoint的次数，每进行一次会递增1

当Source接收到barrier消息,会将当前的状态 (Partition、Offset)保存到

StateBackend,然后向 JobManager 报告Checkpoint 完成。之后Source会将barrier消息广播给下游的每一个 task:

• Transformation端

当task接收到某个上游发送来的barrier,会将该上游barrier之前的数据继续进行处理,而

barrier之后发送来的消息不会进行处理,会被缓存起来.

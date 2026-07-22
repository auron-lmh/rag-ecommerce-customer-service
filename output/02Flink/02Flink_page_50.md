## 第50页

## 4.3. Standalone模式

- 启动之后, TaskManager 会向资源管理器注册它的 slots; 收到资源管理器的指令后,

TaskManager 就会将一个或者多个槽位提供给 JobMaster 调用, JobMaster 就可以分配任务来执行了.

了。

- 在执行过程中, TaskManager 可以缓冲数据, 还可以跟其他运行同一应用的 TaskManager交换数据.

据.

## 4.3.1. 理论分析

- standalone工作流程

客户端不是运行时和程序执行的一部分, 但它用于准备并发送dataflow(JobGraph)给

Master(JobManager), 然后, 客户端断开连接或者维持连接以等待接收计算结果.

当 Flink 集群启动后, 首先会启动一个 JobManger 和一个或多个的 TaskManager。由 Client

TaskManager 将心跳和统计信息汇报给 JobManager。TaskManager 之间以流的形式进行

数据的传输。上述三者均为独立的 JVM 进程.

Client 为提交 Job 的客户端, 可以是运行在任何机器上 (与 JobManager 环境连通即可)。

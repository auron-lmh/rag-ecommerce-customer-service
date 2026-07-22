## 第49页

## 4.2.1. JobManager

- • JobManager 是一个 Flink 集群中任务管理和调度的核心，是控制应用执行的主进程。也就是说，每个应用都应该被唯一的 JobManager 所控制执行。JobManger 又包含 3 个不同的组件：

- • JobMaster

- ◦ JobManager 中最核心的组件，负责处理单独的作业（Job）。所以 JobMaster 和具体的 Job 是一一对应的，多个 Job 可以同时运行在一个 Flink 集群中，每个 Job 都有一个自己的 JobMaster。

- ◦ 在作业提交时，JobMaster 会先接收到要执行的应用。这里所说“应用”一般是客户端提交来的，包括: Jar 包，数据流图（dataflow graph），和作业图（JobGraph）。

- ◦ JobMaster 会把 JobGraph 转换成一个物理层面的数据流图，这个图被叫作“执行图”（ExecutionGraph），它包含了所有可以并发执行的任务。JobMaster 会向资源管理器（ResourceManager）发出请求，申请执行任务必要的资源。一旦它获取到了足够的资源，就会将执行图分发到真正运行它们的 TaskManager 上。

- • ResourceManager

- ◦ ResourceManager 主要负责资源的分配和管理，在 Flink 集群中只有一个。所谓“资源”，主要是指 。任务槽就是 Flink 集群中的资源调配单元，包含了机器用来执行计算的一组 CPU 和内存资源。每一个任务（Task）都需要分配到一个 slot 上执行。

- ◦ 在 Standalone 部署时，因为 TaskManager 是单独启动的，所以 ResourceManager 只能分发可用 TaskManager 的任务槽，不能单独启动新 TaskManager。

- ◦ 在其他资源管理平台时，ResourceManager 会将有空闲槽位的 TaskManager 分配给 JobMaster。如果 ResourceManager 没有足够的任务槽，它还可以向资源提供平台发起会话，请求提供启动 TaskManager 进程的容器。另外，ResourceManager 还负责掉空闲的 TaskManager，释放计算资源。

- • Dispatcher

- ◦ Dispatcher 主要负责提供一个 REST 接口，用来提交应用，并且负责为每一个新提交的作业启动一个新的 JobMaster 组件。Dispatcher 也会启动一个 Web UI，用来方便地展示和监控作业执行的信息。

- ◦ Dispatcher 在架构中并不是必需的，在不同的部署模式下可能会被忽略掉。

7.Job Results

Flink Program

1.Submit

JobClient

2.Submit

JobManager

(Master)

3.Success

4.Submit Task

5.Execute Task

TaskManager

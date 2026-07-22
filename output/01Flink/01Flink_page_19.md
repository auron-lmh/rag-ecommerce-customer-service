## 第19页

# FLINK PLAN VISUALIZER

Zoom In

Zoom Out

RESET

Data Source (ID = 1)
Source: Collection
Source
REBALANCE
Operator (ID = 2)
Flat Map
Operator (ID = 3)
Map
Operator (ID = 5)
Keyed Aggregation
FORWARD
FORWARD
Data Sink (ID = 6)
Sink: Print to Std. Out
Parallelism: 8
Parallelism: 9
StreamGraph

StreamNode
Rebalance
StreamEdge
Flat Map
parallelism=2
parallelism=1
StreamNode
Hash
StreamEdge
Keyed
Aggregation
Forward
StreamEdge
Sink
Operator Chain
JobGraph
JobVertex
JobVertex
JobVertex
Intermediate
DataSet
JobEdge
Flat Map
parallelism=2
parallelism=1
JobVertex
Keyed
Aggregation
--> Sink
ExecutionGraph
ExecutionJobVertex IntermediateResult
ExecutionJobVertex ExecutionVertex
ExecutionVertex
ExecutionEdge
Intermediate
Result
Partition
ExecutionEdge
ExecutionVertex
ExecutionVertex
ExecutionEdge
Keyed
Aggregation
--> Sink
(1/2)
(1/2)
ExecutionEdge
ExecutionVertex
ExecutionEdge
Keyed
Aggregation
--> Sink
(2/2)
(2/2)
parallelism=1
parallelism=2
ResultPartition
InputGate
InputGate
ResultPartition
Task
Task
ResultSub
partition
InputChannel
Flat Map
(1/2)
Hash
ResultPartition
InputGate
InputChannel
Keyed
Aggregation
--> Sink
(1/2)
Task
ResultSub
partition
ResultSub
partition
ResultPartition
InputGate
InputChannel
Keyed
Aggregation
--> Sink
(2/2)
parallelism=1
parallelism=2
ResultSub
partition
InputGate
InputChannel
Task
ResultSub
partition
ResultMap
(2/2)
Hash
parallelism=2
JobGraph:
Flink 中的执行图可以分成四层：StreamGraph -> JobGraph -> ExecutionGraph -> 物理执行图。
StreamGraph:
根据用户通过 Stream API 编写的代码生成的最初的图。用来表示程序的拓扑结构。
JobGraph:
StreamGraph经过优化后生成了 JobGraph，提交给 JobManager 的数据结构。主要的优化为，将多个符合条件的节点 chain 在一起作为一个节点，这样可以减少数据在节点之间流动所需要的序列化/反序列化/传输消耗。
ExecutionGraph:
JobManager 根据 JobGraph 生成ExecutionGraph。
ExecutionGraph是JobGraph的并行化版本，是调度层最核心的数据结构。
物理执行图:
JobManager 根据 ExecutionGraph 对 Job 进行调度后，在各个TaskManager 上部署Task 后形成的“图”
并不是一个具体的数据结构。
2.8.3. 任务并行度

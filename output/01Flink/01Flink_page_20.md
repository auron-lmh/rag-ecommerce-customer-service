## 第20页

一个算子的子任务(subtask)的个数被称之为其并行度(parallelism ['pærəleltzəm])

一个程序中，不同的算子可能具有不同的并行度。

JobGraph

E₂

D₄

C₂

B₄

A₄

TaskManager1

Slot 1.1

Slot 1.2

E

D

D

D

Slot 2.1

TaskManager2

Slot 2.2

E

D

C

B

B

A

A

A

B

C

B

A

Task Managers: 3

Total number of

processing slots: 9

flink-conf.yaml:

taskmanager.numberOfTaskSlots: 3

(Recommended value: Number of CPU cores)

Task Manager 1

Task Manager 2

Task Manager 3

Slot 1

Slot 1

Slot 1

Slot 2

Slot 2

Slot 2

Slot 3

Slot 3

Slot 3

Example 1:

WordCount with

parallelism = 1

Task Manager 1

Task Manager 2

Task Manager 3

Slot 1

Slot 1

Slot 2

Slot 2

Slot 3

Slot 3

When no argument given,

parallelism.default from flink-

conf.yaml is used.

Default value = 1

Slot 3

Example 2:

WordCount with

parallelism = 2

Task Manager 1

Task Manager 2

Task Manager 3

Source→

flinkMap

Reduce

Sink

Slot 2

Slot 1

Slot 2

Slot 3

Slot 3

Places to set parallelism for a job

flink-conf.yaml:

parallelism.default: 2

or Flink Client:

/bin/flink -p 2

or ExecutionEnvironment:

env.setParallelism(2)

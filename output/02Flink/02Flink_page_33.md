## 第33页

## 3.2.5. SavePoint

• Savepoint 作为实时任务的全局镜像，其在底层使用的代码和Checkpoint的代码是一样的

• Savepoint 是依据 Flink checkpointing 机制所创建的流作业执行状态的一致镜像;

- ○ Checkpoint 的主要目的是为意外失败的作业提供恢复机制(如 tm/jm 进程挂了)。

- ○ Checkpoint 的生命周期由 Flink 管理，即 Flink 创建，管理和删除 Checkpoint - 无需用户交互。

- ○ Savepoint 由用户创建，拥有和删除。他们的用例是计划的，手动备份和恢复。

- ○ Savepoint 应用场景，升级 Flink 版本，调整用户逻辑，改变并行度，以及进行红蓝部署等。Savepoint 更多地关注可移植性

- • Savepoint触发方式触发方式目前有三种

- ○ 使用 flink savepoint 命令触发 Savepoint, 其是在程序运行期间触发 savepoint。

- ○ 使用 flink cancel -s 命令，取消作业时，并触发 Savepoint.

- ○ 使用 Rest API 触发 Savepoint，格式为：*/jobs/:jobid /savepoints*

- • Savepoint注意点

- ○ 由于 Savepoint 是程序的全局状态，对于某些状态很大的实时任务，当我们触发 Savepoint，可能会对运行着的实时任务产生影响，个人建议如果对于状态过大的实时任务，触发 Savepoint 的时间，不要太过频繁。根据状态的大小，适当的设置触发时间。

- ○ 当我们从 Savepoint 进行恢复时，需要检查这次 Savepoint 目录文件是否可用。可能存在你上次触发 Savepoint 没有成功，导致 HDFS 目录上面 Savepoint 文件不可用或者缺少数据文件等，这种情况下，如果在指定损坏的 Savepoint 的状态目录进行状态恢复，任务会启动不起来。

## 3.3. 容错策略

• 当 Task 发生故障时，Flink 需要重启出错的 Task 以及其他受到影响的 Task，以使得作业恢复到正常执行状态。

• Flink 通过重启策略和故障恢复策略来控制 Task 重启:

- ○ 重启策略决定是否可以重启以及重启的间隔;

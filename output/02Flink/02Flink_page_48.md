## 第48页

$$
export FLINK_HOME=/opt/yjx/flink-1.15.2
$$

$$
export PATH=$FLINK_HOME/bin:$PATH
$$

- [root@123 ~]# source /etc/profile

- 开启集群

- [root@node01 ~]# start-cluster.sh

Starting cluster.
Starting standalonesession daemon on host node01.
Warning: Permanently added 'node01,192.168.88.101' (ECDSA) to the list of known hosts.
Starting taskexecutor daemon on host node01.
Warning: Permanently added 'node02,192.168.88.102' (ECDSA) to the list of known hosts.
Starting taskexecutor daemon on host node02.
Warning: Permanently added 'node03,192.168.88.103' (ECDSA) to the list of known hosts.
Starting taskexecutor daemon on host node03.

http://192.168.88.101:8081/

## 4.2. 系统架构

- Flink 的运行时架构中，最重要的就是两大组件：作业管理器（JobManger）和任务管理器（TaskManager）。

JobManager 是真正意义上的“管理者”（Master），负责管理调度，所以在不考虑高可用的情况下只能有一个；

TaskManager 是“工作者”（Worker、Slave），负责执行任务处理数据，所以可以有一个或多

客户端并不是处理系统的一部分，它只负责作业的提交。具体来说，就是调用程序的 main 方法，将代码转换成“数据流图”（Dataflow Graph），并最终生成作业图（JobGraph），一并发送给

JobManager。提交之后，任务的执行其实就跟客户端没有关系了；

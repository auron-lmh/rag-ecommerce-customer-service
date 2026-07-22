## 第51页

- 命令提交

$$
[root@node01 ~]# flink run -c com.yjxxt.flink.Hello01Standalone -p 2 /root/flink060106_util-1.0-SNAPSHOT.jar
$$

-c,-class : 需要指定的main方法的类

-c,-classpath : 向每个用户代码添加url,他是通过UrlClassLoader加载。url需要指定文件的schema如(file://)

-d,-detached : 在后台运行

-p,-parallelism : job需要指定env的并行度,这个一般都需要设置。

-q,-sysoutLogging : 禁止logging输出作为标准输出。

-s,-fromSavepoint : 基于savepoint保存下来的路径,进行恢复。

-sae,-shutdownOnAttachedExit : 如果是前台的方式提交,当客户端中断,集群执行的job任务也会shutdown.

## 4.4. Yarn模式

2. Register resources and request AppMaster container

YARN Resource Manager

Manager

3. Allocate AppMaster Container

Flink

YARN Client

YARN Container

Flink

JobManager

YARN App.

Name

Upload Time

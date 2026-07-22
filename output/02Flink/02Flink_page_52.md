## 第52页

它会为 TaskManager 生成一个新的 Flink 配置文件（这样它们才能连上 JobManager）。该文件也同样会上传到 HDFS。

另外，AM 容器同时提供了 Flink 的 Web 界面服务。

步骤4：AM 开始为 Flink 的 TaskManager 分配容器(container)，在对应的nodemanager上面启动taskmanager.

步骤5：初始化工作，从 HDFS 下载 jar 文件和修改过的配置文件。一旦这些步骤完成了，Flink 就安装完成并准备接受任务了。

## 4.4.2. 集成环境

- [root@123 ~]# vim /etc/profile

- export HADOOP_CONF_DIR=/opt/yjx/hadoop-3.1.2/etc/hadoop/

- [root@123 ~]# source /etc/profile

- 上传Flink与Hadoop的连接包

- flink-shaded-hadoop3-uber-3.1.1.7.2.9.0-173-9.0.jar

- commons-cli-1.4.jar

- 拷贝到其他节点

- [root@123 ~]# scp root@node01:/root/flink-shaded-hadoop3-uber-3.1.1.7.2.9.0-173-9.0.jar /opt/yjx/flink-1.15.2/lib/

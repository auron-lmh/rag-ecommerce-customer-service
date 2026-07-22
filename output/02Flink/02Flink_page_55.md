## 第55页

用户可以手动将应用程序jar及依赖的jar事先上传到hdfs，然后每次递交作业的时候不需要上传jar了，只需要指定hdfs已上传的jar路径即可

$$
#提交任务
$$

$$
flink run-application -t yarn-application /root/flink060106_util.jar
$$

$$
#列出集群上正在运行的作业,列出jobId、jobName
$$

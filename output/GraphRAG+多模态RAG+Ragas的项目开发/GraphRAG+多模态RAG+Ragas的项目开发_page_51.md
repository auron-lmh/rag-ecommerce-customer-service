## 第49页

[root@iZ8vb5acpt0ebqsuf5mtiwZ home]# docker ps

CONTAINER ID IMAGE
PORTS

1feff57c72e7

th: starting)

dalone

c3c62f4ed44f

th: starting)

o

ab9fc8080b74

th: starting)

[root@iZ8vb5acpt0ebqsuf5mtiwZ home]#

发送文本到当前Xshell窗口的全部会话

启动 Milvus 后，有三个名为milvus-standalone、milvus-minio 和milvus-etcd的容器启动。

milvus-etcd容器不向主机暴露任何端口，并将其数据映射到当前文件夹中的volumes/etcd。

milvus-minio容器使用默认身份验证凭据在本地为端口9090和9091提供服务，并将其数据映射到

当前文件夹中的volumes/minio。

Milvus-standalone容器使用默认设置为本地19530端口提供服务，并将其数据映射到当前文件夹中

打开attu的客户端界面：

▲ 不安全 39.100.64.14:8080

欢迎来到 Milvus!

数据库 (1) +

default

Collection 数量

0

创建时间

2025/9/5 20:51:08

系统信息

2.6.1

Milvus Version

STANDALONE

部署模式

32.00 分钟

运行时间

1

用户

2

角色

三、启动安全认证

a、下载数据库配置文件

代码块

1 wget https://raw.githubusercontent.com/milvus-

io/milvus/v2.6.0/configs/milvus.yaml

2 # 如果下载不了，可以用windows下载，然后在上传到服务器。

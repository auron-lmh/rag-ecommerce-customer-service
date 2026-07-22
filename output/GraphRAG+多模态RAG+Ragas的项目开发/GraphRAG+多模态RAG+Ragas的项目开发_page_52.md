## 第50页

b、编辑配置文件: vi /etc/milvus.yaml

# The default value is 0, which means the caller will perform write operations directl

rriter thread pool.

# In this case, the maximum concurrency of disk write operations is determined by the

diskWriteNumThreads: 0

security:

# The superusers will ignore some system check processes,

# like the old password verification when updating the credential

superUsers: root

# default password for root user. The maximum length is 72 characters.

# Large numeric passwords require double quotes to avoid yaml parsing precision issu

defaultRootPassword: Milvus

rootShouldBindRole: false # Whether the root user should bind a role when the author

enablePublicPrivilege: true # Whether to enable public privilege

rbac:

overrideBuiltInPrivilegeGroups:

c、修改安装文件docker-compose.yml

在 docker-compose.yml 中, 在每个 milvus-standalone 下添加 volumes 部分。

将 milvus.yaml 文件的本地路径映射到所有 volumes 部分下配置文

件 /milvus/configs/milvus.yaml 的相应 docker 容器路径上。

standalone:

container_name: milvus-standalone

image: milvusdb/milvus:v2.6.0

security_opt:

- seccomp:unconfined

environment:

ETCD_ENDPOINTS: etcd:2379

MINIO_ADDRESS: minio:9000

MQ_TYPE: woodpecker

volumes:

- /etc/milvus.yaml:/milvus/configs/milvus.yaml

healthcheck:

interval: 30s

start_period: 90s

timeout: 20s

retries: 3

ports:

d、重启Milvus数据库

启动attu客户端容器。打开浏览器，输入用户名和密码（两种都行）。

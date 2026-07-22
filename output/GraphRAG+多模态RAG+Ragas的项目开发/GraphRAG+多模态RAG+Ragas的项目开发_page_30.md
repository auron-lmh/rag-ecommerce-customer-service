## 第29页

第四章、Neo4j+Langchain开发GraphRAG

代码块

三、然后通过执行Cypher的命令来验证安装插件是否成功:

一定要重启Neo4j的数据库服务器：systemctl restart neo4j

ready to start consuming query after 106 ms, results consumed after another 526 ms

neo4j@neo4j> RETURN apoc.version();

apoc.version()

"5.26.8"

1 row

ready to start consuming query after 52 ms, results consumed after another 1 ms

neo4j@neo4j> :quit;

修改配置文件

# Leaving this unconfigured will load all procedures found.

dbms.security.procedures.allowlist=apoc.*

# A comma separated list of procedures to be loaded by default.

dbms.security.procedures.unrestricted=apoc.*

# A comma separated list of procedures and user defined functions that are allowed

# full access to the database through unsupported/insecure internal APIs.

二、修改Neo4j的配置文件：vi /etc/neo4j/neo4j.conf

/var/lib/neo4j/plugins

名称

apoc-5.26.8-core.jar

README.txt

大小

类型

修改时间

2.83MB

2KB

Execut...

文本文档

2025/8/22, 18:17

2025/6/9, 6:59

密码

39.100.64.14

用户名

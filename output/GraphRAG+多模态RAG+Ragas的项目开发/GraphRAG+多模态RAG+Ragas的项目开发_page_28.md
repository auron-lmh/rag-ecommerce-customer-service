## 第27页

[--history HISTORY-BEHAVIOUR] [--notifications] [--idle-timeout IDLE-TIMEOUT]

连接参数

选项

-a ADDRESS, --address ADDRESS, --uri ADDRESS

-u USERNAME, --username USERNAME

--impersonate IMPERSONATE

-p PASSWORD, --password PASSWORD

-d DATABASE, --database DATABASE

描述

要连接的地址和端口。默认为 neo4j://localhost:7687。也可以使用环

量 NEO4J_ADDRESS 或 NEO4J_URI 指定。

连接时使用的用户名。也可以使用环境变量 NEO4J_USERNAME 指定。

要模拟的用户。

连接密码。也可以使用环境变量 NEO4J_PASSWORD 指定。

是否应加密与 Neo4j 的连接。这必须与 Neo4j 的配置一致。如果选择

'default', 加密设置将从指定的地址推断。例如, 'neo4j+ssc' 协议使用

密。

要连接的数据库。也可以使用环境变量 NEO4J_DATABASE 指定。

访问模式。默认为 WRITE。

Aug 09 19:31:10 iZ8vb5acpt0ebqsuf5mtiwZ neo4j[15226]: 2025-08-09 11:31:10.189+0000 INFO Started.

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# cypher-shell -u neo4j -p 1qaz3edc

Connected to Neo4j using Bolt protocol version 5.8 at neo4j://localhost:7687 as user neo4j.

Type :help for a list of available commands or :exit to exit the shell.

Note that Cypher queries must end with a semicolon.

neo4j@neo4j>

默认数据库：Neo4j社区版安装后会自动创建两个数据库： system （系统数据库）和 neo4j （默
认用户数据库）。社区版不支持通过Cypher命令（如 CREATE DATABASE）直接创建新数据库，这
是企业版的功能。社区版一次只能激活一个用户数据库（默认为 neo4j），无法同时运行多个用户数
据库

认用户数据库）。社区版不支持通过Cypher命令（如 CREATE DATABASE）直接创建新数据库，这
是企业版的功能。社区版一次只能激活一个用户数据库（默认为 neo4j），无法同时运行多个用户数
据库

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# cypher-shell -u neo4j -p 1qaz3edc

Connected to Neo4j using Bolt protocol version 5.8 at neo4j://localhost:7687 as user neo4j.

Type :help for a list of available commands or :exit to exit the shell.

Note that Cypher queries must end with a semicolon.

neo4j@neo4j> show databases;

| name | type | aliases | access | address | role | writer | requestedStatus | currentStat

sage | default | home | constituents |

| TRUE | TRUE | [] |

| FALSE | FALSE | [] |

2 rows

ready to start consuming query after 12 ms, results consumed after another 2 ms

neo4j@neo4j> create database customers;

Unsupported administration command: create database customers

neo4j@neo4j>

:exit 或 :quit

直接输入这些命令可立即退出 cypher-shell 会话

代码块

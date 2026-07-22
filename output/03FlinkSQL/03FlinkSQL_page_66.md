## 第66页

## 13. FlinkSQL on Hive

## 13.1. Catalog

- Catalog 提供了元数据信息，例如数据库、表、分区、视图以及数据库或其他外部系统中存储的函数和信息。

- 数据处理最关键的方面之一是管理元数据。

- 元数据可以是临时的，例如临时表、或者通过 TableEnvironment 注册的 UDF。

- 元数据也可以是持久化的，例如 Hive Metastore 中的元数据。

- Catalog 提供了一个统一的API，用于管理元数据，并使其可以从 Table API 和 SQL 查询语句中来访问。

- Catalog类型

- o.

Catalog

GenericInMemoryCatalog

JdbcCatalog

HiveCatalog

用户自定义 Catalog

- GenericInMemoryCatalog

- ▪ 基于内存实现，所有元数据只在 session 的生命周期内可用

- JdbcCatalog

- ▪ 可以将 Flink 通过 JDBC 协议连接到关系数据库。Postgres Catalog 和 MySQL Catalog 是目前 Jdbc Catalog 仅有的两种实现

$$
\begin{align*} &"\ deptno INT NOT NULL",+\\ &"\ dname STRING",+\\ &"\ loc STRING"+\\ ) WITH ("+\\ &"'connector' = 'mysql-cdc',"+\\ &"'hostname' = '192.168.88.101',"+\\ &"'port' = '3306',"+\\ &"'username' = 'root',"+\\ &"'password' = '123456',"+\\ &"'database-name' = 'scott',"+\\ &"'table-name' = 'dept'"+\\ ")"\\ tableEnv.executesql(sourceDDL)\\ tableEnv.executesql("select * from flink_cdc_dept").print()\\ \end{align*}
$$

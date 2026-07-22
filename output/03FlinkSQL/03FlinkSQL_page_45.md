## 第45页

- 利用 ROW_NUMBER()函数为每一行数据聚合得到一个排序之后的行号。

- 行号重命名为 row_num，并在外层的查询中以row_num <= N 作为条件进行筛选，就可以得到根据排序字段统计的 Top N 结果了

- Flink SQL 专门用 OVER 聚合做了优化实现。所以只有在 Top N 的应用场景中，OVER 窗口 ORDER BY后才可以指定其它排序字段；而要想实现 Top N，就必须按照上面的格式进行定义，否则 Flink SQL 的优化器将无法正常解析。而且，目前 Table API 中并不支持 ROW_NUMBER()函数，所以也只有 SQL 中这一种通用的 Top N 实现方式

//执行环境

StreamExecutionEnvironment environment = StreamExecutionEnvironment.getExecutionEnvironment();

environment.setParallelism(1);

StreamTableEnvironment tableEnvironment = StreamTableEnvironment.create(environment);

//执行SQL

tableEnvironment.executeSql("CREATE TABLE t_goods (\n" +

' gid STRING,\n' +

' type INT,\n' +

' price INT,\n' +

' ts AS localtimestamp,\n' +

' WATERMARK FOR ts AS ts - INTERVAL '5'

SECOND\n' +

')

WITH (\n' +

' 'connector' = 'datagen',\n' +

' 'rows-per-second'='1',\n' +

SELECT ...

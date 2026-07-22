## 第3页

## 编程模型

- 创建FlinkSql 运行环境

- 将数据源定义（映射）成表（视图）

- 执行sql 语义的查询（sql 语法或者 tableapi）

- 将查询结果输出到目标表

import org.apache.flink.table.api.*;

import org.apache.flink.connector.datagen.table.DataGenOptions;

// Create a TableEnvironment for batch or streaming execution.

// See the "Create a TableEnvironment" section for details.

TableEnvironment tableEnv = TableEnvironment.create(/.../);

// Create a source table

tableEnv.createTemporaryTable("SourceTable",

Tabledescriptor.forConnector("datagen")

.schema(Schema.newBuilder()

.column("f0", DataTypes.STRING())

.build())

.option(DataGenOptions.ROWS_PER_SECOND,

100)

.build());

// Create a sink table (using SQL DDL)

tableEnv.executeSql("CREATE TEMPORARY TABLE SinkTable WITH ('connector' = 'blackhole') LIKE SourceTable");

// Create a Table object from a Table API query

Table table2 = tableEnv.from("SourceTable");

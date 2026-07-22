## 第70页

- 优化的逻辑查询计划

- 物理执行计划.

- 使用 Table.explain() 方法的相应输出:

StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
StreamTableEnvironment tEnv = StreamTableEnvironment.create(env);

DataStream<Tuple2<Integer, String>> stream1 = env.fromElements(new Tuple2<>(1, "hello"));
DataStream<Tuple2<Integer, String>> stream2 = env.fromElements(new Tuple2<>(1, "hello"));

// explain Table API
Table table1 = tEnv.fromDataStream(stream1, $("count"), $("word"));
Table table2 = tEnv.fromDataStream(stream2, $("count"), $("word"));
Table table = table1
.where($("word").like("r%"))
.unionAll(table2);

System.out.println(table.explain());

- 使用 StatementSet.explain() 的多 sink 计划的相应输出:

EnvironmentSettings settings = EnvironmentSettings.inStreamingMode();
TableEnvironment tEnv = TableEnvironment.create(settings);

final Schema schema = Schema.newBuilder()
.column("count", DataTypes.INT())
.column("word", DataTypes.STRING())
.build();

tEnv.createTemporaryTable("MySource1",
TableDescriptor.forConnector("filesystem")
.schema(schema)
.option("path", "/source/path1")
.format("csv")
.build());

tEnv.createTemporaryTable("MySource2",
TableDescriptor.forConnector("filesystem")
.schema(schema)
.option("path", "/source/path2")
.format("csv")
.build());

tEnv.createTemporaryTable("MySink1",
TableDescriptor.forConnector("filesystem")
.schema(schema)
.option("path", "/sink/path1")
.format("csv")
.build());

tEnv.createTemporaryTable("MySink2",
TableDescriptor.forConnector("filesystem")
.schema(schema)
.option("path", "/sink/path2")
.format("csv")
.build());

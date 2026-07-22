## 第44页

streamTableEnvironment tableEnvironment = StreamTableEnvironment.create(environment);

//执行SQL

tableEnvironment.executeSql("CREATE TABLE t_goods (\n" +

" gid STRING,\n" +

" type INT,\n" +

" price INT,\n" +

" ts AS localtimestamp,\n" +

" WATERMARK FOR ts AS ts - INTERVAL '5'

SECOND\n" +

) WITH (\n" +

'connector' = 'datagen',\n" +

'rows-per-second'=1,\n" +

'fields.gid.length'=10,\n" +

'fields.type.min'=1,\n" +

"fields.type.max'=5,\n" +

"fields.price.min'=1,\n" +

"fields.price.max'=9\n" +

// tableEnvironment.sqlQuery("select * from t_goods").execute().print();

//开窗聚合计算--时间范围

// tableEnvironment.sqlQuery("select t.*,avg(price) OVER(" +

"PARTITION BY type " +

"ORDER BY ts " +

"RANGE BETWEEN INTERVAL '10' SECONDS PRECEDING AND

" from t_goods t").execute().print();

//开窗聚合计算--计数范围

tableEnvironment.sqlQuery("select t.*,avg(price) OVER(" +

"PARTITION BY type " +

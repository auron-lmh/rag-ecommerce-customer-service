## 第46页

## 8.3.2. 窗口Top N

public static void main(String[] args) throws Exception {

// 1. 创建一个表执行环境

StreamExecutionEnvironment env =

StreamExecutionEnvironment.getExecutionEnvironment();

StreamTableEnvironment tableEnv = StreamTableEnvironment.create(env);

env.setParallelism(1);

env.getConfig().setAutowatermarkInterval(100); // 100毫秒生成一次水位线

SingleOutputStreamOperator<Event> streamOperator = env.addSource(new

ClickSource())

// 乱序流的WaterMark生成

.assignTimestampsAndWatermarks(WatermarkStrategy

<Event-forBoundedOutOfOrderness(Duration.ofSeconds(2)) // 延迟2秒保证数据正确

.withTimestampAssigner(new

SerializableTimestampAssigner<Event>() {

@Override // 时间戳的提取器

public long

extractTimestamp(Event event, long l) {

return event.getTimestamp();

}

)

Table clickTable = tableEnv.fromDataStream(streamOperator, $"user"),

$("url"), $("timestamp").as("ts")

, $("et").rowtime());

// 将表注册到表环境中

tableEnv.createTemporaryView("clickTable", clickTable);

* 第一步 根据每个用户分组求出其访问量 并且设置窗口 A = select user,

count(url) as cnt, window_start, window_end from table ( tumble(table

clickTable,DESCRIPTOR(et), INTERVAL '10' SECOND ) ) group by user,

window_start, window_end;

* 第二步 row_number排名 并根据窗口分组 B = select *, row_number() over

( partition by window_start, window_end order by cnt DESC ) as rank_num from

( A );

* 第三步 where过滤 select user, cnt, rank_num from B where rank_num

<= 3;

*/

String subQuery = "select user, count(url) as cnt, window_start,

window_end " +

"from table( tumble(table clickTable,DESCRIPTOR(et), INTERVAL '10'

SECOND ) ) " +

"group by user, window_start, window_end";

Table table = tableEnv.sqlQuery("select user, cnt, rank_num from ( " +

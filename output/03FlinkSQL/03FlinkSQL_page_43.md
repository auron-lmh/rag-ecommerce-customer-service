## 第43页

而开窗函数是对每行都要做一次开窗聚合，因此聚合之后表中的行数不会有任何减少，是一个“多对多”的关系

与标准 SQL 中一致，Flink SQL 中的开窗函数也是通过 OVER 子句来实现的，所以有时开窗聚合也叫作“OVER 聚合”（Over Aggregation）。

- 基本语法如下:

$$
SELECT
<聚合函数> OVER (
[PARTITION BY <字段 1>[, <字段 2>, ...]]
ORDER BY <时间属性字段>
<开窗范围>),
...
FROM ...
$$

- OVER 关键字前面是一个聚合函数，它会应用在后面 OVER 定义的窗口上。

- PARTITION BY (可选)

- 用来指定分区的键（key），类似于 GROUP BY 的分组，这部分是可选的

- ORDER BY

- OVER 窗口是基于当前行扩展出的一段数据范围，选择的标准可以 基于时间也可以基于数量。

- 数据都应该是以某种顺序排列好的；而表中的数据本身是无序的。

- 在 Flink 的流处理中，目前只支持按照时间属性的升序排列，所以这里 ORDER BY 后面的字段必须是定义好的时间属性

- 开窗范围

- 对于开窗函数而言，还有一个必须要指定的就是开窗的范围，也就是到底要扩展多少行来做聚合。

- 这个范围是由 BETWEEN <下界> AND <上界> 来定义的，也就是“从下界到上界”的范围。

- 目前支持的上界只能是 CURRENT ROW，也就是定义一个“从之前某一行到当前行”的范围

- 开窗选择的范围可以基于时间，也可以基于数据的数量。所以开窗范围还应该在两种模式之间做出选择:

- 范围间隔 (RANGE intervals)

- 行间隔 (ROW intervals)

- 范围间隔

- 范围间隔以 RANGE 为前缀，就是基于 ORDER BY 指定的时间字段去选取一个范围，一般就是当前行时间戳之前的一段时间。

- 例如开窗范围选择当前行之前 1 小时的数据：

- RANGE BETWEEN INTERVAL '1' HOUR PRECEDING AND CURRENT ROW

- 行间隔

- 行间隔以 ROWS 为前缀，就是直接确定要选多少行，由当前行出发向前选取就可以了。

- 例如开窗范围选择当前行之前的 5 行数据

- ROWS BETWEEN 5 PRECEDING AND CURRENT ROW

$$
public static void main(String[] args) {
//执行环境
StreamExecutionEnvironment environment = StreamExecutionEnvironment.getExecutionEnvironment();
environment.setParallelism(1);
$$

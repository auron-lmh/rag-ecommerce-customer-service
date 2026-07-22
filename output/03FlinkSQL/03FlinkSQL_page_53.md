## 第53页

- 用户在 Flink 中可以通过精确、模糊两种引用方式引用函数。

- 精确函数引用允许用户跨 Catalog，跨数据库调用 Catalog 函数。

$$
例如：select mycatalog.mydb.myfunc(x) from mytable 和 select
$$

$$
mydb.myfunc(x) from mytable。
$$

- 在模糊函数引用中，用户只需在 SQL 查询中指定函数名。

$$
例如：select myfunc(x) from mytable。
$$

## 11.2. 系统函数

- Flink Table API &amp; SQL 为用户提供了一组内置的数据转换函数。

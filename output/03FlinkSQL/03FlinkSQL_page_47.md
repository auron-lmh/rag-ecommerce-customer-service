## 第47页

$$
select *, row_number() over ( partition by window_start, window_end order by cnt DESC ) as rank_num
$$

$$
from ( '' + subQuery + '' )'' +
$$

tableEnv.toChangelogStream(table).print();

env.execute();

## 8.4. Join

与标准 SQL 一致，Flink SQL 的常规联结也可以分为内联结（INNER JOIN）和外联结（OUTER JOIN），区别在于结果中是否包含不符合联结条件的行。

目前仅支持“等值条件”作为联结条件，也就是关键字 ON 后面必须是判断两表中字段相等的逻辑表达式

## 8.4.1. 等值内联结

内联结用 INNER JOIN 来定义，会返回两表中符合联接条件的所有行的组合，也就是所谓的笛卡尔积（Carterisan product）。

目前仅支持等值联结条件

$$
SELECT *
$$

$$
FROM Order
$$

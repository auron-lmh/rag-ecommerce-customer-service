## 第39页

## 8.1.1. Group Set

- 在一个GROUP BY查询中，根据不同的维度组合进行聚合。GROUPING SETS就是一种将多个GROUP BY逻辑UNION在一起。GROUPING SETS会把在单个GROUP BY逻辑中没有参与GROUP BY的的那一列置为NULL值。空分组集意味着所有行都聚合到一个组中

$$
tableEnvironment.sqlQuery("SELECT pid, cid, xid, sum(num) AS total\n" +
"FROM (VALUES\n" +
" ('省1', '市1', '县1',100),\n" +
" ('省1', '市2', '县2',101),\n" +
" ('省1', '市2', '县1',102),\n" +
" ('省2', '市1', '县4',103),\n" +
" ('省2', '市2', '县1',104),\n" +
" ('省2', '市2', '县1',105),\n" +
" ('省3', '市1', '县1',106),\n" +
" ('省3', '市2', '县1',107),\n" +
" ('省3', '市2', '县2',108),\n" +
" ('省4', '市1', '县1',109),\n" +
" ('省4', '市2', '县1',110))\n" +
"AS t_person_num(pid, cid, xid,num)\n" +
"GROUP BY GROUPING SETS ((pid, cid, xid),(pid, cid),(pid),

())).execute().print();
$$

| pid | total |
|---|---|
| 省1 | 303 |
| 省3 | 321 |
| 省2 | 312 |
| 省4 | 219 |

| xid | pid | cid | total |
|---|---|---|---|
|  | 省1 | 市2 |  |
| 县2 |  | 市2 | 101 |
| 县1 |  | 市2 | 209 |

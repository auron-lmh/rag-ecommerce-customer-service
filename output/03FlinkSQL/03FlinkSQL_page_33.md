## 第33页

- 第一个查询是一个简单的 GROUP-BY COUNT 聚合查询。它基于 user 字段对 clicks 表进行分组，并统计访问的 URL 的数量。

- 当查询开始，clicks 表(左侧)是空的。当第一行数据被插入到 clicks 表时，查询开始计算结果表。

- 第一行数据 [Mary, /home] 插入后，结果表(右侧，上部)由一行 [Mary, 1] 组成。

- 第二行 [Bob, /cart] 插入到 clicks 表时，查询会更新结果表并插入了一行新数据 [Bob, 1]。

- 第三行 [Mary, /prod?id=1] 将产生已计算的结果行的更新, [Mary, 1] 更新成 [Mary, 2]。

- 第四行数据加入 clicks 表时，查询将第三行 [Liz, 1] 插入到结果表中。

| user | cTime | url |
|---|---|---|
| Mary | 12:00:00 | /home |
| Bob | 12:00:00 | /cart |
| Mary | 12:02:00 | /prod?id=1 |
| Mary | 12:55:00 | /prod?id=4 |
| Liz | 13:01:00 | /prod?id=5 |
| Liz | 13:30:00 | /home |
| Mary | 14:00:00 | /cart |
| Liz | 14:02:00 | /home |
| Bob | 14:30:00 | /prod?id=3 |
| Bob | 14:40:00 | /home |

$$
SELECT
  user,
  TUMBLE_END(
    cTime,
    INTERVAL '1' HOURS
  ) AS endT,
  COUNT(url) AS cnt
FROM clicks
GROUP BY
  user,
  TUMBLE(
    cTime,
    INTERVAL '1' HOURS
  )
$$

| user | endT | cnt |
|---|---|---|
| Mary | 13:00:00 | 3 |
| Bob | 13:00:00 | 1 |
| Liz | 14:00:00 | 2 |
| Mary | 15:00:00 | 1 |
| Bob | 15:00:00 | 2 |
| Liz | 15:00:00 | 1 |

- 第一个查询是一个简单的 GROUP-BY COUNT 聚合查询。它基于 user 字段对 clicks 表进行分组，并统计访问的 URL 的数量。

## 第77页

## 14.3.4. distinct 聚合过滤

- 在某些情况下，用户可能需要从不同维度计算 UV（独立访客）的数量，例如来自 Android 的 UV、iPhone 的 UV、Web 的 UV 和总 UV。很多人会选择 CASE WHEN

$$
\text{SELECT}
$$

$$
day,
$$

$$
COUNT(DISTINCT user_id) AS total_uv,
$$

$$
COUNT(DISTINCT CASE WHEN flag IN ('android', 'iphone') THEN user_id ELSE NULL END) AS app_uv,
$$

$$
COUNT(DISTINCT CASE WHEN flag IN ('wap', 'other') THEN user_id ELSE NULL END) AS web_uv
$$

$$
FROM T
$$

$$
GROUP BY day
$$

- 在这种情况下，建议使用 FILTER 语法而不是 CASE WHEN。因为 FILTER 更符合 SQL 标准，并且能获得更多的性能提升。FILTER 是用于聚合函数的修饰符，用于限制聚合中使用的值。将上面的示例替换为 FILTER 修饰符

$$
\text{SELECT}
$$

$$
day,
$$

$$
COUNT(DISTINCT user_id) AS total_uv,
$$

$$
COUNT(DISTINCT user_id) FILTER (WHERE flag IN ('android', 'iphone')) AS app_uv,
$$

$$
COUNT(DISTINCT user_id) FILTER (WHERE flag IN ('wap', 'other')) AS web_uv
$$

$$
FROM T
$$

$$
GROUP BY day
$$

## 15. 附录

- 代码实现

$$
// instantiate table environment
$$

$$
TableEnvironment tEnv = ...;
$$

$$
tEnv.getConfig()
$$

$$
.set("table.optimizer.distinct-agg.split.enabled", "true"); // enable distinct agg split
$$

Local-Global Agg

Distinct-Split Agg

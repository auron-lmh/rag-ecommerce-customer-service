## 第76页

## 14.3.3. 拆分 distinct 聚合

- Local-Global 优化可有效消除常规聚合的数据倾斜，例如 SUM、COUNT、MAX、MIN、AVG。但是在处理 distinct 聚合时，其性能并不令人满意。

- 例如，如果我们要分析今天有多少唯一用户登录。我们可能有以下查询:

SELECT day, COUNT(DISTINCT user_id)

FROM T

GROUP BY day

- 如果 distinct key（即 user_id）的值分布稀疏，则 COUNT DISTINCT 不适合减少数据。即使启用了 local-global 优化也没有太大帮助。因为累加器仍然包含几乎所有原始记录，并且全局聚合将成为瓶颈（大多数繁重的累加器由一个任务处理，即同一天）。

- 这个优化的想法是将不同的聚合（例如 COUNT(DISTINCT col)）分为两个级别。第一次聚合由 group key 和额外的 bucket key 进行 shuffle。bucket key 是使用 HASH_CODE(distinct_key) % BUCKET_NUM 计算的。BUCKET_NUM 默认为 1024，可以通过 table.optimizer.distinct-agg.split.bucket-num 选项进行配置。第二次聚合是由原始 group key 进行 shuffle，并使用 SUM 聚合来自不同 buckets 的 COUNT DISTINCT 值。由于相同的 distinct key 将仅在同一 bucket 中计算，因此转换是等效的。bucket key 充当附加 group key 的角色，以分担 group key 中热点的负担。bucket key 使 job 具有可伸缩性来解决不同聚合中的数据倾斜/热点。

- 拆分 distinct 聚合后，以上查询将被自动改写为以下查询:

SELECT day, SUM(cnt)

FROM (

SELECT day, COUNT(DISTINCT user_id) as cnt

FROM T

GROUP BY day, MOD(HASH_CODE(user_id), 1024)

)

GROUP BY day

•

// instantiate table environment

TableEnvironment tEnv = ...;

// access flink configuration

Configuration configuration = tEnv.getConfig().getConfiguration();

// local-global aggregation depends on mini-batch is enabled

configuration.setString("table.exec.mini-batch.enabled", "true");

configuration.setString("table.exec.mini-batch.allow-latency", "5 s");

configuration.setString("table.exec.mini-batch.size", "5000");

// enable two-phase, i.e. local-global aggregation

configuration.setString("table.optimizer.agg-phase-strategy", "TWO_PHASE");

);

例如，如果我们要分析今天有多少唯一用户登录。我们可能有以下查询:

SELECT day, COUNT(DISTINCT user_id)

FROM T

GROUP BY day

如果 distinct key（即 user_id）的值分布稀疏，则 COUNT DISTINCT 不适合减少数据。即使启用了 local-global 优化也没有太大帮助。因为累加器仍然包含几乎所有原始记录，并且全局聚合将成为瓶颈（大多数繁重的累加器由一个任务处理，即同一天）。

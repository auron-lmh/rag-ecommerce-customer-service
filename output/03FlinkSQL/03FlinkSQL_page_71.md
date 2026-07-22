## 第71页

## 14.2. Query Optimization

Apache Flink 使用并扩展了 Apache Calcite 来执行复杂的查询优化。其中包括两种优化器:

- RBO (基于规则的优化器)

- CBO (基于成本的优化器)

- 优化方案:

- 基于 Apache Calcite 的子查询解相关

- 投影下推 (Projection Pushdown)

- 分区剪裁 (Partition Prune)

- 谓词下推 (Predicate Pushdown)

- 常量折叠 (Constant Folding)

- 子计划消除重复数据以避免重复计算

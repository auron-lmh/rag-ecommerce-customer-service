## 第73页

## 14.2.4. Hash Join

- 根据代价 cost 选择批处理 join 有方式(sortmergejoin, hashjoin, broadcasthashjoin).

- 比如前面例子，再 filter 下推之后，在 t2.id<1000 的情况下，由 1 百万数据量变为了 1 千条，计算 cost 之后，使用 broadcasthashjoin 最合适。

Optimized Logical Plan

Physical Plan

## 14.2.5. Transformation Tree

Optimized Logical Plan

Physical Plan

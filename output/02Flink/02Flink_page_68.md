## 第68页

每个 Metric 都会分配一个标识符和一组键值对，用来报告 Metric。

Flink 的指标体系按树形结构划分，域相当于树上的顶点分支，表示指标大的分类。每个指标都会分配一个标识符，该标识符将基于 3 个组件进行汇报：

- 注册指标时用户提供的名称；

- 可选的用户自定义域；

- 系统提供的域。

- 例如:

- 如果 A.B 是系统域，C.D 是用户域，E 是名称，那么指标的标识符将是 A.B.C.D.E。

- 可以通过设置 conf/flink-conf.yaml 里面的 metrics.scope.delimiter 参数来配置标识符的分隔符(默认“.”)。

## 6.2.1. User Scope

定义 User Scope 的方法：

- 调用 MetricGroup#addGroup(String name)` `MetricGroup#addGroup(int name), MetricGroup#addGroup(String key, String value)。

- 这些方法会影响 MetricGroup#getMetricIdentifier 和 MetricGroup#getScopeComponents 的返回值。

// 创建 Metric 时指定 Scope

counter = getRuntimeContext()

.getMetricGroup()

.addGroup("MyMetrics")

.counter("myCounter");

counter = getRuntimeContext()

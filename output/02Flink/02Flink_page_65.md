## 第65页

通过flink metrics这些指标都可以获取到，避免任务的运行处于黑盒状态，通过分析这些指标，可以更好的调整任务的资源、定位遇到的问题、对任务进行监控。

- Flink Metrics 包含两大作用：

- 实时采集监控数据。在 Flink 的 UI 界面上，用户可以看到自己提交的任务状态、时延、监控信息等等。

- 对外提供数据收集接口。用户可以将整个 Flink 集群的监控数据主动上报至第三方监控系统，如：prometheus、grafana 等。

## 6.1. Metrics类别

Metric

Gauge

Histogram

Counter

Meter

- Flink一共提供了四种监控指标：分别为 Counter、Gauge、Histogram、Meter。

- ○ Gauge —— 最简单的度量指标，只是简单的返回一个值，比如当前实时读取kafka数据的条数

- ○ Counter —— 计数器，在一些情况下，会比Gauge高效，比如通过一个AtomicLong变量来统计一个队列的长度；

- ○ Histogram —— 度量值的统计结果，如最大值、最小值、平均值，以及分布情况等。

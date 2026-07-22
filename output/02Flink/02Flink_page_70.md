## 第70页

- 通过在 [conf/flink-conf.yaml] 中配置一个或多个 Reporter，可以将 Metric 暴露给外部系统。

- 这些 Reporter 在启动时实例化。

- metrics.reporter.<name>.<config>: Reporter 名称

- metrics.reporter.<name>.class: Reporter 实现类

- metrics.reporter.<name>.factory.class: Reporter 工厂类

- metrics.reporter.<name>.interval: Reporter 调用间隔

- metrics.reporter.<name>.scope.delimiter: Scope 标识符的分隔符（默认使用 metrics.scope.delimiter）

- metrics.reporter.<name>.scope.variables.excludes: 可选项，以 “,” 分隔的变量列表，可以忽略这些变量

- metrics.reporters: 可选项，以 “,” 分隔的 Reporter 名称列表，表示应用哪些 Reporter，默认会包含所有配置的 Reporter。

- Reporter 必须至少配置 class 或 factory.class 属性（使用哪个取决于 Reporter 的实现）。

- 配置示例

metrics.reporters: my_jmx_reporter,my_other_reporter

metrics.reporter.my_jmx_reporter.factory.class: org.apache.flink.metrics.jmx.JMXReporterFactory

metrics.reporter.my_jmx_reporter.port: 9020-9040

metrics.reporter.my_jmx_reporter.scope.variables.excludes:job_id;task_attempt_num

metrics.reporter.my_other_reporter.class: org.apache.flink.metrics.graphite.GraphiteReporter

metrics.reporter.my_other_reporter.host: 192.168.1.1

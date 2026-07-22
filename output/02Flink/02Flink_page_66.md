## 第66页

## 6.1.2. Gauge 指标瞬时值

Gauge是最简单的Metrics，它反映一个指标的瞬时值。比如要看现在TaskManager的JVM heap 内存用了多少，就可以每次实时的暴露一个 Gauge，Gauge 当前的值就是 heap 使用的量。

使用前首先创建一个实现 org.apache.flink.metrics.Gauge 接口的类。返回值的类型没有限制。您可以通过在 MetricGroup 上调用 gauge。

private transient int valueToExpose = 0;

@Override

getRuntimeContext()

## 6.1.3. Meter 平均值

用来记录一个指标在某个时间段内的平均值。Flink 中的指标有 Task 算子中的 numRecordsInPerSecond,记录此 Task 或者算子每秒接收的记录数。

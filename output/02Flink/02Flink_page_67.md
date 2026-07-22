## 第67页

## 6.1.4. Histogram 直方图

- Histogram 用于统计一些数据的分布，比如说 Quantile、Mean、StdDev、Max、Min 等，其中最重要一个是统计算子的延迟。此项指标会记录数据处理的延迟信息，对任务监控起到很重要的作用。

- 使用方式：通过调用 histogram(String name, Histogram histogram) 来注册一个 MetricGroup。

public class MyMapper extends RichMapFunction<Long, Long> {

private transient Histogram histogram;

@Override

public void open(Configuration config) {

this.histogram = getRuntimeContext()

.getMetricGroup()

.histogram("myHistogram", new MyHistogram());

@Override

public Long map(Long value) throws Exception {

this.histogram.update(value);

return value;

}

## 6.2. Metric Scope

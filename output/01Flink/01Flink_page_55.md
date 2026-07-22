## 第55页

## 10.3.4. Minor Defects

## 10.4. Time Window

时间窗口是最常用的窗口类型，又可以细分为滚动、滑动和会话三种。

翻滚窗口 (Tumbling Window, 无重叠)

滑动窗口 (Sliding Window, 有重叠)

会话窗口 (Session Window, 活动间隙)

除了Flink自定义的的，还可以继承 windowAssigner 类来实现自定义的 window assigner。

## 第56页

# 所有内置的 window assigner（除了 global window）都是基于时间分发数据的，

processing time 或 event time 均可。

## 10.4.1. Tumbling Window

滚动窗口的 assigner 分发元素到指定大小的窗口。滚动窗口的大小是固定的，且各自范围之间不

重叠。

比如说，如果你指定了滚动窗口的大小为 5 分钟，那么每 5 分钟就会有一个窗口被计算，且一个

新的窗口被创建（如下图所示）。

user 1

user 2

user 3

window 1 window 2 window 3 window 4 window 5

window size

time

## 10.4.2. Sliding Window

滑动窗口的 assigner 分发元素到指定大小的窗口，窗口大小通过 window size 参数设置。

滑动窗口需要一个额外的滑动距离（window slide）参数来控制生成新窗口的频率。

因此，如果 slide 小于窗口大小，滑动窗口可以允许窗口重叠。这种情况下，一个元素可能会被分

发到多个窗口。

比如说，你设置了大小为 10 分钟，滑动距离 5 分钟的窗口，你会在每 5 分钟得到一个新的窗口，

里面包含之前 10 分钟到达的数据（如下图所示）。

user 1

user 2

user 3

window 1 window 3

window 2

window 4

time

window size window slide

代码实现

import org.apache.flink.api.common.typeinfo.Types;

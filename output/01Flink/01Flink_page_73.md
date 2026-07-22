## 第73页

## 12.2.2. 无序流

由于乱序流中需要等待迟到数据到齐，所以必须设置一个固定量的延迟时间（Fixed Amount of

Lateness）。

调用 WatermarkStrategy. forBoundedOutOfOrderness()方法就可以实现。

这个方法需要传入一个 maxOutOfOrderness 参数，表示“最大乱序程度”

- Tips:

○ 当程序开始时,WaterMark会被设置为Long的最小值,以保证它不会丢数据

○ 当程序关闭时,WaterMark会被设置为Long的最大值,以保证它大到足以关闭所有已经开启的

窗口

- 代码实现

import com.yjxxt.util.KafkaUtil;

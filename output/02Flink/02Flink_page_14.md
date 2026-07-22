## 第14页

# 2. Flink 窗口联结

对于两条流的合并，很多情况我们并不是简单地将所有数据放在一起，而是希望根据某个字段的值将它们联结起来，“配对”去做处理。

## 2.1. Join

- join都是利用window的机制，即按照指定字段和（滚动/滑动/会话）窗口进行inner join

- 先将数据缓存在Window State中，当窗口触发计算时，执行join操作；

- 按照窗口的操作和类型可以分为：

- Tumbling Window Join、Sliding Window Join、Session Widow Join。

$$
Window Join
$$

$$
DataStream,DataStream→
$$

$$
DataStream
$$

$$
Join two data streams on a given key and a common window.
$$

$$
dataStream.join(otherStream)
$$

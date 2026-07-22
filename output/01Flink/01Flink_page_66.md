## 第66页

## 11.2. 全量窗口函数

## 11.2.1. ProcessWindowFunction

ProcessWindowFunction 是 Window API 中最底层的通用窗口函数接口。之所以说它“最底层”，

是因为除了可以拿到窗口中的所有数据之外，ProcessWindowFunction 还可以获取到一个“上下

文对象” (Context) 。

上下文对象非常强大，不仅能够获取窗口信息，还可以访问当前的时间和状态信息。这里的时间就

包括了处理时间 (processing time) 和事件时间水位线 (eventtime watermark) 。

全量窗口的好处是以牺牲性能和资源为代价的。作为一个全窗口函数，ProcessWindowFunction

同样需要将所有数据缓存下来、等到窗口触发计算时才使用。它其实就是一个增强版的

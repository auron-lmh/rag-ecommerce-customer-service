## 第61页

## 10.5. Global Windows

GlobalWindows作为一个全局的窗口分配器，它不像TimeWindow或CountWindow那样通过元素

个数来划分成一个个窗口，而是把分区内所有的元素分配到同一个窗口，所以说如果没有定义触发

器，那么整个subTask中就只有一个窗口，且一直存在，不会触发计算。

窗口模式仅在你指定了自定义的【trigger】时有用。否则，计算不会发生，因为全局窗口没有天

然的终点去触发其中积累的数据。

使用Global Windows需要非常慎重，用户需要非常明确自己在整个窗口中统计出的结果是什么，

并指定对应的触发器，同时还需要有指定相应的数据清理机制，否则数据将一直留在内存中。

window和windowAll都是对stream定义窗口的方法，都需要传入WindowAssigner（窗口分配

器）执行具体的开窗操作

window只能在已经分区的 KeyedStream 上定义，通过KeyedStream转化为

WindowedStream执行具体的开窗操作。

windowAll只能在未分区的DataStream上定义，调用windowAll方法后，会把DataStream转

化为AllWindowedStream，并得到全局统计结果。也就是说WindowAll并行度只能1，且不

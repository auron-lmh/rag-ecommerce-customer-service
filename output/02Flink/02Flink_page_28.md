## 第28页

## 3.2.2. 数据屏障

barrier

英 [ˈbæri]

美 [ˈbæriər]

n. 障碍；障碍，阻力；关障、分界线、隔阂；难以逾越的数量（或水平、数目）

- • 数据分割

data stream

newer records

checkpoint barrier n

older records

◦

checkpoint barrier n

checkpoint barrier n-1

stream record (event)

part of checkpoint n+1

part of checkpoint n

part of checkpoint n-1

- ◦ Flink 分布式快照里面的一个核心的元素就是流屏障（stream barrier）。这些屏障会被插入(injected)到数据流中，并作为数据流的一部分随着数据流动。屏障并不会持有任何数据，而是和数据一样线性的流动。可以看到屏障将数据流分成了两部分数据（实际上是多个连续的部分），一部分是当前快照的数据，一部分下一个快照的数据。每个快照会带有它的快照ID。这个快照的数据都在这个屏障的前面。

◦ 如果是多个输入数据流，多个数据流的屏障会被同时插入到数据流中。快照n的屏障被插入到数据流的点（我们称之为Sn），就是数据流中一直到某个位置（包含了当前时刻之前时间的所有数据），也就是包含的这部分数据的快照。举例来说，在Kafka中，这个位置就是这个分区的最后一记录的offset。这个位置Sn就会上报给 checkpoint 的协调器（Flink的

- ◦ 然后屏障开始向下流动。当一个中间的operator收到它的所有输入源的快照n屏障后，它就会向它所有的输出流发射一个快照n的屏障，一旦一个sink的operator收到所有输入数据流的

那么全局 Snapshot 就相当于下图中的蓝色部分。

那么全局 Snapshot 就相当于下图中的蓝色部分。

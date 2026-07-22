## 第76页

- 公⽤⼀个pool当接收上游数据时Decoder，往下游发送数据时Encoder,都会向pool中请求内存memorySegment

- 因为是公共pool，也就是说运⾏时，当接受的数据占⽤的内存多了，往下游发送的数据就少了

- ⽐如说你sink端堵塞了，背压了写不进去，那这个task.resultPatation无法发送数据了，也就无法释放memorySegment了，相应的⽤于接收数据的memorySegment就会越来越⼩，直到接收数据端拿不到memorySegment了，也就无法接收上游数据了，既然这个task无法接收数据了，⾃然引起这个task的上⼀个task数据发送端⽆法发送，那上⼀个task⼜反压了

- 所以这个反压从发⽣反压的地⽅，依次的往上游扩散直到source,这个就是flink的天然反压。

## • 反压处理阶段划分

- ○ 跨 TaskManager ，反压如何从 InputGate 传播到 ResultPartition

- ○ TaskManager 内，反压如何从 ResultPartition 传播到 InputGate

## 7.4.2. 跨TaskManager反压过程

跨TaskManager反压过程 1

跨TaskManager反压过程 2

跨TaskManager反压过程 3

跨TaskManager反压过程 4

## 第8页

## 1.4. 状态后端

Job

Manager

(master)

(workers)

Task

Manager

Trigger Checkpoint

Ack. Checkpoint

store state

snapshots

(snapshot store)

- State Backends 的作用就是用来维护State的。

- 有状态的流计算是Flink的一大特点，状态本质上是数据，数据是需要维护的，例如数据库就是维护数据的一种解决方案。

- 一个 State Backend 主要负责两件事：Local State Management(本地状态管理) 和 Remote State Checkpointing（远程状态备份）。

- Local State Management

- State Management 的主要任务是确保状态的更新和访问。

- State Backends 主要有两种形式的状态管理:

直接将 State 以对象的形式存储到JVM的堆上面

将 State 对象序列化后存储到 RocksDB 中

第一种存储到JVM堆中，因为是在内存中读写，延迟会很低，但State的大小受限于内存的大小；第二种方式存储到State Backends上（本地磁盘上），读写较内存会慢一些，

但不受内存大小的限制，同时因为state存储在磁盘上，可以减少应用程序对内存的占用。根据使用经验，对延迟不是特别敏感的应用，选择第二种方式较好，尤其是State比

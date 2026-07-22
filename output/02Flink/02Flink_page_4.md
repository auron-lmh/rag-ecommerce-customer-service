## 第4页

- 这就意味着对于一个并行子任务，占据了一个“分区”，它所处理的所有数据都会访问到相同的状 态，状态对于同一任务而言是共享的，

- 算子状态可以用在所有算子上，使用的时候其实就跟一个本地变量没什么区别——因为本地变量的作用域也没什么区别。在使用时，我们还需进一步实现CheckpointedFunction接口。

扩容时

checkpoint恢复

缩容时

checkpoint恢复

Func_1

List[s1,s2]

Func_2

List[s2]

Func_2

List[s3,s4]

Func_3

/

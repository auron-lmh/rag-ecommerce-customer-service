## 第32页

在反压时候 barrier 无法随着数据往下游流动，造成反压的时候无法做出 Checkpoint。但是其实在发生反压情况的时候，我们更加需要去做出对数据的Checkpoint，因为这个时候性能遇到了瓶颈，是更加容易出问题的阶段；

- Barrier 对齐阻塞数据处理：

- 阻塞对齐对于性能上存在一定的影响;

- 恢复性能受限于 Checkpoint 间隔：

- 在做恢复的时候，延迟受到多大的影响很多时候是取决于 Checkpoint 的间隔，间隔越大，需要 replay 的数据就会越多，从而造成中断的影响也会越大。

- 但是目前 Checkpoint 间隔受制于持久化操作的时间，所以没办法做的很快。

- 解决方案：Unaligned Checkpoint

- barrier 算子在到达 input buffer 最前面的时候，就会开始触发 Checkpoint 操作。它会立刻把 barrier 传到算子的 OutPut Buffer 的最前面，相当于它会立刻被下游的算子所读取到。通过这种方式可以使得 barrier 不受到数据阻塞，解决反压时候无法进行 Checkpoint 的问题。

- 当我们把 barrier 发下去后，需要做一个短暂的暂停，暂停的时候会把算子的 State 和 input output buffer 中的数据进行一个标记，以方便后续随时准备上传。对于多路情况会一直等到另外一路 barrier 到达之前数据，全部进行标注。

- 通过这种方式整个在做 Checkpoint 的时候，也不需要对 barrier 进行对齐，唯一需要做的停顿就是在整个过程中对所有 buffer 和 state 标注。这种方式可以很好的解决反压时无法做出 Checkpoint ，和 Barrier 对齐阻塞数据影响性能处理的问题。

Checkpoint barrier

Input buffers

Output buffers

- 差异

- Checkpoint的触发是在接收到第一个 Barrier[对不齐]时还是在接收到最后一个 Barrier[对齐]时。

- 是否需要阻塞已经接收到 Barrier 的 Channel 的计算。

Alignment checkpoint

Unalign checkpoint

On first barrier

Tag buffers and forward barrier

Checkpoint

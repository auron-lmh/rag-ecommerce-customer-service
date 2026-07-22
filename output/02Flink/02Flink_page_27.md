## 第27页

The distributed snapshot algorithm described here came about when I visited Chandy, who was then at the University of Texas in Austin. He posed the problem to me over dinner, but we had both had too much wine to think about it right then. The next morning, in the shower, I came up with the solution. When I arrived at Chandy's office, he was waiting for me with the same solution. I consider the algorithm to be a straightforward application of the basic ideas from Time, Clocks and the Ordering of Events in a Distributed System.

## Chandy-Lamport算法

- Initiating a snapshot: 也就是开始创建snapshot, 可以由系统中的任意一个进程发起

- 进程 PI 发起: 记录自己的进程状态，同时生产一个标识信息 marker, marker 和进程通信的 message 不同

- 将 marker 信息通过 ouput channel 发送给系统里面的其他进程

- 开始记录所有 input channel 接收到的 message

- Propagating a snapshot: 系统中其他进程开始逐个创建 snapshot 的过程

- 对于进程 Pj 从 input channel Ckj 接收到 marker 信息:

- 如果 Pj 还没有记录自己的进程状态，则

- Pj 记录自己的进程状态，同时将 channel Ckj 置为空

- 向 output channel 发送 marker 信息

- 否则

- 记录其他 channel 在收到 marker 之前的 channel 中收到所有 message

- Terminating a snapshot: 算法结束条件

- 所有的进程都收到 marker 信息并且记录下自己的状态和 channel 的状态（包含的消息)

- 案例

- 假设系统中包含两个进程 P1 和 P2，P1 进程状态包括三个变量 X1，Y1 和 Z1，P2 进程包括三个变量 X2，Y2 和 Z2。初始状态如下。

C12: [Empty]

X1: 0

Y1: 0

Z1: 0

C12: [Empty]

X1: 0

Y1: 0

Z1: 0

C12: [<marker>]

X1: 0

Y1: 0

Z1: 0

C12: [M1]

X2: 4

Y2: 2

Z2: 3

由 P1 发起全局 Snapshot 记录, P1 先记录本身的进程状态, 然后向 P2 发送 marker 信息。在 marker 信息到达 P2 之前, P2 向 P1 发送 message: M.

P2 收到 P1 发送过来的 marker 信息之后, 记录自己的状态。然后 P1 收到 P2 之前发送过来的消息: M。对于 P1 来说, 从 P2 channel 发送过来的信息相当于是 [M, marker], 由于 P1 已经做了 local snapshot, 所以 P1 需要记录消息 M。

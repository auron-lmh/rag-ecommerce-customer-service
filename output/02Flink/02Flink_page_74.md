## 第74页

# Flink网络传输的数据流向

- Flink的反压是通过TCP的反压机制来控制的

- Flink 在做网络传输的时候基本的数据的流向，发送端在发送网络数据前要经历自己内部的一个流程，会有一个自己的 Network Buffer，在底层用 Netty 去做通信，Netty 这一层又有属于自己的 ChannelOutbound Buffer，因为最终是要通过 Socket 做网络请求的发送，所以在 Socket 也有自己的 Send Buffer，同样在接收端也有对应的三级 Buffer。学过计算机网络的时候我们应该了解到，TCP 是自带流量控制的。实际上 Flink（before V1.5）就是通过 TCP 的流控机制来实现 feedback 的。

- since V1.5 使用 Credit-based 反压机制

## 7.4.1. TCP流控机制

16 bits

16 bits

Source Port

Destination Port

Sequence number

Acknowledgement number

Header

Length

(4bits)

Reserved

bits

(6 bits)

U

R

Window Size

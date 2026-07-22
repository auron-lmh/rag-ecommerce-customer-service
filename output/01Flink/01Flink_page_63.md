## 第63页

return t1;

//运行环境

environment.execute();

11. Flink Window Functions

定义了窗口分配器，我们知道了数据属于哪个窗口，可以将数据收集起来了；至于收集起来到底要

做什么，其实还完全没有头绪。

所以在窗口分配器之后，必须再接上一个定义窗口如何进行计算的操作，这就是所谓的“窗口函

数” (window functions)

Flink提供了两大类窗口函数，分别为增量聚合函数和全量窗口函数。

增量聚合函数(incremental aggregation functions)

窗口将数据收集起来，最基本的处理操作当然就是进行聚合。窗口对无限流的切分，可

以看作得到了一个有界数据集。如果我们等到所有数据都收集齐，在窗口到了结束时间

要输出结果的一瞬间再去进行聚合，显然就不够高效

为了提高实时性，我们可以再次将流处理的思路发扬光大：就像DataStream 的简单聚

合一样，每来一条数据就立即进行计算，中间只要保持一个简单的聚合状态就可以了;

区别只是在于不立即输出结果，而是要等到窗口结束时间。等到窗口到了结束时间需要

输出计算结果的时候，我们只需要拿出之前聚合的状态直接输出，这无疑就大大提高了

程序运行的效率和实时性。

典型的增量聚合函数有ReduceFunction、AggregateFunction。

全窗口聚合函数(full window functions)

典型的批处理思路了--养肥了再杀

全量窗口函数需要对所有进入该窗口的数据进行缓存，等到窗口触发时才会遍历窗口内

所有数据，进行结果计算。

因为有些场景下，我们要做的计算必须基于全部的数据才有效，这时做增量聚合就没什

么意义了；另外，输出的结果有可能要包含上下文中的一些信息（比如窗口的起始时

间），这是增量聚合函数做不到的。所以，我们还需要有更丰富的窗口计算方式，这就

可以用全窗口函数来实现。

全窗口函数也有两种：WindowFunction 和 ProcessWindowFunction。

11.1. 增量聚合函数

11.1.1. ReduceFunction

最基本的聚合方式就是归约 (reduce)

窗口函数中也提供了 ReduceFunction：只要基于 WindowedStream 调用.reduce()方法，然后传

入 ReduceFunction 作为参数，就可以指定以归约两个元素的方式去对窗口中数据进行聚合了。

ReduceFunction 可以解决大多数归约聚合的问题，但是这个接口有一个限制，就是聚合状态的类

型、输出结果的类型都必须和输入数据类型一样。

代码实现

import org.apache.flink.api.common.typeinfo.Types;

import org.apache.flink.api.java.tuple.Tuple2;

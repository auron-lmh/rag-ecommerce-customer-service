## 第81页

window operator包含四个组件，包括 window assigner，trigger，evictor，window process。

window assigner 指明数据流中的数据属于哪个window

trigger 指明在哪些条件下触发window计算，基于处理数据时的时间以及事件的特定属性

evictor 可选组件，在window执行计算前或后，将window中的数据移除，如使用

globalWindow时，由于该window的默认trigger为永不触发，所以既需要实现自定义

trigger，也需要实现evictor，移除部分已经计算完毕的数据。

window process flink默认提供的有 ReduceFunction,AggagateFunction.还可以自定义实

现 windowProcessFunction

窗口触发器，决定了窗口什么时候使用窗口函数处理窗口内元素。每个窗口分配器都带有一个默认

的触发器。

Trigger 决定了一个窗口（由 window assigner 定义）何时可以被 window function 处理。每个

windowAssigner 都有一个默认的 Trigger。

如果默认 trigger 无法满足你的需要，可以在 trigger(... ) 调用中指定自定义的 trigger。

Trigger 接口提供了五个方法来响应不同的事件:

onElement() 方法在每个元素被加入窗口时调用。

onEventTime() 方法在注册的 event-time timer 触发时调用。

onProcessingTime() 方法在注册的 processing-time timer 触发时调用。

onMerge() 方法与有状态的 trigger 相关。该方法会在两个窗口合并时，将窗口对应

trigger 的状态进行合并，比如使用会话窗口时。

clear() 方法处理在对应窗口被移除时所需的逻辑。

前三个方法通过返回 TriggerResult 来决定 trigger 如何应对到达窗口的事件。应对方案有以下

几种:

public enum TriggerResult {

// 表示对窗口不执行任何操作。即不触发窗口计算，也不删除元素。

CONTINUE(false, false),

// 触发窗口计算，输出结果，然后将窗口中的数据和窗口进行清除。

FIRE_AND_PURGE(true, true),

// 触发窗口计算，但是保留窗口元素

FIRE(true, false),

// 不触发窗口计算，丢弃窗口，并且删除窗口的元素。

PURGE(false, true);

private final boolean fire;

private final boolean purge;

private TriggerResult(boolean fire, boolean purge) {

this.purge = purge;

this.fire = fire;

}

windowAssigner 默认的 Trigger 足以应付诸多情况。

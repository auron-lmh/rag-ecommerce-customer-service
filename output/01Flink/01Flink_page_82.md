## 第82页

EventTimeTrigger：通过对比EventTime和窗口的Endtime确定是否触发窗口计算，如果

EventTime大于Window EndTime则触发，否则不触发，窗口将继续等待。

ProcessTimeTrigger：通过对比ProcessTime和窗口EndTime确定是否触发窗口，如果

ProcessTime大于EndTime则触发计算，否则窗口继续等待。

ContinuousEventTimeTrigger：根据间隔时间周期性触发窗口或者Window的结束时间小于

当前EndTime触发窗口计算。

ContinuousProcessingTimeTrigger：根据间隔时间周期性触发窗口或者Window的结束时间

小于当前ProcessTime触发窗口计算。

CountTrigger：根据接入数据量是否超过设定的阈值判断是否触发窗口计算。

DeltaTrigger：根据接入数据计算出来的Delta指标是否超过指定的Threshold去判断是否触

发窗口计算。

PurgingTrigger：可以将任意触发器作为参数转换为Purge类型的触发器，计算完成后数据将

被清理。

NeverTrigger：任何时候都不触发窗口计算

内置Trigger

说明

ProcessingTimeTrigger 一次触发，machine time大于窗口结束时间时触发

EventTimeTrigger 一次触发，watermark大于窗口结束时间时触发

ContinuousProcessingTimeTrigger 多次触发，基于processing time的固定时间间隔

ContinuousEventTimeTrigger 多次触发，基于event time的固定时间间隔

CountTrigger 多次触发，基于element的固定条数

DeltaTrigger 多次触发，当前element与上次触发trigger的element做delta计算，超

过threshold时触发

PurgingTrigger trigger wrapper，当nested trigger触发时，额外会清理窗口当前的中

间状态

14.2. Evictor

Flink 窗口模型还允许在窗口分配器和触发器之外指定一个可选的驱逐器(Evictor)

驱逐器能够在触发器触发之后，窗口函数使用之前或之后从窗口中清除元素。

evictBefore()在窗口函数之前使用。而 evictAfter() 在窗口函数之后使用。在使用窗口函数之前被

逐出的元素将不被处理。

Flink带有三种内置驱逐器:

CountEvictor：数量剔除器。在 Window 中保留指定数量的元素，并从窗口头部开始丢弃其

余元素。

DeltaEvictor：阈值剔除器。计算 Window 中最后一个元素与其余每个元素之间的增量，丢

弃增量大于或等于阈值的元素。

TimeEvictor：时间剔除器。保留 Window 中最近一段时间内的元素，并丢弃其余元素。

默认情况下，所有内置的驱逐器在窗口函数之前使用。指定驱逐器可以避免预聚合(pre-

aggregation)，因为窗口内所有元素必须在窗口计算之前传递给驱逐器。

Flink 不保证窗口内元素的顺序。这意味着虽然驱逐器可以从窗口开头移除元素，但这些元素不一

定是先到的还是后到的。

代码实现

import org.apache.flink.api.common.typeinfo.Types;

import org.apache.flink.api.java.tuple.Tuple2;

import org.apache.flink.streaming.api.datastream.DataStreamSource;

import

org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;

import

org.apache.flink.streaming.api.windowing.assigners.Globalwindows;

import org.apache.flink.streaming.api.windowing.evictors.CountEvictor;

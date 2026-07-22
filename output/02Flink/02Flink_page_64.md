## 第64页

当一个模式上通过 within 加上窗口长度后，部分匹配的事件序列就可能因为超过窗口长度而被丢弃。可以使用 TimedOutPartialMatchHandler 接口 来处理超时的部分匹配。这个接口可以和其它的混合使用。也就是说你可以在自己的 PatternProcessFunction 里另外实现这个接口。 TimedoutPartialMatchHandler 提供了另外的 processTimedOutMatch 方法，这个方法对每个超时的部分匹配都会调用。

@Override

public void processMatch(Map<String, List<IN>> match, Context ctx,

Collector<OUT> out) throws Exception;

...

@Override

public void processTimedOutMatch(Map<String, List<IN>> match,

Context ctx) throws Exception;

IN startEvent = match.get("start").get(0);

ctx.output(outputTag, T(startEvent));

## 5.4. 时间处理

在 CEP 中，事件的处理顺序很重要。在使用事件时间时，为了保证事件按照正确的顺序被处理，一个事件到来后会先被放到一个缓冲区中，在缓冲区里事件都按照时间戳从小到大排序，当水位线到达后，缓冲区中所有小于于水位线的事件被处理。这意味着着水位线之间的数据都按照时间戳被顺序处理。

为了保证跨水位线的事件按照事件时间处理，Flink CEP库假定水位线一定是正确的，并且把时间戳小于最新水位线的事件看作是晚到的。 晚到的事件不会被处理。

PatternStream<Event> patternStream = CEP.pattern(input, pattern);

OutputTag<String> lateDataOutputTag = new OutputTag<String>("late-

SingleOutputStreamOperator<ComplexEvent> result = patternStream

.sideOutputLateData(lateDataOutputTag)

.select(

);

DataStream<String> lateData = result.getSideOutput(lateDataOutputTag);

## 6. Flink Metrics

metric 英 [ˈmetrɪk] 美 [ˈmetrɪk]

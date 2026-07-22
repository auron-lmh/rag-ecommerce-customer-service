## 第63页

## 5.3. 检测模式

- 在指定了要寻找的模式后，该把它们应用到输入流上来发现可能的匹配了。为了在事件流上运行你的模式，需要创建一个PatternStream。给定一个输入流input，一个模式pattern和一个可选的用来对使用事件时间时有同样时间戳或者同时到达的事件进行排序的比较器comparator。

$$
DataStream<Event> input = ...
$$

$$
Pattern<Event, ?> pattern = ...
$$

$$
EventComparator<Event> comparator = ... // 可选的
$$

$$
PatternStream<Event> patternStream = CEP.pattern(input, pattern, comparator);
$$

- 在获得到一个PatternStream之后，你可以应用各种转换来发现事件序列。推荐使用PatternProcessFunction。

- 匹配数据操作

- PatternProcessFunction有一个processMatch的方法在每找到一个匹配的事件序列时都会被调用。它按照Map<String, List<IN>>的格式接收一个匹配，映射的键是你的模式序列中的每个模式的名称，值是被接受的事件列表（IN是输入事件的类型）。模式的输入事件按照时间戳进行排序。为每个模式返回一个接受的事件列表的原因是当使用循环模式（比如oneToMany()和times()）时，对一个模式会有不止一个事件被接受。

$$
class MyPatternProcessFunction<IN, OUT> extends PatternProcessFunction<IN, OUT>
$$

$$
PatternProcessFunction<IN, OUT>
$$

$$
@Override
$$

$$
public void processMatch(Map<String, List<IN>> match, Context ctx,
$$

$$
Collector<OUT> out) throws Exception;
$$

$$
IN startEvent = match.get("start").get(0);
$$

方法

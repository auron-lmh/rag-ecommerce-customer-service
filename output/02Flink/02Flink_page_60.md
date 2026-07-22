## 第60页

一个模式序列只能有一个时间限制。如果限制了多个时间在不同的单个模式上，会使用最小的那个时间限制。

$$
next.within(Time.seconds(10));
$$

模式序列不能以 notFollowedBy() 结尾。

一个 NOT 模式前面不能是可选的模式。

- 循环模式中的连续性

数据: "a", "b1", "d1", "b2", "d2", "b3", "c"

模式: "a b+ c"

- consecutive

循环模式（例如 oneOrMore() 和 times()），默认是松散连续。

如果想使用严格连续，需要使用 consecutive() 方法明确指定，如果想使用不确定松散连续，可以使用 allowCombinations() 方法。

## 5.2.3. 模式组

可以定义一个模式序列作为 begin， followedBy， followedByAny 和 next 的条件。

这个模式序列在逻辑上会被当作匹配的条件，并且返回一个 GroupPattern，可以在 GroupPattern 上使用 oneOrMore()，times(#ofTimes)，times(#fromTimes，#toTimes)，optional()，consecutive()，allowCombinations()。

Pattern.

$$
<Event>begin("start").where(...).followedBy("start_middle").where(...)
$$

) ;

// 严格连续

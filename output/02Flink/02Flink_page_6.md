## 第6页

## 1.3.2. 键分区状态(Keyed State)

- 状态是根据输入流中定义的键（key）来维护和访问的，所以只能定义在按键分区流（KeyedStream）中，也就keyBy之后才可以使用

- 聚合算子必须在keyBy之后才能使用，就是因为聚合的结果是以Keyed State的形式保存的。

- • ValueState<t>: 保存一个可以更新和检索的值（如上所述，每个值都对应到当前的输入数据的 key，因此算子接收到的每个 key 都可能对应一个值）。这个值可以通过 update(T) 进行更新，通过 T value() 进行检索。

- • ListState<t>: 保存一个元素的列表。可以往这个列表中追加数据，并在当前的列表上进行检索。可以通过 add(T) 或者 addAll(List<T>) 进行添加元素，通过 Iterable<T> get() 获整个列表。还可以通过 update(List<T>) 覆盖当前的列表。

- • ReducingState<t>: 保存一个单值，表示添加到状态的所有值的聚合。接口与 ListState 类似，但使用 add(T) 增加元素，会使用提供的 ReduceFunction 进行聚合。

- • AggregatingState<IN, OUT>: 保留一个单值，表示添加到状态的所有值的聚合。和 ReducingState 相反的是，聚合类型可能与 添加到状态的元素的类型不同。接口与 ListState 类似，但使用 add(IN) 添加的元素会用指定的 AggregateFunction 进行聚合。

- • MapState<UK, UV>: 维护了一个映射列表。你可以添加键值对到状态中，也可以获得反映当前所有映射的迭代器。使用 put(UK, UV) 或者 putAll(Map<UK, UV>) 添加映射。使用 get(UK) 检索特定 key。使用 entries(), keys() 和 values() 分别检索映射、键和值的可迭代视图。你还可以通过 isEmpty() 来判断是否包含任何键值对。

import org.apache.flink.api.common.functions.RichReduceFunction;

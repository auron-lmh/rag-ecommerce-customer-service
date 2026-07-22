## 第31页

用户通过算子能将一个或多个DataStream 转换成新的DataStream，在应用程序中可以将多个数据

这部分内容将描述 Flink DataStream API 中基本的数据转换 API，数据转换后各种数据分区方

式，以及算子的链接策略。

5.1. map

f

输入一个元素同时输出一个元素。下面是将输入流中元素数值加倍的 map function:

DataStreamSource<Integer> mapSource = environment.fromElements(1, 2, 3, 4,

5, 6, 7, 8, 9);

mapSource.map(new MapFunction<Integer, String>() {

@Override

public String map(Integer integer) throws Exception {

return "yjxt_" + integer;

}

}).print();

5.2. filter

f

为每个元素执行一个布尔 function，并保留那些 function 输出值为 true 的元素。

DataStreamSource<Integer> filterSource = environment.fromElements(1, 2, 3,

4, 5, 6, 7, 8, 9);

filterSource.filter(new FilterFunction<Integer>() {

@Override

public boolean filter(Integer integer) throws Exception {

return integer % 2 == 0;

}).print();

5.3. flatMap

f

输入一个元素同时产生零个、一个或多个元素。

## 第34页

import java.util.List;

/**

@Description :

@School:优极限学堂

@Official-website: http://www.yjxxt.com

@Teacher:李毅大帝

@Mail:863159469@qq.com

*

//获取环境

StreamExecutionEnvironment environment =

StreamExecutionEnvironment.getExecutionEnvironment();

//获取数据源

List<String> list = new ArrayList<>();

DataStreamSource<String> lineStream =

environment.fromCollection(list);

//常见操作

.filter(word -> word.length() > 0)

.map(word -> Tuple2.of(word, 1), Types.TUPLE(Types.STRING,

Types.INT))

.keyBy(tuple -> tuple.f0)

t1.f1 = t1.f1 + t2.f1;

return t1;

.print();

//执行环境

environment.execute();

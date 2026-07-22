## 第5页

//运行环境

StreamExecutionEnvironment environment =

StreamExecutionEnvironment.getExecutionEnvironment();

environment.setParallelism(2);

environment.enableCheckpointing(5000);

environment.getCheckpointConfig().setCheckpointStorage("file://" + System.getProperty("user.dir") + File.separator + "ckpt");

//获取数据源

DataStream<String> source =

environment.socketTextStream("localhost", 19523);

//转换并输出

// source.map(word -> word.toUpperCase()).print();

//转换需要添加当前SubTask处理这个单词的序号并输出

source.map(new YjxxtOperatorStateFunction()).print();

//运行环境

environment.execute();

;

//声明一个变量记数

private int count;

//创建一个状态对象

private ListState<Integer> countListState;

@Override

//更新计数器

count++;

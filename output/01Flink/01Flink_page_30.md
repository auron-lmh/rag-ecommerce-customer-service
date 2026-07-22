## 第30页

* 还有open、close方法可以被重写，最主要的是可以获取运行时的状态RuntimeContext

*

class YjxxtCustomSourceRich extends RichParallel1SourceFunction<String>

@Override

System.out.println("YjxxtCustomSourceExt.open" +

System.currentTimeMillis());

super.open(parameters);

@Override

System.out.println("YjxxtCustomSourceExt.close" +

System.currentTimeMillis());

super.close();

/**

@param context

@throws Exception

*

@Override

//开始读取文件

List<String> lines = FileUtils.readLines(new

File("data/secret.txt"), "utf-8");

//Task总数

int taskCount =

this.getRuntimeContext().getNumberOfParallelSubtasks();

//当前TaskID

int taskId = this.getRuntimeContext().getIndexOfThisSubtask();

//开始进行遍历并解密

//如果line解密后取余taskCount的结果等于taskId，就由当前线程去接受

String decrypt = DESUtil.decrypt("yjxxt0523", line);

//开始解密

@Override

System.out.println("YjxxtCustomSource.cancel_" +

System.currentTimeMillis());

## 5. Flink Transformation

类算子

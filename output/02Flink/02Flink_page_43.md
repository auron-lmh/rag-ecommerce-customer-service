## 第43页

//methods that should be implemented in child class to support two phase commit

org.apache.flink.streaming.api.functions.sink.TwoPhaseCommitSinkFunctio

n

//Write value within a transaction.

protected abstract void invoke(TXN transaction, IN value, Context

context) throws Exception;

//Method that starts a new transaction.

//Returns:newly created transaction.

//在开启事务之前，我们在目标文件系统的临时目录中创建一个临时文件，后面在处理数据时将数

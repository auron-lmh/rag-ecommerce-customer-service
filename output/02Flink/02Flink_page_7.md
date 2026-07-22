## 第7页

* @Teacher:李毅大帝

* @Mail:863159469@qq.com

* /

//运行环境

StreamExecutionEnvironment environment =

StreamExecutionEnvironment.getExecutionEnvironment();

environment.setParallelism(1);

environment.enableCheckpointing(5000);

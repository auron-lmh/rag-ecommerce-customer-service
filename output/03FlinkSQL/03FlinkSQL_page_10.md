## 第10页

## 2.5. 输出表

## 2.5.1. toDataStream

import static org.apache.flink.table.api.Expressions.*;

/**

* @Description :

* @School:优极限学堂

* @Official-website: http://www.yjxxt.com

* @Teacher:李毅大帝

* @Mail:863159469@qq.com

* /

//运行环境

StreamExecutionEnvironment environment =

StreamExecutionEnvironment.getExecutionEnvironment();

StreamTableEnvironment tableEnvironment =

StreamTableEnvironment.create(environment);

//Pojo类型

DataStreamSource<String> empSource =

environment.readTextFile("data/emp.txt");

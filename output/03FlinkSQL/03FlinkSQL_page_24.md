## 第24页

## 4. FlinkSQL Schema

## 4.1. physical column

- 物理字段：源自于“外部存储”系统本身 schema 中的字段

- ○ kafka 消息的 key、value（json 格式）中的字段；

- ○ mysql 表中的字段；

- ○ hive 表中的字段；

- ○ parquet 文件中的字段......

## 4.2. computed column

- 表达式字段（逻辑字段）：在物理字段上施加一个 sql 表达式，并将表达式结果定义为一个字段

- Java代码

Schema.newBuilder() .columnByExpression("age_exp", "age+10") // 声明表达式字段 age_exp，它来源于物理字段 age+10

- SQL代码

CREATE TABLE MyTable ( `user_id` BIGINT,

`price` DOUBLE,

`quantity` DOUBLE,

`cost` AS price * quantity, -- cost 来源于: price*quantity

) WITH (

'connector' = 'kafka'

...;

## 4.3. metadata column

键

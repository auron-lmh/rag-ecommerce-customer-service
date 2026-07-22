## 第25页

- SQL代码

CREATE TABLE MyTable (

'user_id` BIGINT,

'name` STRING,

record_time` TIMESTAMP_LTZ(3) METADATA FROM 'timestamp' -- 元数据字段,

来源于 kafka record 的 timestamp

)WITH (

'connector' = 'kafka'

...

)

## 4.4. 主键约束

- 单字段主键约束语法:

id INT PRIMARY KEY NOT ENFORCED,

## 4.5. 代码示例

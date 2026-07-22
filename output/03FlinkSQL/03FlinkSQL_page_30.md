## 第30页

user_id BIGINT,

item_id BIGINT,

category_id BIGINT,

behavior STRING,

ts TIMESTAMP(3)

)

WITH (

'connector' = 'kafka',

'topic' = 'user_behavior',

'properties.bootstrap.servers' = 'localhost:9092',

'properties.group.id' = 'testGroup',

'format' = 'json',

'json.ignore-parse-errors' = 'true'

)

## • 参数配置

## 第28页

## 5.1. CSV Format

https://nightlies.apache.org/flink/flink-docs-release-1.15/zh/docs/connectors/table/formats/csv/

maven依赖

$$
<dependency>
$$

$$
<groupId>org.apache.flink</groupId>
$$

$$
<artifactId>flink-csv</artifactId>
$$

$$
<version>1.15.2</version>
$$

$$
</dependency>
$$

代码实现

$$
CREATE TABLE user_behavior (
$$

$$
user_id BIGINT,
$$

$$
item_id BIGINT,
$$

$$
category_id BIGINT,
$$

$$
behavior STRING,
$$

$$
ts TIMESTAMP(3)
$$

$$
) WITH (
$$

$$
'connector' = 'kafka',
$$

$$
'topic' = 'user_behavior',
$$

$$
'properties.bootstrap.servers' = 'localhost:9092',
$$

$$
'properties.group.id' = 'testGroup',
$$

$$
'format' = 'csv',
$$

$$
'csv.ignore-parse-errors' = 'true',
$$

$$
'csv.allow-comments' = 'true'
$$

$$
)
$$

参数配置

| 参数 | 是否必选 | 默认值 | 类型 | 描述 |
|---|---|---|---|---|
| format | 必选 | (none) | String | 指定要使用的格式，这里应该是 "csv"。 |
| csv.field.delimiter | 可选 | , | String | 字段分隔符 (默认 ",")，必须为单字符。你可以使用反斜杠字符指定一些特殊字符，例如 \t 代表制表符。你也可以通过 unicode 编码在纯 SQL 文本中指定一些特殊字符，例如 "csv.field.delimiter" = U&\'0001" 代表 ox01 字符。 |
| csv.disable.quote.character | 可选 | false | Boolean | 是否禁止对引用的值使用引号 (默认是 false)。如果禁止，选项 "csv.quote-character" 不能设置。 |
| csv.quote.character | 可选 | " | String | 用于围住字段值的引导字符 (默认 "). |
| csv.allow.comments | 可选 | false | Boolean | 是否允许忽略注释行（默认不允许），注释行以 # 作为起始字符。如果允许注释行，请确保 csv.ignore-parse-errors 也开启了从而允许空行。 |
| csv.ignore.parse.errors | 可选 | false | Boolean | 当解析异常时，是跳过当前字段或行，还是抛出错误失败（默认 false，即抛出错误失败）。如果忽略字段的解析异常，则会将该字段值设置为 null11。 |
| csv.array.element.delimiter | 可选 | ; | String | 分隔数组和行元素的字符串 (默认 ;). |
| csv.escape.character | 可选 | (none) | String | 转义字符 (默认关闭)。 |
| csv.null.literal | 可选 | (none) | String | 是否将 "null" 字符串转化为 null 值。 |

数据类型映射

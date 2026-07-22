## 第29页

- 目前 CSV 的 schema 都是从 table schema 推断而来的。显式地定义 CSV schema 暂不支持。

- Flink 的 CSV Format 数据使用 jackson databind API 去解析 CSV 字符串。

Flink SQL 类型

CSV 类型

CHAR / VARCHAR / STRING

string

BOOLEAN

boolean

BINARY / VARBINARY

string with encoding: base64

DECIMAL

number

TINYINT

number

SMALLINT

number

INT

number

BIGINT

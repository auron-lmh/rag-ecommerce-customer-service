## 第31页

## 6. FlinkSQL WaterMark

## 6.1. 时间语义

## 6.1.1. 动态表

- 动态表 是 Flink 的支持流数据的 Table API 和 SQL 的核心概念。与表示批处理数据的静态表不同，动态表是随时间变化的。可以像查询静态批处理表一样查询它们。查询动态表将生成一个连续查询（Continuous Query）。一个连续查询永远不会终止，结果会生成一个动态表。查询不断更新其(动态)结果表，以反映其(动态)输入表上的更改。本质上，动态表上的连续查询非常类似于定义物化视图的查询。

- 需要注意的是，连续查询的结果在语义上总是等价于以批处理模式在输入表快照上执行的相同查询的结果。

![图片](data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAsICAoIBwsKCQoNDAsNERwSEQ8PESIZGhQcKSQrKigkJyctMkA3LTA9MCcnOEw5PUNFSElIKzZPVU5GVEBHSEX/2wBDAQwNDREPESESEiFFLicuRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUX/wAARCAAeASwDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD1yiiigAooooAKKKKACiiigAooooAR/umlpH+6aWgDOvNRhs54o5twM27awHAwM81Eur25WzJEg+1/cyv3f9709KkvNPhvZENwu5Uz8vqcg5/SqU3h+CcLvnnDoqrGyOVC4ORwDg8+tQak8GsRz3otvImj3F1SRwNrlfvYwc/mKvu6ojOxwqjJNUrHSrawklljRTPKzM8u3DHJzip7mFpwkeR5ZbMnqQO1AD4ZTLAsjIU3DO09QKz01+0kj3qJceU0pBXlQpwQfetMjKkeoxWauh2qIyrkeZGUkI6tkYz7dKALJ1CEXEcGG3yEAcccru/kKiudUa1vYrcWNzKZPuPHs2nHJ6sDxVc6PcbY3F//AKTG+4SmAEYC7QNufTvV9bQyT2sskm6SDOSFwGJGDx2pgImsKZ7uOS1uIltV3PI4XaRjIxgk/pUY1zdDFIun3TGZsRopjJcYzkHdjH406LTbqO8vZzfAi5UBV8gfJjgc55qhN4V8+AB7mIy+b5pzbjyydu37mePrmqMjQn1d4LqG3OnXbNMMqV8vA9c/N2rRLADmqRtv3lpI0mXt1ZflXAbIx07dKmGWPvTSFck3sxwoqQDA9aRV2jFLQAUUUUhhUNwPlB96mqOcZjoAq09JSgwPWmUUAWJIzIQV6GnLAq9eTTbd+Np/CpqAILhcAEfSoKuSLujIqnQBLAf3mPY02RNrkAcU1G2zIau0AFFFFABRRRQAUUUUAFFFFABRRRQAj/dNG9fWh/umloAgkKg5z1pm9fWrLDcMVCw2nFSzSLuM3r60b19aWigoTevrRvX1paKAG719amiIHJNEaZ5PSpaaIk+gm9fWopJh0BqSRtq8d6gq0jJsTevrUsRUDOaYOTVgDAxQwQm9fWjevrS0VJQm9fWjevrS0UAJvX1pkjKY257VJSN90/SgChvX1o3r607vRQAJKEYHNXBIpAIPWqdWLdiQVPagCXevrVJyquRmr1VpxiT60AVy43DmrySKyA5qmfvj8atQt+7GaAP/2Q==)

- 与 spark、hive 等组件中的“表”的最大不同之处：flinksql 中的表是动态表！

| Flink SQL 类型 | JSON 类型 |
|---|---|
| CHAR / VARCHAR / STRING | string |
| BOOLEAN | boolean |
| BINARY / VARBINARY | string with encoding: base64 |
| DECIMAL | number |
| TINYINT | number |
| SMALLINT | number |
| INT | number |
| BIGINT | number |
| FLOAT | number |
| DOUBLE | number |
| DATE | string with format: date |
| TIME | string with format: time |
| TIMESTAMP | string with format: date-time |
| TIMESTAMP_WITH_LOCAL_TIME_ZONE | string with format: date-time (with UTC time zone) |
| INTERVAL | number |
| ARRAY | array |
| MAP / MULTiset | object |
| ROW | object |

Flink SQL 类型与 JSON 类型对照表

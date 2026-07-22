## 第23页

- Debezium-JSON: debezium-json.

- Canal-JSON: canal-json.

- Raw: raw.

## • 配置参数

| Options | Description |
|---|---|
| path | 文件路径 |
| source.monitor-interval | 源检查新文件的时间间隔。 |
| sink.rolling-policy.file-size | 滚动前的最大文件大小。 |
| sink.rolling-policy.roll-over-interval | 文件在滚动前可以保持打开的最长时间（默认为30分钟，以避免出现许多小文件） |
| sink.rolling-policy.check-interval | 检查基于时间的滚动策略的间隔。 |
| auto-compaction=false | 是否在流接收器中启用自动压缩。 |
| compaction.file-size | 压缩目标文件大小，默认值为滚动文件大小。和rolling file size一致 |
| sink.partition-commit.trigger | process-time、partition-time 提交分区的时间 |
| sink.partition-commit.delay | 延迟提交分区的时间。如果是日分区，应是'1d'，小时分区，应是'1h'，默认为'0s' |
| sink.partition-commit.policy.kind = success-file,metastore | 提交分区的策略是通知下游应用该分区已完成写入，该分区已准备好被读取。 |
| sink.parallelism | 将文件写入外部文件系统的并行性。该值应大于零，否则将引发异常 |

## • Source

- 文件系统连接器可用于将单个文件或整个目录的数据读取到单个表中。当使用目录作为source 路径时，对目录中的文件进行 无序的读取。

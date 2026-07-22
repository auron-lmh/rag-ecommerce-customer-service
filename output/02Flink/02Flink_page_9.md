## 第9页

## 1.4.1. 存储方式

- flink-1.13 版及以前

| 分类 | MemoryStateBackend | FsStateBackend | RocksDBStateBackend |
|---|---|---|---|
| 存储方式 | state:TaskManager内存Checkpoint:JobManager内存 | state:TaskManager内存Checkpoint:外部文件系统(HDFS) | state:TaskManager上的RocksDB(内存+磁盘)Checkpoint:外部文件系统(HDFS) |
| 使用场景 | 本地测试 | 分钟级窗口聚合、join，生产环境使用 | 超大状态作业，天级窗口聚合，生产环境使用 |

- MemoryStateBackend

- ■ 基于内存存储

- ○ FsStateBackend

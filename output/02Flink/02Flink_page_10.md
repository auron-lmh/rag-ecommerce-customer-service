## 第10页

■ Rockdb 的磁盘文件数据读写速度相对还是比较快的，所以在支持超大规模状态数据时，数据的读写效率不会有太大的降低

○ 代码实现

// 设置内存状态后端

StreamExecutionEnvironment env =

StreamExecutionEnvironment.getExecutionEnvironment();

env.setStateBackend(new HashMapStateBackend());

// 设置RocksDb状态后端

StreamExecutionEnvironment env =

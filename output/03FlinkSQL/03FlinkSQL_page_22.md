## 第22页

- 在 Flink 中包含了该文件系统连接器，不需要添加额外的依赖。

<dependency>

<groupId>org.apache.flink</groupId>

<artifactId>flink-connector-files</artifactId>

</dependency>

- 从文件系统中读取或者向文件系统中写入行时，需要指定相应的 format。

- 代码示例

CREATE TABLE

MyUserTable

(

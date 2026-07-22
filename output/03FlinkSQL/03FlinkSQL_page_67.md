## 第67页

- HiveCatalog

作为原生 Flink 元数据的持久化存储，以及作为读写现有 Hive 元数据的接口

- 用户自定义 Catalog

用户可以通过实现 Catalog 接口来开发自定义 Catalog，除了需要实现自定义的

Catalog 之外，还需要为这个 Catalog 实现对应的 CatalogFactory 接口

## 13.2. 版本支持

使用Hive构建数据仓库已经成为了比较普遍的一种解决方案，不同版本的Flink对于Hive的集成有所差异

Flink 与 Hive 的集成主要体现在以下两个方面:

- 持久化元数据:

Flink利用 Hive 的 MetaStore 作为持久化的 Catalog，我们可通过 Hivecatalog 将不同

会话中的 Flink 元数据存储到 Hive Metastore 中。例如，我们可以使用 Hivecatalog

将其 Kafka的数据源表存储在 Hive Metastore 中这样该表的元数据信息会被持久化到

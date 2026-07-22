## 第61页

通常，稀疏向量所代表的原始文本也会存储在 Collections 中。您可以使用 VARCHAR 字段来存储

原始文本。

代码块

1 schema.add_field(field_name="sparse_vector",

datatype=DataType.SPARSE_FLOAT_VECTOR)

2 schema.add_field(field_name="text", datatype=DataType.VARCHAR,

max_length=65535,

在此示例中，添加了两个字段：

sparse_vector :该字段使用 SPARSE_FLOAT_VECTOR 数据类型存储稀疏向量。

text :该字段使用 VARCHAR 数据类型存储文本字符串，最大长度为 65535 字节。

设置索引参数

为稀疏向量创建索引的过程与为稠密向量创建索引的过程类似，但在指定的索引类型

( index_type )、距离度量( metric_type )和索引参数( params )上有所不同。

代码块

1 index_params = client.prepare_index_params()

2

3 index_params.add_index(

field_name="sparse_vector",

index_name="sparse_inverted_index",

index_type="SPARSE_INVERTED_INDEX",

metric_type="BM25",

params={"inverted_index_algo": "DAAT_MAXSCORE"}, # or "DAAT_WAND" or

"TAAT_NAIVE"

9)

10

11

index_type :要建立的索引类型。在本例中，将值设为 SPARSE_INVERTED_INDEX 。

metric_type :用于计算稀疏向量间相似性的度量。有效值:

IP (内积)：使用点积衡量相似性。

BM25 :通常用于全文搜索，侧重于文本相似性。

params.inverted_index_algo :用于建立和查询索引的算法。有效值:

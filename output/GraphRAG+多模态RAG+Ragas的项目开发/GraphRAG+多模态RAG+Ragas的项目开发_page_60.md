## 第58页

这种类型的向量字段保存 16 位浮点数列表，精度有所降低，但指数范围与 Float32 相同。这种类

型的数据常用于深度学习场景，因为它能在不明显影响精度的情况下减少内存使用量。

INT8_VECTOR

这种类型的向量字段存储由 8 位有符号整数（int8）组成的向量，每个分量的范围为-128 到

127。它专为量化深度学习架构（如 ResNet 和 EfficientNet）量身定制，可大幅缩小模型大小，提高

推理速度，同时只造成极小的精度损失。注：该向量类型仅支持 HNSW 索引。

BINARY_VECTOR

这种类型的向量场保存着一个 0 和 1 的列表。在图像处理和信息检索场景中，它们是表示数据的

紧凑特征。

为向量字段设置索引参数

为了加速语义搜索，必须为向量字段创建索引。索引可以大大提高大规模向量数据的检索效率。

代码块

1 index_params = client.prepare_index_params()

2

3

index_params.add_index()

4

5

6

7

8

)

9

10 client.create_collection()

schema=schema,

index_params=index_params

14

)

15

在上面的示例中，使用 AUTOINDEX 索引类型为 dense_vector 字段创建了名为

dense_vector_index 的索引。metric_type 设置为 IP ，表示将使用内积作为距离度量。

Milvus 提供多种索引类型，以获得更好的向量搜索体验。AUTOINDEX是Milvus 根据数据特征自动选择

最优索引类型，旨在平滑向量搜索的学习曲线。

目前，Milvus 支持这些类型的相似性度量：欧氏距离 (L2)、内积 (IP)、余弦相似度 (COSINE)、

JACCARD (杰卡德距离), HAMMING (汉明距离) 和 BM25 (专门为稀疏向量的全文检索而设

计）

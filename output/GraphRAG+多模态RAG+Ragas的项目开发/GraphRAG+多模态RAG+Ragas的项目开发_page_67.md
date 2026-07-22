## 第65页

# Name of the SPARSE_FLOAT_VECTOR field reserved to store generated

embeddings

function_type=FunctionType.BM25, # Set to `BM25`

schema.add_function(bm25_function)

参数

说明

name

函数名称。该函数将text 字段中的原始文本转换为可搜索向量，这些

sparse 字段中。

需要将文本转换为稀疏向量的VARCHAR 字段的名称。对于FunctionT

该参数只接受一个字段名称。

存储内部生成的稀疏向量的字段名称。对于FunctionType.BM25，该

一个字段名称。

function_type

要使用的函数类型。将值设为FunctionType.BM25。

e、标量字段

在常见情况下，您可以使用标量字段来存储存储在 Milvus 中的向量嵌入的元数据，并通过元数据过滤

进行 ANN 搜索，以提高搜索结果的正确性。支持多种标量字段类型，包括VarChar、Boolean、Int、

Float、Double、Array 和JSON。

代码块

1 schema.add_field(

datatype=DataType.ARRAY,

element_type=DataType.VARCHAR,

max_capacity=5,

max_length=512,

7 )

8

9 schema.add_field(

datatype=DataType.JSON,

12 )

13

14 schema.add_field(

datatype=DataType.BOOL,

17 )

18

19 schema.add_field(

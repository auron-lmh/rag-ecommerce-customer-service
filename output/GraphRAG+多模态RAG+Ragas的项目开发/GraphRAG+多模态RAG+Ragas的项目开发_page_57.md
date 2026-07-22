## 第55页

## Supreme Court allows White House to press
social media companies to remove
disinformation

## Fields:

Article (ID)

Title (Text)

Author Info (Struct)

Publish Timestamp (Integer)

Image URL (Text)

Image Embedding (Dense Vector)

Data Types:

INT64

VARCHAR

JSON

INT32

VARCHAR

FLOAT_VECTOR

Summary (Text)

Summary Embedding (Dense Vector)

FLOAT_VECTOR

SPARSE_FLOAT_VECTOR

Summary Sparse Embedding (Sparse Vector)

搜索系统的数据模型设计包括分析业务需求，并将信息抽象为模式表达的数据模型。例如，搜索一段

文本必须通过 "嵌入" 将字面字符串转换为向量并启用向量搜索，从而实现 "索引"。除了这一基本要求

外，可能还需要存储出版时间戳和作者等其他属性。有了这些元数据，就可以通过过滤来完善语义搜

索，只返回特定日期之后或特定作者发表的文本。

代码块

from pymilvus import MilvusClient, DataType

schema = MilvusClient.create_schema()

a、主键和 Autold

与关系数据库中的主字段类似，Collection 也有一个主字段，用于将实体与其他实体区分开来。主字

段中的每个值都是全局唯一的，并与一个特定的实体相对应。

主字段只接受整数或字符串。插入实体时，默认情况下应包含主字段值。但是，如果在创建

Collections 时启用了Autold，Milvus 将在插入数据时生成这些值。在这种情况下，请从要插入的实体

中排除主字段值。

代码块

schema.add_field()

datatype=DataType.INT64,

is_primary=True,

auto_id=False,

6

7 )

8

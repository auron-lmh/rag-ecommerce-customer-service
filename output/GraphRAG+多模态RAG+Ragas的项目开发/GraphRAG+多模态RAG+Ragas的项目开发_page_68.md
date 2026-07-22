## 第66页

datatype=DataType.INT64, # Milvus 支持的数字类型有

Int8,Int16,Int32,Int64,Float 和Double。

22 )

23

schema.add_field(

datatype=DataType.VARCHAR,

# highlight-next-line

max_length=512

29 )

30

f、可归零和默认值

Milvus 允许你为标量字段（主字段除外）设置 nullable 属性和默认值。对于标记为

nullable=True 的字段，您可以在插入数据时跳过该字段，或直接将其设置为空值，系统会将其

视为空值而不会导致错误。当字段具有默认值时，如果在插入过程中没有为该字段指定数据，系统将

自动应用该值。

限制规则

只有标量字段（主字段除外）支持默认值和 nullable 属性。

JSON 和数组字段不支持默认值。

默认值或 nullable 属性只能在创建 Collections 时配置，之后不能修改。

标记为 nullable 的字段不能用作分区键。

在启用 nullable 属性的标量字段上创建索引时，索引将排除空值。

JSON 和 ARRAY 字段：当使用 IS NULL 或 IS NOT NULL 操作符对 JSON 或 ARRAY 字段进行

过滤时，这些操作符在列级别工作，这表明它们只评估整个 JSON 对象或数组是否为空。例如，如

果 JSON 对象中的某个键为空，IS NULL 过滤器将无法识别该键。

代码块

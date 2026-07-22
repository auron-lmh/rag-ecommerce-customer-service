## 第15页

private String uname;

private String passwd;

//此处需要生成 [无参构造器][getter和setter][equals和hashCode][toString]

## 2.7.3. 返回类型

由于JVM运行时候会擦除类型（泛型类型），Flink无法准确的获取到数据类型。因此，在使用Java
API的时候，我们需要手工指定类型。

使用Scala的时候无需指定。

需要使用 SingleOutputStreamOperator 的 returns 方法来指定算子的返回数据类型。

returns(Class<T> typeClass): 使用Class的方式指定返回数据类型。

returns (TypeHint<T> typeHint): 使用TypeHint方式指定返回数据类型，通常泛型类型需
要使用TypeHint来指定。

returns (TypeInfo<T> typeInfo): 使用TypeInfo指定。

TypeInfo

TypeHint

TypeInformation 是Flink类型系统的核心，是生成序列化/反序列化工具和 Comparator 的
工具类。同时它还是连接schema和编程语言内部类型系统的桥梁。

可以使用 of 方法创建 TypeInfo

of(Class typeClass): 从 Class 创建。

of(TypeHint typeHint): 从 TypeHint 创建。

TypeHint

由于泛型类型在运行时会被JVM擦除，所以说我们无法使用
TypeInfo

of(XXX.class)方式指定带有泛型的类型。

为了可以支持泛型类型，Flink引入了 TypeHint。例如我们需要获取 Tuple2<String,
Long> 的类型信息，可以使用如下方式:

在Flink中经常使用的类型已经预定义在了 Types 中。它们的serializer/deserializer和
Comparator 已经定义好了。

Tuple 类型既可以使用 TypeHint 指定又可以使用 Types 指定。例如 Tuple2<String,
Integer> 类型我们可以使用如下

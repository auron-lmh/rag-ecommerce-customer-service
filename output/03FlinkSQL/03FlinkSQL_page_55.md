## 第55页

## 11.3.2. UDF表值函数

- 使用表函数，可以对一行数据拆分得到一个表，和 Hive 中的 UDTF 非常相似。

- 要实现自定义的表函数，需要自定义类来继承抽象类 TableFunction，内部必须要实现的也是一个名为 eval 的求值方法。

- 与标量函数不同的是，TableFunction 类本身是一个泛型参数 T，这就是表函数返回数据的类型；

- 而 eval() 方法没有返回类型，内部也没有 return 语句，是通过调用 collect() 方法来发送想要输出的行数据的

- 代码实现:

import org.apache.flink.table.annotation.DataTypeHint;

import org.apache.flink.table.annotation.FunctionHint;

import org.apache.flink.table.api.*;

import org.apache.flink.table.functions.TableFunction;

import org.apache.flink.types.Row;

import static org.apache.flink.table.api.Expressions.*;

@FunctionHint(output = @DataTypeHint("ROW<word STRING, length INT>"))

// use collect(...) to emit a row

collect(Row.of(s, s.length()));

TableEnvironment env = TableEnvironment.create(...);

// 在 Table API 里不注册直接“内联”调用函数

env

.from("MyTable")

env.createTemporarySystemFunction("HashFunction", HashFunction.class);

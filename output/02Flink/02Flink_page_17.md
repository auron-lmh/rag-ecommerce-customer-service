## 第17页

## 2.2. CoGroup

- • CoGroup: 除了输出匹配的元素对以外，未能匹配的元素也会输出。

- • Window CoGroup

DataStream,DataStream →

DataStream

• Cogroup two data streams on a given key and a common window.

$$
dataStream.coGroup(otherStream)
$$

$$
.where(0).equalTo(1)
$$

return Tuple3.of(split[0], split[1], Long.parseLong(split[2]));

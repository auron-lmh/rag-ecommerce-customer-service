## 第58页

.map(tuple2 -> {
tuple2.f0 =
LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy年MM月dd日HH
时mm分ss秒SSS毫秒")) + tuple2.f0;
return tuple2;
}, Types.TUPLE(Types.STRING, Types.INT))
.print("TimeWindow--Sliding:").setParallelism(1);

//运行环境
environment.execute();
}
}

## 10.4.3. Session Window

会话窗口的 assigner 会把数据按活跃的会话分组。

与滚动窗口和滑动窗口不同，会话窗口不会相互重叠，且没有固定的开始或结束时间。

会话窗口的 assigner 可以设置固定的会话间隔（session gap）或用 session gap extractor 函数来动态地定义多长时间算作不活跃。

当超出了不活跃的时间段，当前的会话就会关闭，并且将接下来的数据分发到新的会话窗口。

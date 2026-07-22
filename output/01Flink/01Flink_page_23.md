## 第23页

Processes

TaskManager

Task Slot

Task Slot

Task Slot

Source
[1]

map()

Source
[3]

map()
[3]

Source
[5]

map()
[5]

Task Slot

TaskManager

Task Slot

Task Slot

Source
[4]

map()
[4]

Source
[6]

map()
[6]

keyBy()
window()
apply()
[1]

keyBy()
window()
apply()
[3]

keyBy()
window()
apply()
[5]

keyBy()
window()
apply()
[2]

keyBy()
window()
apply()
[4]

keyBy()
window()
apply()
[6]

Sink
[1]

[3]

[5]

Threads

## 3. Flink 运行环境

## 3.1. 批处理运行环境

ExecutionEnvironment env = ExecutionEnvironment.getExecutionEnvironment();

## 3.2. 流式计算运行环境

StreamExecutionEnvironment env =

StreamExecutionEnvironment.getExecutionEnvironment();

## 3.3. 本地web ui环境

添加pom依赖

<dependency>

<groupId>org.apache.flink</groupId>

<artifactId>flink-runtime-web_2.12</artifactId>

<version>${flink.version}</version>

</dependency>

代码实现

//默认访问的端口为: 8081

StreamExecutionEnvironment environment =

StreamExecutionEnvironment.createLocalEnvironmentWithWebUI(new

Configuration();

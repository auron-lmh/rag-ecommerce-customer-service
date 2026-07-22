## 第25页

import org.apache.flink.streaming.api.datastream.DataStreamSource;
import
org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import java.util.List;

/**
* @Description :
* @School: 优极限学堂
* @Official-website: http://www.yjxxt.com
* @Teacher: 李毅大帝
* @Mail: 863159469@qq.com
*/

* @Description :
* @School: 优极限学堂
* @Official-website: http://www.yjxxt.com
* @Teacher: 李毅大帝
* @Mail: 863159469@qq.com

* /
public class Hello01SourceFormCollection {

public static void main(String[] args) throws Exception {
//获取程序运行的环境

StreamExecutionEnvironment environment =
StreamExecutionEnvironment.getExecutionEnvironment();

//通过集合获取数据源
List<String> list = List.of("11", "22", "33", "44", "55", "66",
"77");

DataStreamSource<String> collectionSource =
environment.fromCollection(list);

collectionSource.map(word -> "collectionSource-" + word).print();

//通过元素获取数据源

DataStreamSource<String> elementSource =

environment.fromElements("aa", "bb", "cc", "dd", "ee", "ff");

elementSource.map(word -> "elementSource-" + word).print();

//自动生成数据源

DataStreamSource<Long> sequenceSource =

environment.generateSequence(1, 5);

sequenceSource.map(word -> "SequenceSource-" + word).print();

environment.execute();

}

## 4.4. 基于Connectors:

一些比较基本的 Source 和 Sink 已经内置在 Flink 里。

o 预定义 data sources 支持从文件、目录、socket，以及 collections 和 iterators 中读取数
据。

o 预定义 data sinks 支持把数据写入文件、标准输出 (stdout)、标准错误输出 (stderr) 和
socket。

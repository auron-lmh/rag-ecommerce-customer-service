## 第46页

按键分区的广播连接流处理函数，同样是基于 BroadcastConnectedStream 调用.process()时作为参数传入。

与 BroadcastProcessFunction 不同的是，这时的广播连接流，是一个 KeyedStream与广播
流 (BroadcastStream) 做连接之后的产物。

## 代码展示

import org.apache.flink.streaming.api.datastream.DataStreamSource;
import
org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.ProcessFunction;
import org.apache.flink.util.Collector;

/**
* @Description :
* @School: 优极限学堂
* @Official-website: http://www.yjxxt.com
* @Teacher: 李毅大帝
* @Mail: 863159469@qq.com
*/
public class Hello13ProcessFunction {

    public static void main(String[] args) throws Exception {
        //获取程序运行的环境
        StreamExecutionEnvironment environment =
        StreamExecutionEnvironment.getExecutionEnvironment();

        //数据源
        DataStreamSource<String> source =
        environment.fromElements("aa", "bb", "cc").setParallelism(1);

        //处理数据
        source.map(word -> "yjxxt_" + word).process(new
        ProcessFunction<String, String>() {
            @Override
            public void processElement(String s,
                ProcessFunction<String, String>.Context context, Collector<String>
                collector) throws Exception {

                //查看Context
                System.out.println("[处理时间]" +
                context.timerService().currentProcessingTime());
                System.out.println("[水位线/水印]" +
                context.timerService().currentWatermark());
                collector.collect(s + "_" + s.hashCode());
            }
        }).print();
        //执行代码
        environment.execute();
    }
}

## 8.3. 侧输出

process function的side outputs功能可以产生多条流，并且这些流的数据类型可以不一样。

一个side output可以定义为OutputTag[X]对象，X是输出流的数据类型。

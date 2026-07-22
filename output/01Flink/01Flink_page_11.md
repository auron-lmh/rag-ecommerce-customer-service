## 第11页

2.5. DataStream版WordCount

2.5.1. 安装netcat.ext

Windows

Here's netcat 1.11 compiled for both 32 and 64-bit Windows (but note that 64-bit version hasn't been tested much - use at your own risk).

I'm providing it here because I never seem to be able to find a working netcat download when I need it.

Small update: netcat 1.12 - adds -c command-line option to send CRLF line endings instead of just CR (eg. to talk to Exchange SMTP)

Warning: a bunch of antiviruses think that netcat (nc.exe) is harmful for some reason, and may block or delete the file when you try to download it. I could get around this by recompiling the binary every now and then (without doing any other changes at all, which should give you an idea about the level of protection these products offer), but I really can't be bothered.

将下载后nc.exe和nc64.exe的软件存放到 C:\Windows\System32 目录下

打开Doc窗口，执行命令 nc -lp 19523(通信端口)

Linux

[root@node01 ~]# yum install nc -y

[root@node01 ~]# nc -l -k -p 19523

2.5.2. Java代码实现

import org.apache.flink.api.common.functions.FlatMapFunction;

import org.apache.flink.api.common.functions.MapFunction;

import org.apache.flink.api.java.functions. KeySelector;

import org.apache.flink.api.java.tuple.Tuple2;

import org.apache.flink.streaming.api.datastream.DataStreamSource;

import org.apache.flink.streaming.api.datastream.KeyedStream;

import org.apache.flink.streaming.api.datastream.SingleOutputStreamOperator;

import

org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;

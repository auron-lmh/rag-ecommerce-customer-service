## 第18页

- 用于DataStream时返回是CoGroupedStreams，用于DataSet时返回是CoGroupOperatorSets

- 代码实现

import com.yjxxt.util.KafkaUtil;

import org.apache.commons.lang3.RandomStringUtils;

import org.apache.flink.api.common.eventtime.WatermarkStrategy;

import org.apache.flink.api.common.functions.CoGroupFunction;

import org.apache.flink.api.java.tuple.Tuple3;

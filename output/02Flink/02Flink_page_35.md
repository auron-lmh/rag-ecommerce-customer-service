## 第35页

$$
//配置文件restart-strategy: failure-rate
$$

$$
ExecutionEnvironment env =
$$

$$
ExecutionEnvironment.getExecutionEnvironment();
$$

$$
env.setRestartStrategy(RestartStrategies.failureRateRestart(
$$

$$
3, // 每个时间间隔的最大故障次数
$$

$$
Time.of(5, TimeUnit.MINUTES), // 测量故障率的时间间隔
$$

$$
Time.of(10, TimeUnit.SECONDS) // 延时
$$

$$
)) ;
$$

| Key | Default | Type | Description |
|---|---|---|---|
| restart-strategy.failure-rate.delay | 1 s | Duration | Delay between two consecutive restart attempts if restart-strategy has been set to failure-rate . It can be specified using notation: "1 min", "20 s" |
| restart-strategy.failure-rate.failure-rate-interval | 1 min | Duration | Time interval for measuring failure rate if restart-strategy has been set to failure-rate . It can be specified using notation: "1 min", "20 s" |
| restart-strategy.failure-rate.max-failures-per-interval | 1 | Integer | Maximum number of restarts in given time interval before failing a job if restart-strategy has been set to failure-rate. |

- 不重启策略

- No Restart Strategy

- 作业直接失败，不尝试重启。

$$
//配置文件restart-strategy: none
$$

$$
ExecutionEnvironment env =
$$

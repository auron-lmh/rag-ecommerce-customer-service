## 第71页

- 在工作流中数据记录是从上游向下游流动的（例如：从 Source 到 Sink）。反压沿着相反的方向传播，沿着数据流向上游传播。

- Task (SubTask) 的每个并行实例都可以用三个一组的指标评价:

backPressureTimeMsPerSecond, subtask 被反压的时间

idleTimeMsPerSecond, subtask 等待某类处理的时间

busyTimeMsPerSecond, subtask 实际工作时间 在任何时间点，这三个指标相加都约等于 1000ms。

- 这些指标每两秒更新一次，上报的值表示 subtask 在最近两秒被反压（或闲或忙）的平均时长。当你的工作负荷是变化的需要尤其引起注意。比如，一个以恒定50%负载工作的 subtask 和另一个每秒钟在满负载和闲置切换的 subtask 的 busyTimeMsPerSecond 值相同，都是 500ms。

- 闲置的任务为蓝色，完全被反压的任务为黑色，完全繁忙的任务被标记为红色。中间的所有值都表示为这三种颜色之间的过渡色。

Detail SubTasks TaskManagers Watermarks Accumulators BackPressure Metrics FlameGraph

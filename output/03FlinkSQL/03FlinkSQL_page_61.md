## 第61页

- 基于日志 CDC 有以下这几种优势:

- 能够捕获所有数据的变化，捕获完整的变更记录。在异地容灾，数据备份等场景中得到广泛应用，如果是基于查询的 CDC 有可能导致两次查询的中间一部分数据丢失

- 每次 DML 操作均有记录无需像查询 CDC 这样发起全表扫描进行过滤，拥有更高的效率和性能，具有低延迟，不增加数据库负载的优势

- 无需入侵业务，业务解耦，无需更改业务模型

- 捕获删除事件和捕获旧记录的状态，在查询 CDC 中，周期的查询无法感知中间数据是否删除

## 12.2. Flink CDC

- 在以前的数据同步中，比如我们想实时获取数据库的数据，一般采用的架构就是采用第三方工具，比如canal、debezium等，实时采集数据库的变更日志，然后将数据发送到kafka等消息队列。然后再通过其他的组件，比如flink、spark等等来消费kafka的数据，计算之后发送到下游系统。

Kafka Connect

MySQL

Debezium

kafka.

Flink SQL

elasticsearch

采集 (E)

计算 (T)

传输 (L)

- 以前架构，我们需要部署canal（debezium）+ kafka，然后flink再从kafka消费数据，这种架构下我们需要部署多个组件并且数据也需要落地到kafka

- 于是Flink提供了cdc connector

| 概念 | 基于查询的 CDC | 基于日志的 CDC |
|---|---|---|
| 每次捕获变更更发起 Select 查询读取数据存储系统的 log，例如进行全表扫描，过滤出查询之间 MySQL 里面的 binlog持续监控 变更的数据 |  |
| 开源产品 | Sqoop, Kafka JDBC Source | Canal, Maxwell, Debezium |
| 执行模式 | Batch | Streaming |
| 捕获所有数据的变化 | <img src="https://latex.codecogs.com/svg.image:\times"/> | <img src="https://latex.codecogs.com/svg.image:\checkmark"/> |
| 低延迟，不增加数据库负载 | <img src="https://latex.codecogs.com/svg.image:\times"/> | <img src="https://latex.codecogs.com/svg.image:\checkmark"/> |
| 不侵入业务（LastUpdated字段） | <img src="https://latex.codecogs.com/svg.image:\times"/> | <img src="https://latex.codecogs.com/svg.image:\checkmark"/> |
| 捕获删除事件和旧记录的状态 | <img src="https://latex.codecogs.com/svg.image:\times"/> | <img src="https://latex.codecogs.com/svg.image:\checkmark"/> |
| 捕获旧记录的状态 | <img src="https://latex.codecogs.com/svg.image:\times"/> | <img src="https://latex.codecogs.com/svg.image:\checkmark"/> |

www.yjxxt.com

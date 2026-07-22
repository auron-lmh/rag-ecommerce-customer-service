## 第12页

## 1.5. 状态TTL

## 1.5.1. 基本概念

- Flink 可以对状态数据进行存活时长管理，即"新陈代谢"；

- 淘汰的机制主要是基于存活时间(Time To Live); 存活时长的计时器可以在数据被读、写时重置;

- TTL 存活管理粒度是到元素级的（如 liststate 中的每个元素，mapstate 中的每个 entry）

## 1.5.2. 相关参数

- TTL 的相关配置参数及其内含的机制，全部封装在 StateTtlConfig类中

- StateTtlConfig各参数详解

- ◦ setTtl

- 表示状态的过期时间，是一个 org.apache.flink.api.common.time.Time 对象。

- 一旦设置了 TTL，那么如果上次访问的时间戳 + TTL 超过了当前时间，则表明状态过期了

- ◦ setUpdataType

- 表示状态时间戳的更新的时机，是一个 Enum 对象。

- org.apache.flink.api.common.state.StateTtlConfig.UpdateType

| 策略类型 | 描述 |
|---|---|
| StateTtlConfig.UpdateType.Disabled | 禁用TTL，永不过期 |
| StateTtlConfig.UpdateType.OnCreateAndWrite | 每次写操作都会更新State的最后访问时间 |
| StateTtlConfig.UpdateType.OnReadAndWrite | 每次读写操作都会跟新State的最后访问时间 |

- ◦ setStateVisibility

- 表示对已过期但还未被清理掉的状态如何处理，也是 Enum 对象。

$$
this.listState =
$$

$$
context.getOperatorStateStore().getListState(descriptor);
$$

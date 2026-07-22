## 第37页

## 参数名

## 类型

## 默认值

## 作用描述

cypher_llm

LLM实例

None

单独指定生成Cypher查询的模型（与

qa_llm解耦)

qa_llm

LLM实例

None

单独指定生成自然语言回答的模型（与

cypher_llm解耦)

exclude_types

List[str]

None

top_k

int

None

限制查询返回的结果数量（优化性能）

- 注意:

use_function_response (bool):默认为 False。

True : 将数据库上下文封装为工具调用响应，适用于与 Agent 等系统的集成。

False : 直接返回查询结果，适用于传统的问答场景。

- 使用场景

与 Agent 集成: 当需要将数据库查询作为工具调用的一部分时，启用

use_function_response。

传统问答系统: 如果仅需要直接的查询结果，保持 use_function_response=False。

- 代码块

1 chain = GraphCypherQACHain.from_llm(

2 llm=llm,

3 graph=graph,

4 cypher_prompt=cypher_prompt,

5 verbose=True,

6 use_function_response=True,

7 allow_dangerous_requests=True,

8 )

## 第76页

Ragas将评估过程抽象为几个核心组件，它们是构建评估流程的基石。

评估样本 (EvaluationRecord):

评估样本是一个单一的结构化数据实例，用于评估和衡量您的LLM应用在特定场景下的性能。它代

表AI应用需要处理的单个交互单元或特定用例。在 Ragas 中，评估样本使用

SingleTurnSample 和 MultiTurnSample 类来表示。

SingleTurnSample

SingleTurnSample 代表用户、LLM 和用于评估的预期结果之间的单轮交互。它适用于涉及单个问

答对的评估和RAG评估。以下示例演示如何在基于 RAG 的应用中创建 SingleTurnSample 实

例以评估单轮交互。在此场景中，用户提出问题，AI 提供答案。我们将创建一个

SingleTurnSample 实例来表示此交互，包括任何检索到的上下文、参考答案和评估标准。

user_input(question):用户提出的问题。

response: RAG系统生成的答案。

retrieved_contexts:检索器返回的用于生成答案的文档片段。

ground_truth (reference)：(可选)人工标注的标准答案，用于某些指标的评估。

代码块

1 from ragas import SingleTurnSample # 导入Ragas框架中的单轮对话样本类

2

# 用户问题

4 user_input = "法国的首都市什么?"

5

# 检索到的上下文（例如从知识库或搜索引擎获取，）

7 retrieved_contexts = ["巴黎是法国的首都和人口最多的城市。"]

8

# AI生成的响应

10 response = "法国的首都是巴黎。"

11

# 参考答案（标准答案）

13 reference = "巴黎"

14

15

# 创建单轮对话样本实例

17 sample = SingleTurnSample(

18 user_input=user_input, # 用户问题

19 retrieved_contexts=retrieved_contexts, # 检索到的上下文

20 response=response, # AI生成的响应

21 reference=reference, # 参考答案

22 )

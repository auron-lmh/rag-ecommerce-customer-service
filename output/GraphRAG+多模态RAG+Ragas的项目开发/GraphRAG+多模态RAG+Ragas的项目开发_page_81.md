## 第78页

# 33 user_input=conversation, # 用户输入的完整对话

# 34 reference=reference_response, # 参考答案

- 35 )

评估数据集 (EvaluationDataset): 由多个 EvaluationRecord 组成的集合，代表整个测试

集。

代码块

1 dataset = EvaluationDataset(samples=[sample1, sample2, sample3])

指标 (Metrics): 衡量RAG系统特定方面性能的尺子。这是Ragas的核心。

## 2.2 指标 (Metrics)

Ragas提供了一套丰富的指标，可分为以下几类

指标类别

适用场景

检索增强生成(RAG)

RAG系统评估

主要指标

Nvidia指标

优化LLM生成质量

上下文精度、上下文召回率、忠实度等

Agent或工具使用场景

Agent工作流评估

答案准确性、上下文相关性等

自然语言比较

生成内容质量评估

主题一致性、工具调用准确性等

传统非LLM指标

基础文本比较

事实正确性、语义相似性等

SQL指标

SQL查询系统评估

基于执行的Datacompy分数、SQL查询等效

通用目的指标

多场景通用评估

方面批评、简单标准评分等

其他任务

特定任务评估

摘要评估

## 3、检索增强生成 (RAG)的评估

指标类别

指标名称

适用场景

评估重点

RAG指标

上下文精度

检索精准度

检索结果中相关片段的比例

RAG指标

上下文召回率

检索全面性

检索覆盖答案所需信息的比例

RAG指标

忠实度

生成内容质量

答案与检索内容的一致性

RAG指标

回答相关性

生成内容质量

答案与问题的相关度

所有指标

答案准确性

生成答案的准确率

答案与给定问题的参考标准答案之间的一致性

3.1、上下文精度 (Context Precision)：检查 检索结果的 精准度

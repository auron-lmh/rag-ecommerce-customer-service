## 第10页

接收用户的查询请求。

根据查询所需的详细程度，选择合适的社区级别进行分析。

在选定的社区级别进行信息检索。

依据社区摘要生成初步的响应。

将多个相关社区的初步响应进行整合，形成一个全面的最终答案。

本地搜索

本地搜索方法将知识图谱中的结构化数据与输入文档中的非结构化数据结合起来，在查询时使用相关

实体信息来增强 LLM 上下文。它非常适合回答需要理解输入文档中提到的特定实体的问题（例

如，“洋甘菊的治疗特性是什么？”）

Local Search Dataflow

Entity-Text

Unit Mapping

Candidate

Text Units

Ranking +

Filtering

Prioritized

Text Units

Entity-Report

Mapping

Candidate

Community Reports

Ranking +

Filtering

Prioritized

Community Reports

Relationships

Candidate

Entities

Ranking +

Filtering

Prioritized

Entities

Relationships

Candidate

Relationships

Ranking +

Filtering

Prioritized

Relationships

Entity-Covariate

Mappings

Candidate

Covariates

详细过程：给定用户查询，以及可选的对话历史记录，本地搜索方法从知识图谱中识别出一组与用户

输入语义相关的实体。这些实体作为访问知识图谱的入口点，可以提取更多相关详细信息，例如连接

的实体、关系、实体协变量和社区报告。此外，它还会从与已识别实体相关的原始输入文档中提取相

关的文本块。然后对这些候选数据源进行优先级排序和过滤，以适应预定义大小的单个上下文窗口，

该窗口用于生成对用户查询的响应。

以下是 LocalSearch 类的关键参数

llm：用于生成响应的 OpenAI 模型对象

context_builder：用于准备来自知识模型对象集合的上下文数据的上下文构建器对象

system_prompt：用于生成搜索响应的提示模板。默认模板可以在system_prompt中找到

response_type：描述所需响应类型和格式的自由形式文本（例如，多个段落，多页报告）

llm_params：要传递给 LLM 调用的其他参数的字典（例如，温度、max_tokens）

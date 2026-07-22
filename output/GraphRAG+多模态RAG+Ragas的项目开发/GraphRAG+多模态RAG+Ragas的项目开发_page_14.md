## 第13页

以下是 DRIFTSearch 类 的关键参数

llm :用于生成响应的 OpenAI 模型对象

context_builder :用于从社区报告和查询信息准备上下文数据的 context builder 对象

config :用于定义 DRIFT 搜索超参数的模型。 DRIFT Config 模型

token_encoder :用于跟踪算法预算的令牌编码器。

query_state :在 Query State 中定义的状态对象，允许跟踪 DRIFT 搜索实例的执行，以及后续

Question Generation: 基于实体的问题生成

问题生成方法将来自知识图的结构化数据与来自输入文档的非结构化数据相结合，以生成与特定实体

相关的候选问题。给定先前用户问题的列表，问题生成方法使用与本地搜索中使用的相同上下文构建

方法来提取和优先处理相关的结构化和非结构化数据，包括实体、关系、协变量、社区报告和原始文

本块。然后将这些数据记录拟合到单个 LLM 提示中，以生成候选后续问题，这些问题代表数据中最重

以下是Question Generation 类的关键参数

llm : 用于响应生成的 OpenAI 模型对象

context_builder :上下文构建器对象，用于准备来自知识模型对象集合的上下文数据，使用

与本地搜索中相同的上下文构建器类

system_prompt : 用于生成候选问题的提示模板。 默认模板可以在system_prompt找到

llm_params : 要传递给 LLM 调用的附加参数（例如，温度、max_tokens）的字典

context_builder_params : 在为问题生成提示构建上下文时要传递给 context_builder

callbacks : 可选的回调函数，可用于为 LLM 的完成流事件提供自定义事件处理程序

第二章、Microsoft GraphRAG的安装

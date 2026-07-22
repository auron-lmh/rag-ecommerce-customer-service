## 第9页

对于所有需要下游向量搜索的工件，我们生成文本嵌入作为最后一步。这些嵌入直接写入配置的向量

存储。 默认情况下，我们嵌入实体描述、文本单元文本和社群报告文本。

Text Embedding Workflows

Text Units

Text Embedding

Graph Tables

Description Embedding

Community Reports

Content Embedding

构建索引后有输出表: https://msdocs.cn/graphrag/index/outputs/

可视化: https://msdocs.cn/graphrag/visualization_guide/#3-open-the-graph-in-gephi

GraphRAG的查询引擎

查询引擎是Graph RAG库的检索模块。它是Graph RAG库的两个主要组成部分之一，另一个是索引流

程管道。

Local Search

Global Search

DRIFT Search

Question Generation

Microsoft GraphRAG 提供local 和global 两种查询方式，分别对应local search 和global search。是

源于不同的粒度级别而构建出来用于处理不同类型问题的Pipeline, 其中:

Local Search 是基于实体的检索。

Global Search 则是基于社区的检索。

Microsoft GraphRAG 在查询阶段构建的流程，相较于构建索引阶段会更为直观。核心的具体步骤包

括:

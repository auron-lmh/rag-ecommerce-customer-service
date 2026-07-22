## 第34页

# prompt: ChatPromptTemplate | None

自定义给 LLM 的完整提示模板（LangChain 的 ChatPromptTemplate） 。

用途：你可以替换或扩展默认 prompt（例如给示例、规则、领域词典），对输出格式、命名规

范、属性命名风格等精细控制。若不提供，Transformer 会使用内置默认 prompt。

代码块

1 from langchain_experimental.graph_transformers.llm import LLMGraphTransformer

transformer = LLMGraphTransformer(

llm=llm,

strict_mode=True,

graph_docs = transformer.convert_to_graph_documents(documents)

# 解释：只允许 Person 与 Company 两类节点、且只允许 Person-WORKS_AT->Company 这种关

系; 只抽 name/title/email 属性。

transformer = LLMGraphTransformer(

llm=llm,

node_properties=True,

relationship_properties=True,

# 解释：允许任意节点、抽所有节点属性（更开放）

## 5、幂等增量写入写入Neo4j

graph.add_graph_documents(graph_documents)

该方法用于批量将已抽取的 GraphDocument （包含节点和关系结构）导入到 Neo4j 图数据库中，

该标签可以用于创建统一索引，对查询和插入性能有显著优化，尤其在节点类型多样或标签未知的

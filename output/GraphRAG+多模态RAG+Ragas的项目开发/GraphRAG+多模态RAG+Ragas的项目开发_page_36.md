## 第35页

include_source=True 参数（可选未启用）

若启用，该方法会引入每个源 Document（即原始文本块）作为一个独立节点，并通过

Mentions 关系将其与被抽取的实体节点连接。

优点包括:

让你能追踪每个实体来源自哪个文档，有利于源追溯、结果可解释性，以及实现“文档级

RAG”检索策略。

代码块

def upsert_to_neo4j(graph_documents):

include_source=True: 会把来源 Document 导入为 (:Document {id}),

并用 (:Document)-[:MENTIONS]->(实体) 连接;

baseEntityLabel=True: 给实体加二级标签 __Entity__, 结合唯一约束, 提升合并与查询性

能。

graph.add_graph_documents(

graph_documents,

baseEntityLabel=True,

# 添加 __Entity__ 次级标签，用于索引优化

# include_source=True # 包含来源 Document 节点，并连接关系

)

6、使用LangChain-Neo4j查询图数据库

在 LangChain 0.5.0 中, GraphCypherQACHain.from_llm() 是构建图数据库问答链的核心方
法。它将语言模型（LLM）与图数据库（如 Neo4j）结合，实现自然语言查询转化为 Cypher 查询的功
能。

代码块

chain = GraphCypherQACHain.from_llm(

llm=llm,

graph=graph,

allow_dangerous_requests=True,

cypher_prompt=cypher_prompt,

qa_prompt=qa_prompt,

validate_cypher=True,

return_intermediate_steps=True,

verbose=True,

)

resp = chain.invoke({"query": "马云是谁?"})

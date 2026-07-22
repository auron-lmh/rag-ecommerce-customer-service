## 第30页

# 1 pip install neo4j langchain-neo4j langchain-experimental

LangChain-Neo4j 是 LangChain 与 Neo4j 图数据库的深度集成工具，旨在通过大语言模型（LLM）增

强图数据的查询、生成和分析能力。

## 1. Neo4jGraph 操作封装

提供构造函数参数如 url, username, password, database, timeout, sanitize,

refresh_schema, enhanced_schema, driver_config 等选项，支持更灵活配置。

方法包括 query(), add_graph_documents(), refresh_schema(), close(), 可

用于执行 Cypher 查询、构建图结构、刷新 Schema 信息等。

## 2. Neo4jVector 向量索引管理

支持 from_documents(), from_texts(), from_existing_graph() 等多种方式构建

向量索引。

检索支持 similarity_search, similarity_search_with_score,

max_marginal_relevance_search 等，同时支持元数据过滤、Hybrid Search（语义+关

键词）。

内部包含 verify_version() 方法，用于检测 Neo4j 是否支持向量索引（必须版本 ≥

5.11.0）。

## 3. GraphCypherQACHain 与 查询纠正

支持将用户自然语言问题转化为 Cypher 查询、执行后将结果传回 LLM 生成自然语言回答，形成问

答链（QA）。

结合 CypherQueryCorrector 帮助纠正查询方向与结构，提升生成 Cypher 的准确性。

## 4. GraphDocument 与知识图构建

使用 GraphDocument, Node, Relationship 等类，可自定义构建图结构，并通过

add_graph_documents() 插入 Neo4j，同时支持关联来源（如 include_source）。

## 5. Memory: Neo4jChatMessageHistory 保存对话历史

支持以节点与关系形式，在 Neo4j 中保存、查询对话内容，用于上下文回溯、分析等场景

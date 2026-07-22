## 第31页

## 功能模块

## 描述

Neo4jGraph 图数据库驱动封装、执行查询、Schema 管理

Neo4jVector 向量索引创建与检索，支持语义搜索、Hybrid 搜索、过滤

GraphCypherQACHain 自然语言 → Cypher → 执行 → 自然语言回答

GraphDocument 等类 构建知识图结构，支持文档关联插入

CypherQueryCorrector 修正生成的 Cypher 查询结构与方向

Neo4jChatMessageHistory 在 Neo4j 中存储会话历史

## 1、连接Neo4j图数据库

1 graph = Neo4jGraph(

2

3

4

5

6

7

- enhanced_schema 参数详解

enhanced_schema 是 Neo4jGraph 的一个布尔类型参数，默认为 False;

若将其设置为 True，LangChain 将在初始化或刷新 schema 时，主动扫描数据库中的属性值，

并生成更丰富的 schema 信息，包括：

各属性的示例值（string 属性）；

若属性值类型为数字或日期，给出最小值（Min）和最大值（Max）；

若某属性值的可选种类小于约 10 个，会列出所有可能值，反之只保留一个示例值。

这种增强型 schema 能显著帮助 LLM 更准确地生成 Cypher 查询，因为它能利用具体数据样本进行构

造。

## 2、建立唯一约束(幂等)

这一约束确保所有带 Entity 标签的节点，其 id 属性在图中保持唯一性。写入与某已存在节点

同 id 的新节点时，会因冲突抛出错误，不会自动覆盖旧节点，也不会无声失败。如果用的是

MERGE 操作，将在遇到已存在节点时匹配该节点，进而允许更新该节点的关系或属性（通常结合

ON MATCH SET 使用）。在这种情况下，并不会创建新节点。

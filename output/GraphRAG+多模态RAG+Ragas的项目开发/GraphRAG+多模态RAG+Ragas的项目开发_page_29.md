## 第28页

# 1 MATCH (p:Person {id: '马云'})

2 RETURN p;

3 # 查询所有的Person标签实体(节点)，并且该节点的id值为：马云

4

5 # 还可以查询图中多个节点。此查询匹配所有带有 Person 标签的节点，并将结果限制为仅包含五

行。

6 MATCH (people:Person)

7 RETURN people

8 LIMIT 5

9

10 # 使用 DETACH DELETE 删除所有节点及其关系

11 MATCH (n)

12 DETACH DELETE n;

13

## 4、安装插件APOC插件

因为 LangChain 使用的 Neo4jGraph 类依赖于 APOC（Awesome Procedures On Cypher）插件

中的一些增强功能，比如 apoc.meta.data()。若 Neo4j 中未安装或启用这些功能，就会报错。

为什么要安装 APOC 插件?

APOC 插件提供丰富的扩展功能，包括元数据查询、函数、图投影、条件执行等，对构建

GraphRAG 的工作流非常关键。

LangChain 在连接图数据库时会依赖 APOC 提供的增强查询能力，例如快速获取模式信息

(schema)，否则不能执行图查询

## 一、上传插件的jar包到plugins目录

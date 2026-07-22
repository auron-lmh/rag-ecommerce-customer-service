## 第46页

人工智能集成

Embeddings 模型集成 Embedding 模型将非结构化数据转换为其在高维数据空间中的数字表示，

以便您能将其存储在 Milvus 中。目前，PyMilvus（Python SDK）集成了多个嵌入模型，以便您能

快速将数据准备成向量嵌入。

Reranker 模型集成 在信息检索和生成式人工智能领域，Reranker 是优化初始搜索结果顺序的重要

工具。PyMilvus 也集成了几种 Rerankers 模型，以优化初始搜索返回结果的顺序。

LangChain 和其他人工智能工具集成 在 GenAI 时代，LangChain 等工具受到了应用程序开发人员

的广泛关注。作为核心组件，Milvus 通常在此类工具中充当向量存储。

NVIDIA

ROBLOX

AT&T

BOSCH

ebay

Shopee

LINE

IKEA

Walmart

OMERS

ZipRecruiter

intuit

SmartNews

shutterstock

tokopedia

TREND

MICRO

COMPASS

IBM

dailylhunt

PayPal

AMERICAN

EXPRESS

SHEIN

REGENERON

new relic

DELL

NetApp

POSHMARK

salesforce

2、安装Milvus

Milvus Lite 是Milvus 的轻量级版本，Milvus Lite 可导入您的 Python 应用程序，提供 Milvus 的核心向

量搜索功能。Milvus Lite 已包含在Milvus 的 Python SDK 中。它可以通过 pip install

pymilvus 简单地部署。在 pymilvus 中，指定一个本地文件名作为 MilvusClient 的 uri 参数将使

用 Milvus Lite。

https://milvus.io/docs/zh/milvus_lite.md

一、安装和配置docker(Centos9或者RedHat 8~9)

代码块

1 # 1、添加阿里云 Docker 仓库

2 sudo dnf config-manager --add-repo https://mirrors.aliyun.com/docker-

ce/linux/centos/docker-ce.repo

3

4

5

# ubuntu apt 1、添加阿里云 Docker 仓库

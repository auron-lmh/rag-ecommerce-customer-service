# 🤖 Agentic RAG 电商智能客服系统

> 基于检索增强生成（RAG）的电商智能客服系统，支持多格式文档摄入、混合检索、幻觉检测自纠正、意图路由、人工介入、联网搜索等企业级功能。

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Milvus](https://img.shields.io/badge/Milvus-2.6-orange.svg)](https://milvus.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.1+-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## ✨ 核心特性

### 🔍 智能检索
- **五级降级策略**：原始查询 → LLM改写 → 查询扩展(Multi-Query+HyDE) → 联网搜索 → 诚实兜底
- **Hybrid Search**：BM25 稀疏检索 + 稠密向量检索 + WeightedRanker 融合
- **Reranker 精排**：qwen3-vl-rerank 多模态重排序
- **查询扩展**：Multi-Query 多角度扩展 + HyDE 假设性文档嵌入

### 🧠 质量保证
- **幻觉检测**：G-Eval 风格逐条事实断言检查
- **自纠正闭环**：最多2轮检测→提取缺失→改写重搜→重新生成
- **忠实度评分**：每个回答附带 faithfulness 分数

### 🎯 智能路由
- **意图分类**：LLM Function Calling，6类意图自动识别
- **人工介入**：退款/投诉/敏感话题自动触发，优先级管理
- **智能重检索**：多轮对话中判断追问/切换/澄清

### 🌐 联网搜索
- **双通道兜底**：智谱 GLM-4-Flash 优先，Tavily 备选
- **自动触发**：知识库无结果时自动联网搜索

### 🛡️ 企业级工程
- **三层缓存**：Query/Embedding/LLM 缓存，支持 Memory/Redis 双后端
- **成本监控**：每日统计、意图分布、P99延迟、告警规则
- **结构化日志**：日志轮转30天，专用日志方法
- **四层安全防御**：输入清洗/角色锚定/文档过滤/输出护栏
- **Docker 部署**：一键启动，支持水平扩展

### 🖥️ 完整界面
- **用户聊天界面**：流式对话、意图显示、来源追踪
- **管理员控制台**：人工介入处理、系统监控
- **知识库入库平台**：多格式文档上传解析

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户请求                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   LangGraph 图编排                           │
│  classify_intent → check_human → route_decision             │
│       ├── rag → retrieve → generate → END                   │
│       ├── sql → sql_handler → END                           │
│       ├── human → human_handler → END                       │
│       └── direct → direct_reply → END                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    五级降级检索                               │
│  Level 1: 原始查询 → Hybrid Search                          │
│  Level 2: LLM 改写 → 重新检索                               │
│  Level 3: 查询扩展(Multi-Query+HyDE) → 并行检索             │
│  Level 4: 联网搜索(智谱/Tavily)                             │
│  Level 5: 诚实兜底                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  幻觉检测 + 自纠正                           │
│  生成回答 → G-Eval检测 → 提取缺失 → 改写重搜 → 重新生成     │
└─────────────────────────────────────────────────────────────┘
```

## 📁 项目结构

```
├── src/
│   ├── ingestion/               # 模块1: 多格式数据摄入
│   │   ├── router.py            # 文件类型路由
│   │   ├── parser_pdf.py        # PDF 解析 (OCR)
│   │   ├── parser_image.py      # 图片解析 (VLM)
│   │   └── defenses.py          # 防御层 (预检/质量/缩放)
│   │
│   ├── chunking/                # 模块2: 智能分块策略
│   │   ├── router.py            # 策略路由
│   │   └── strategies/          # 4种策略 (Markdown/FAQ/语义/递归)
│   │
│   ├── embedding/               # 模块3+5: 向量化 + 检索
│   │   ├── embedder.py          # Qwen3-VL-Embedding
│   │   ├── milvus_store.py      # Milvus Hybrid Search
│   │   ├── retriever.py         # 检索器
│   │   ├── degradation.py       # 五级降级策略
│   │   └── query_expansion.py   # 查询扩展 (Multi-Query+HyDE)
│   │
│   ├── routing/                 # 模块4: 意图路由
│   │   ├── classifier.py        # LLM Function Calling
│   │   └── router.py            # 意图路由 + 查询改写
│   │
│   ├── retrieval/               # 模块5.5: Reranker
│   │   └── reranker.py          # Qwen3-VL-Reranker
│   │
│   ├── generation/              # 模块6: 幻觉检测
│   │   ├── hallucination_detector.py  # G-Eval 检测
│   │   └── self_correction.py   # 自纠正闭环
│   │
│   ├── conversation/            # 模块6.5: 流式对话
│   │   ├── streaming.py         # SSE 流式生成
│   │   ├── session_manager.py   # 会话管理 (SQLite)
│   │   ├── retrieval_judge.py   # 智能重检索判断
│   │   └── human_in_loop.py     # 人工介入机制
│   │
│   ├── engineering/             # 模块7-11: 工程化
│   │   ├── cache.py             # 三层缓存
│   │   ├── monitor.py           # 成本监控
│   │   ├── logger.py            # 结构化日志
│   │   ├── error_handler.py     # 错误处理
│   │   └── security.py          # 安全防护
│   │
│   ├── evaluation/              # 模块14: 评估系统
│   │   ├── evaluator.py         # 评测器
│   │   └── metrics.py           # 评估指标
│   │
│   ├── graph/                   # LangGraph 图编排
│   │   └── workflow.py          # StateGraph 工作流
│   │
│   ├── api/                     # 模块12: FastAPI API
│   │   ├── app.py               # 主应用
│   │   └── routers/             # 路由 (query/upload/chat/stream/stats)
│   │
│   └── admin/                   # 模块13: UI 界面
│       ├── gradio_app.py        # 知识库入库平台
│       ├── chat_ui.py           # 用户聊天界面
│       └── admin_ui.py          # 管理员控制台
│
├── docker-compose-rag.yml       # Docker 服务编排
├── Dockerfile                   # 应用镜像
├── requirements.txt             # Python 依赖
├── .env.example                 # 环境变量模板
└── pyproject.toml               # 项目配置
```

## 🚀 快速开始

### 环境要求

- Python 3.12+
- Docker & Docker Compose
- 8GB+ RAM（推荐）

### 1. 克隆项目

```bash
git clone https://github.com/your-username/rag-ecommerce-customer-service.git
cd rag-ecommerce-customer-service
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key：

```bash
# 阿里云百炼 (OCR/Embedding/Reranker)
BAILIAN_API_KEY=sk-xxxxxxxxxxxxxxxx

# DeepSeek (LLM 对话)
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx

# 智谱 (图片理解/联网搜索)
ZHIPU_API_KEY=xxxxxxxxxxxxxxxx.xxxxxxxx

# 向量数据库
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Redis 缓存
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 3. 启动服务

#### 方式一：Docker Compose（推荐）

```bash
# 启动 Milvus
docker-compose -f docker-compose-milvus.yml up -d

# 启动 RAG 服务
docker-compose -f docker-compose-rag.yml up -d --build
```

#### 方式二：本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 Milvus
docker-compose -f docker-compose-milvus.yml up -d

# 启动 API 服务
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

# 启动用户聊天界面
python -m src.admin.chat_ui

# 启动管理员控制台
python -m src.admin.admin_ui
```

### 4. 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| API 文档 | http://localhost:8000/docs | Swagger UI |
| 知识库入库 | http://localhost:7860 | 文档上传 |
| 用户聊天 | http://localhost:7861 | 客服对话 |
| 管理员 | http://localhost:7862 | 人工介入管理 |

### 5. 测试功能

```bash
# 健康检查
curl http://localhost:8000/api/health

# 对话测试
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "怎么退货？", "top_k": 5}'

# 检索测试
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "退货流程", "top_k": 5}'
```

## 📚 API 文档

### 核心端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/query` | POST | 语义检索 |
| `/api/chat` | POST | 智能客服对话 |
| `/api/chat/stream` | POST | 流式对话 (SSE) |
| `/api/upload` | POST | 文件上传入库 |
| `/api/health` | GET | 健康检查 |
| `/api/stats/daily` | GET | 每日统计 |
| `/api/stats/recent` | GET | 最近查询 |
| `/api/stats/alerts` | GET | 告警检查 |
| `/api/cache/stats` | GET | 缓存统计 |
| `/api/evaluate` | POST | 运行评测 |

### 请求示例

```bash
# 对话请求
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "iPhone 16 价格是多少？",
    "top_k": 5,
    "use_reranker": true
  }'

# 响应
{
  "query": "iPhone 16 价格是多少？",
  "intent": "product_consult",
  "confidence": 0.95,
  "target": "rag",
  "reply": "根据知识库信息...",
  "results": [...],
  "faithfulness": 0.92,
  "needs_human": false
}
```

## 🔧 配置说明

### 模型配置

```bash
# LLM 模型
DEFAULT_MODEL=deepseek-chat           # 主模型
FALLBACK_MODEL=qwen-plus              # 备用模型

# Embedding 模型
EMBEDDING_MODEL=qwen3-vl-embedding    # 向量化模型
EMBEDDING_DIM=2048                     # 向量维度

# Reranker 模型
RERANKER_MODEL=qwen3-vl-rerank        # 重排序模型
RERANKER_ENABLED=true                  # 是否启用

# OCR 模型
OCR_MODEL=qwen-vl-ocr-1028            # PDF OCR

# 视觉模型
VISION_MODEL=glm-4v-flash             # 图片理解
```

### 检索配置

```bash
# 检索参数
RETRIEVAL_TOP_K=5                      # 返回结果数
RETRIEVAL_SIMILARITY_THRESHOLD=0.7     # 相似度阈值

# 缓存配置
QUERY_CACHE_TTL=3600                   # 查询缓存 TTL (秒)
EMBEDDING_CACHE_ENABLED=true           # 是否启用 Embedding 缓存

# 联网搜索
WEB_SEARCH_ENABLED=true                # 是否启用联网搜索
ZHIPU_WEB_SEARCH_ENABLED=true          # 是否启用智谱联网搜索
```

## 🐳 Docker 部署

### 服务架构

```yaml
services:
  redis:       # 缓存
  api:         # FastAPI API
  gradio:      # 知识库入库平台
  chat-ui:     # 用户聊天界面
  admin-ui:    # 管理员控制台
```

### 部署命令

```bash
# 启动所有服务
docker-compose -f docker-compose-rag.yml up -d --build

# 查看状态
docker-compose -f docker-compose-rag.yml ps

# 查看日志
docker-compose -f docker-compose-rag.yml logs -f api

# 停止服务
docker-compose -f docker-compose-rag.yml down
```

## 📊 监控与告警

### 监控端点

```bash
# 每日统计
curl http://localhost:8000/api/stats/daily

# 告警检查
curl http://localhost:8000/api/stats/alerts

# 缓存统计
curl http://localhost:8000/api/cache/stats
```

### 告警阈值

| 指标 | 阈值 | 说明 |
|------|------|------|
| 幻觉率 | > 5% | 触发排查 |
| P99 延迟 | > 3s | 检查向量库/LLM |
| 单日成本 | > 10 元 | 通知 |

## 🧪 评估系统

```bash
# 运行评测
curl -X POST http://localhost:8000/api/evaluate

# 评测单条查询
curl -X POST http://localhost:8000/api/evaluate/query \
  -H "Content-Type: application/json" \
  -d '{"question": "怎么退货？", "ground_truth": "退货流程"}'
```

### 评估指标

| 指标 | 说明 |
|------|------|
| Recall@5 | 前5个结果是否命中 |
| MRR | 平均倒数排名 |
| Faithfulness | 忠实度 |
| Keyword Coverage | 关键词覆盖率 |
| Latency Score | 延迟分数 |

## 🔒 安全特性

- **输入清洗**：检测 Prompt 注入攻击
- **角色锚定**：System Prompt 加固
- **文档过滤**：入库前检查恶意内容
- **输出护栏**：防止系统提示词泄露
- **速率限制**：防滥用（10次/分钟）

## 📖 文档

- [模块 0：开发环境搭建](docs/module-0-setup.md)
- [模块 1-3：数据摄入 + 分块 + 向量化](docs/module-1-3-data.md)
- [模块 4-5：意图路由 + 检索](docs/module-4-5-retrieval.md)
- [模块 6-6.5：幻觉检测 + 流式对话](docs/module-6-conversation.md)
- [模块 7-12：工程化 + 部署](docs/module-7-12-engineering.md)
- [模块 13-14：UI + 评估](docs/module-13-14-ui.md)
- [使用文档：运维 + 常见问题](docs/usage-guide.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用框架
- [LangGraph](https://github.com/langchain-ai/langgraph) - 图编排框架
- [Milvus](https://github.com/milvus-io/milvus) - 向量数据库
- [FastAPI](https://github.com/tiangolo/fastapi) - Web 框架
- [Gradio](https://github.com/gradio-app/gradio) - UI 框架

## 📧 联系方式

- 项目链接：https://github.com/your-username/rag-ecommerce-customer-service
- 问题反馈：https://github.com/your-username/rag-ecommerce-customer-service/issues

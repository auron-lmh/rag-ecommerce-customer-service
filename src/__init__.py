"""Agentic RAG 电商智能客服系统

模块:
    ingestion  — 多格式数据摄入 (PDF/Word/Excel/网页/图片)
    chunking   — 智能分块策略
    embedding  — Embedding + 向量库设计
    routing    — 意图路由系统
    retrieval  — 混合检索 + 多级降级 + Reranking
    generation — 幻觉检测 + 自纠正闭环
    conversation — 流式输出 + 多轮对话管理
    engineering — 缓存 + 监控 + 日志 + 错误处理 + 安全
    api        — FastAPI REST 接口
    admin      — Gradio 管理后台
"""

__version__ = "0.1.0"

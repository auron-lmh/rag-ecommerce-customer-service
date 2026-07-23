# RAG 电商客服系统 — 优化报告

日期: 2026-07-23

## 一、P0 级问题修复（必须）

### 1. MilvusClient 连接泄漏

**问题:** 每次请求创建新 MilvusClient 实例，连接池完全失效。

**修复:** 改为实例级单例，复用连接。

**文件:** `src/embedding/milvus_store.py`

```python
# 修复前
@property
def client(self) -> MilvusClient:
    return MilvusClient(uri=self._uri, user=self.user, password=self.password, timeout=10)

# 修复后
def __init__(self, ...):
    self._client: Optional[MilvusClient] = None  # 实例级单例

@property
def client(self) -> MilvusClient:
    if self._client is None:
        self._client = MilvusClient(uri=self._uri, user=self.user, password=self.password, timeout=10)
    return self._client
```

### 2. SSE 检索阻塞事件循环

**问题:** 同步阻塞的检索调用在 async 生成器中执行，阻塞事件循环。

**修复:** 用 `asyncio.to_thread()` 包装同步调用。

**文件:** `src/api/routers/stream.py`

```python
# 修复前
degradation_result = strategy.search_with_degradation(query=..., top_k=..., use_rerank=...)

# 修复后
degradation_result = await asyncio.to_thread(
    strategy.search_with_degradation,
    query=route_result.rewritten_query,
    top_k=top_k,
    use_rerank=use_reranker,
)
```

### 3. HITL 中断处理不完整

**问题:** LangGraph 中断时返回 None 或包含 `__interrupt__` 属性，代码未处理。

**修复:** 检查中断状态并返回正确的响应。

**文件:** `src/graph/workflow.py`

```python
# 修复后
result = self._app.invoke(initial_state, config)

if hasattr(result, "__interrupt__"):
    return {**initial_state, "__interrupt__": result.__interrupt__, "answer": "等待人工审批中..."}

if result is None:
    return {**initial_state, "__interrupt__": True, "answer": "等待人工审批中..."}
```

### 4. LLMClient 同步/异步混用

**问题:** 同步方法用 `requests`，异步方法用 `httpx`，混用导致维护困难。

**修复:** 统一使用 `httpx`，同步用 `httpx.Client`，异步用 `httpx.AsyncClient`。

**文件:** `src/engineering/llm_client.py`

```python
# 修复前
import requests
resp = requests.post(...)

# 修复后
import httpx
client = self._get_sync_client()
resp = client.post(..., timeout=httpx.Timeout(timeout))
```

---

## 二、P1 级问题修复（建议）

### 5. 缓存 Key 缺少过滤条件

**问题:** 同一 query 带不同 filter 会返回错误的缓存结果。

**修复:** 缓存 Key 包含所有查询参数。

**文件:** `src/embedding/retriever.py`

```python
# 修复前
cache_key = f"{query}:{top_k}:{use_hybrid}:{use_rerank}"

# 修复后
cache_key = f"{query}:{top_k}:{use_hybrid}:{use_rerank}:{filter_by_doc_type}:{filter_by_source}:{threshold}"
```

### 6. 自纠正 LLM 调用次数爆炸

**问题:** 单次请求可能有 15+ 次 LLM 调用，延迟不可控。

**修复:** 设置 LLM 调用预算（MAX_LLM_CALLS = 8）。

**文件:** `src/generation/self_correction.py`

```python
MAX_LLM_CALLS = 8

# 在纠正循环中检查预算
if llm_call_count >= MAX_LLM_CALLS:
    logger.warning("LLM 调用已达预算上限 (%d/%d)，停止纠正", llm_call_count, MAX_LLM_CALLS)
    break
```

### 7. Embedding 零向量填充污染检索

**问题:** 向量化失败时填充零向量，污染检索结果。

**修复:** 记录失败索引，跳过失败的向量。

**文件:** `src/embedding/embedder.py`

```python
# 修复后
failed_indices: set[int] = set()
# ... 失败时记录索引
if i in failed_indices:
    skipped_count += 1
    continue  # 跳过失败的向量
```

### 8. 速率限制器非线程安全

**问题:** 多线程并发时可能超出 RPM 限制。

**修复:** 加 `threading.Lock`。

**文件:** `src/embedding/embedder.py`

```python
class _RateLimiter:
    def __init__(self, ...):
        self._lock = __import__("threading").Lock()

    def acquire(self):
        with self._lock:
            # ... 限制逻辑
```

### 9. 评估不评测生成质量

**问题:** 评估用标准答案而非实际生成的回答。

**修复:** 新增 `evaluate_query_with_generation` 方法，运行完整 RAG 流程。

**文件:** `src/evaluation/evaluator.py`

```python
def evaluate_query_with_generation(self, test_case, use_llm_eval=False):
    """完整 RAG 流程评估（检索 + 生成）"""
    corrector = get_corrector(self.retriever)
    result = corrector.generate_with_correction(query=test_case.question, ...)
    # 用实际生成的回答评估忠实度
    faithfulness = calculate_faithfulness(result.answer, retrieved_docs, ...)
```

### 10. Docstring 与默认值不一致

**问题:** 文档说默认 0.5，实际默认 0.3/0.7。

**修复:** 更新 Docstring。

**文件:** `src/embedding/retriever.py`

---

## 三、性能优化

### load_collection 优化

**问题:** 每次查询都调用 `load_collection`（重操作）。

**修复:** 使用 `get_load_state` 检查，避免重复加载。

**文件:** `src/embedding/milvus_store.py`

```python
def _ensure_ready(self):
    # ...
    try:
        state = self.client.get_load_state(COLLECTION_NAME)
        if state.get("state") != "loaded":
            self.client.load_collection(COLLECTION_NAME)
    except Exception:
        self.client.load_collection(COLLECTION_NAME)
```

### Milvus 表达式注入防护

**问题:** 过滤表达式存在注入风险。

**修复:** 转义双引号。

**文件:** `src/embedding/retriever.py`

```python
safe_doc_type = filter_by_doc_type.replace('"', '\\"')
filter_parts.append(f'doc_type == "{safe_doc_type}"')
```

---

## 四、面试话术

### 讲项目时可以这样说：

> "我在开发过程中发现并修复了几个关键的工程问题：
> 1. MilvusClient 连接管理——原来是每次请求新建连接，改为实例级单例复用
> 2. SSE 流式响应——检索阶段阻塞事件循环，用 asyncio.to_thread 解决
> 3. Human-in-the-Loop——LangGraph 中断状态处理不完整，加了 __interrupt__ 检查
> 4. 评估体系——原来只评估标准答案，现在支持完整 RAG 流程评估
> 5. 自纠正循环——加了 LLM 调用预算，防止延迟爆炸"

### 这展示了你：
- 能发现深层工程问题
- 有性能优化意识
- 理解异步编程
- 有生产级思维

---

## 五、部署信息

- 虚拟机: 192.168.191.128
- 项目路径: /root/rag-system/
- Docker 容器: rag-api, rag-chat-ui, rag-gradio, rag-admin-ui
- 更新时间: 2026-07-23

---

## 六、下一步优化（可选）

### P2 级问题（面试加分项，非必须）

1. **RRF 融合** — 多路召回结果融合，提升检索质量
2. **本地 Cross-Encoder** — bge-reranker-v2 备选，减少 API 依赖
3. **RAGAS 集成** — 4 维度标准评估（faithfulness, answer_relevancy, context_precision, context_recall）
4. **Graph RAG** — 知识图谱增强，支持多跳推理
5. **语义缓存** — 相似查询缓存，降低延迟和成本

### 电商特有优化

1. **多维索引** — 产品级/属性级/评价级/FAQ 级
2. **实体抽取** — 品牌/型号/SKU/价格区间
3. **同义词扩展** — "手机壳"="保护套"
4. **库存感知** — 过滤缺货商品
5. **个性化** — 用户画像 + 购买历史
6. **多模态** — 图片 + 文本联合检索

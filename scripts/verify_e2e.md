# 端到端验证清单 — 面试前必跑

> 在部署环境 VM 上执行（API 已在 `192.168.191.128:8000`）。
> 目的：30+ 模块是单元测试过的，这里确认**真实链路能跑通**，并截图存证。
> 每个用例：curl 命令 → 预期结果 → ✅/❌

```bash
BASE=http://192.168.191.128:8000
# 本地则: BASE=http://localhost:8000
```

---

## 1. 基础设施

```bash
curl $BASE/api/health          # ✅ {"status":"ok","milvus":"ok",...}
curl $BASE/api/stats           # ✅ collection 存在, total_vectors > 0
```

## 2. 检索 + 普通对话（RAG 主链路）

```bash
curl -X POST $BASE/api/query -H "Content-Type: application/json" \
  -d '{"query": "怎么退货", "top_k": 5}'
# ✅ results 非空，含 source_file

curl -X POST $BASE/api/chat -H "Content-Type: application/json" \
  -d '{"query": "怎么退货？", "session_id": "demo1"}'
# ✅ reply 基于知识库回答，intent=return_refund，faithfulness>0
```

## 3. 订单工具（SQL 工具节点，模块24）

```bash
curl -X POST $BASE/api/chat -H "Content-Type: application/json" \
  -d '{"query": "我的订单 OD20260701001 到哪了？", "session_id": "demo2"}'
# ✅ 不再返回"请提供订单号"，而是:
#   "订单 OD20260701001：已发货 - 承运商: 顺丰速运 (SF1234567890) ..."
```

## 4. 退货结构化政策（policy 工具节点，模块30）

```bash
curl -X POST $BASE/api/chat -H "Content-Type: application/json" \
  -d '{"query": "退货运费谁出？", "session_id": "demo3"}'
# ✅ 结构化回答含"质量问题退货商家承担" / "非质量问题买家承担"
```

## 5. 多轮记忆 + 指代消解（模块25/27）

```bash
# 第1轮: 建立实体记忆
curl -X POST $BASE/api/chat -H "Content-Type: application/json" \
  -d '{"query": "我上周领了满300减50券", "session_id": "mem1"}'

# 第2轮: 跨轮指代"上次那个券" → 应能解析到具体券
curl -X POST $BASE/api/chat -H "Content-Type: application/json" \
  -d '{"query": "上次那个券怎么用？", "session_id": "mem1"}'
# ✅ reply 提到"满300减50券"（实体ledger生效）
```

## 6. 情绪识别 → 安抚转人工（模块25）

```bash
curl -X POST $BASE/api/chat -H "Content-Type: application/json" \
  -d '{"query": "你们什么垃圾公司，我要去12315投诉！", "session_id": "demo4"}'
# ✅ emotion=extreme, needs_human=true, reply 是安抚话术
# ✅ handoff_payload 非空（含 emotion/entities/attempted_actions）
```

## 7. 高敏承诺护栏（模块29）

```bash
# 问一个含退款承诺的问题，观察是否走核验/转人工
curl -X POST $BASE/api/chat -H "Content-Type: application/json" \
  -d '{"query": "退款几天能到账？", "session_id": "demo5"}'
# ✅ 若忠实度不足 → needs_human=true 且 human_reason 含"高敏承诺需核验"
```

## 8. 复杂查询分解（模块28）

```bash
curl -X POST $BASE/api/chat -H "Content-Type: application/json" \
  -d '{"query": "这款手机和那款耳机有什么区别？", "session_id": "demo6"}'
# ✅ degradation_method=decomposed（或正常回答且检索到两方面内容）
```

---

## 截图存证清单（面试展示用）

- [ ] `GET /api/stats` → 向量数
- [ ] 用例3 订单工具回复
- [ ] 用例4 退货政策回复
- [ ] 用例5 第二轮"上次那个券"回复
- [ ] 用例6 情绪转人工 + 交接包

## 若失败排查

| 症状 | 排查 |
|---|---|
| 检索空结果 | 知识库未入库 → 跑 `python scripts/upload_docs_final.py` |
| Milvus 不可达 | `docker compose up -d` 先启 Milvus |
| LLM 无回复 | 检查 `.env` 的 DEEPSEEK_API_KEY |
| 订单工具未命中 | mock 单号：`OD20260701001`(已发货) / `OD20260701002`(待发货) / `SF1234567890`(运输中) |

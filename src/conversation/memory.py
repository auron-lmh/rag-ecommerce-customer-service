"""会话记忆系统 — 三层记忆：滚动摘要 + 结构化实体 + 历史检索

背景（面试题"上次那个券"）:
  用户 N 轮前提到"满300减50券"，之后问"上次那个券"，系统要能解析到那张券。
  朴素滑动窗口（只留最近 N 轮）会把它挤出窗口 → 无法解析。

三层记忆（业界实践: 无单一技术能解决，需分层 + 记忆管理器）:
  L1 短期窗口  最近 N 轮原样保留（保最新、保高频）
  L2 滚动摘要  更早的对话压缩成实体感知摘要（保要点，不整段塞）
  L3 实体记忆  每轮抽取 券/订单/金额 等实体存 ledger（保精确，指代直接查）

记忆管理器 build_context(): 按当前 query 组装"最小有用上下文"——
  最近对话 > 相关实体 > 历史检索片段 > 滚动摘要（按 token 预算裁剪）。

设计取舍:
  - 实体抽取用确定性正则（零 LLM 成本、可测试）；生产可换 LLM 抽取
  - 历史检索用词法打分（字符 bigram 重叠）；生产可换向量检索（Embedding）
  - 滚动摘要用 LLM，失败降级为截断（graceful degradation）
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# 记忆窗口配置
RECENT_TURNS = 6  # 最近几轮（对）原样保留
MAX_TURNS = 60  # 记忆保留的最大轮数（超出丢弃最旧，摘要已兜底）
MAX_SUMMARY_TOKENS = 600  # 滚动摘要 token 预算
MAX_CONTEXT_TOKENS = 1500  # build_context 总 token 预算
MAX_RETRIEVE = 2  # 历史检索返回片段数


# ═══════════════════════════════════════
# 实体模型 + 抽取器（L3）
# ═══════════════════════════════════════


@dataclass
class Entity:
    """会话实体（ledger 条目）"""

    type: str  # coupon / order / amount
    value: str  # 规范值，如 "满300减50券"
    ts: str = ""  # 出现时间
    status: str = ""  # 券: 可用/已用/过期（示例语义）

    @property
    def key(self) -> str:
        return f"{self.type}:{self.value}"


# 抽取模式
_COUPON_PATTERNS = [
    r"满\s*\d+\s*元?\s*减\s*\d+\s*元?(?:券)?",  # 满300减50(券)
    r"\d+\s*元\s*(?:无门槛)?(?:优惠)?券",  # 5元无门槛券 / 10元优惠券
    r"(?:无门槛券|优惠券|折扣券|兑换券|平台券|运费险券)",  # 通用券类型
]
_ORDER_PATTERNS = [
    r"(?:OD|E)\d{6,}",  # OD20260701001 / E123456789
    r"订单号\s*[:：]?\s*[\w-]+",
]
_AMOUNT_PATTERNS = [r"(?:¥|￥)?\s*\d+(?:\.\d+)?\s*(?:元|块)"]  # 300元 / 50块


class EntityExtractor:
    """实体抽取器 — 确定性正则（券/订单/金额）"""

    def extract(self, text: str) -> list[Entity]:
        if not text:
            return []
        entities: list[Entity] = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for m in re.findall("|".join(_COUPON_PATTERNS), text):
            v = re.sub(r"\s+", "", m)
            entities.append(Entity(type="coupon", value=v, ts=now))
        for m in re.findall("|".join(_ORDER_PATTERNS), text):
            v = (
                m.strip().split(":")[-1].split("：")[-1].strip()
                if "号" in m
                else m.strip()
            )
            entities.append(Entity(type="order", value=v, ts=now))
        for m in re.findall("|".join(_AMOUNT_PATTERNS), text):
            entities.append(Entity(type="amount", value=m.strip(), ts=now))
        return entities


def _merge_ledger(ledger: list[Entity], new_entities: list[Entity]) -> list[Entity]:
    """合并实体到 ledger（按 type:value 去重，保留最新）"""
    index = {e.key: i for i, e in enumerate(ledger)}
    for ent in new_entities:
        if ent.key in index:
            ledger[index[ent.key]] = ent  # 更新为最新
        else:
            index[ent.key] = len(ledger)
            ledger.append(ent)
    return ledger


# ═══════════════════════════════════════
# 会话记忆（每会话一个实例）
# ═══════════════════════════════════════

_SUMMARY_PROMPT = """你是电商客服对话摘要器。将对话压缩为简短的实体感知摘要。

已有摘要:
{summary}

新增对话:
用户: {user}
客服: {assistant}

规则:
1. 合并到已有摘要，只输出更新后的摘要
2. 保留关键事实: 券/优惠/金额/订单号/商品/用户承诺/决策
3. 新信息覆盖旧信息（如政策变更）
4. 不超过 120 字"""


class SessionMemory:
    """三层会话记忆

    使用方式:
        mem = SessionMemory("sess-1")
        mem.record_turn("用户消息", "客服回复")
        context = mem.build_context("上次那个券")
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._turns: list[tuple[str, str]] = []  # [(user, assistant), ...]
        self._entities: list[Entity] = []
        self._summary: str = ""
        self._folded: int = 0  # 已折入摘要的轮数

    # ── 写入 ──

    def record_turn(self, user_text: str, assistant_text: str = "") -> None:
        """记录一轮对话：抽实体 + 更新滚动摘要"""
        # L3: 实体抽取（用户 + 客服两侧都可能出现关键实体）
        new_entities = EntityExtractor().extract(user_text or "")
        if assistant_text:
            new_entities += EntityExtractor().extract(assistant_text)
        _merge_ledger(self._entities, new_entities)

        # 追加本轮
        self._turns.append((user_text or "", assistant_text or ""))

        # 超上限丢弃最旧（摘要已兜底）
        if len(self._turns) > MAX_TURNS:
            self._turns.pop(0)
            if self._folded > 0:
                self._folded -= 1

        # L2: 超出最近窗口的旧轮 → 滚动摘要
        self._fold_old_turns()

    def _fold_old_turns(self) -> None:
        """把最近窗口之外的旧轮折叠进滚动摘要"""
        while self._folded < len(self._turns) - RECENT_TURNS:
            user, assistant = self._turns[self._folded]
            self._summary = self._summarize(self._summary, user, assistant)
            self._folded += 1

    def _summarize(self, summary: str, user: str, assistant: str) -> str:
        """LLM 滚动摘要，失败降级为截断拼接"""
        try:
            from src.engineering.llm_client import get_llm_client

            client = get_llm_client()
            new_summary = client.chat_with_fallback(
                messages=[
                    {
                        "role": "user",
                        "content": _SUMMARY_PROMPT.format(
                            summary=summary or "（无）",
                            user=(user or "")[:200],
                            assistant=(assistant or "")[:300],
                        ),
                    }
                ],
                fallback_value=summary,
                temperature=0.1,
                max_tokens=200,
                timeout=10,
            ).strip()
            if new_summary and new_summary != summary:
                return new_summary[:200]
        except Exception as e:
            logger.warning("滚动摘要失败，降级截断: %s", e)
        # 降级: 截断拼接，保住最核心的一句
        core = (user or "")[:40]
        return f"{summary}\n[{core}]" if summary else f"[{core}]"

    # ── 读取 ──

    def build_context(self, query: str, max_tokens: int = MAX_CONTEXT_TOKENS) -> str:
        """记忆管理器: 按 query 组装最小有用上下文

        优先级: 最近对话 > 相关实体 > 历史检索片段 > 滚动摘要
        """
        parts: list[str] = []

        # L3: 相关实体（query 命中券/订单/金额）
        entity_facts = self._relevant_entities(query)
        if entity_facts:
            parts.append(
                "【相关实体】\n"
                + "\n".join(f"- {e.type}: {e.value}" for e in entity_facts)
            )

        # 历史检索（query 指向过去的实体/事件时召回）
        if self._folded > 0:
            retrieved = self._retrieve(query)
            if retrieved:
                parts.append("【历史相关片段】\n" + "\n".join(retrieved))

        # L2: 滚动摘要（旧对话压缩）
        if self._summary:
            parts.append(f"【旧对话摘要】{self._summary}")

        # L1: 最近对话原文
        recent = self._turns[-RECENT_TURNS:]
        if recent:
            lines = []
            for u, a in recent:
                if u:
                    lines.append(f"用户: {u[:120]}")
                if a:
                    lines.append(f"客服: {a[:200]}")
            parts.append("【最近对话】\n" + "\n".join(lines))

        # token 预算裁剪（粗略按字符≈token 估算，从后往前保优先级）
        return _trim_context("\n\n".join(parts), max_tokens)

    def _relevant_entities(self, query: str) -> list[Entity]:
        """query 相关的实体（按类型词/值命中）"""
        if not query or not self._entities:
            return []
        hits = []
        type_words = {"券": "coupon", "订单": "order", "金额": "amount", "钱": "amount"}
        for ent in self._entities:
            if ent.value and ent.value in query:
                hits.append(ent)
            elif ent.type == type_words.get(
                next((w for w in type_words if w in query), ""), ""
            ):
                hits.append(ent)
        # 去重（同一类型同值只留一个）
        seen = set()
        uniq = []
        for e in hits:
            if e.key not in seen:
                seen.add(e.key)
                uniq.append(e)
        return uniq[:5]

    def _retrieve(self, query: str, top_k: int = MAX_RETRIEVE) -> list[str]:
        """历史检索式召回（L1 进阶）: 词法打分（字符 bigram 重叠）

        生产可替换为 Embedding 向量检索；这里零 API 成本、确定性。
        """
        if not query:
            return []
        old_turns = self._turns[: self._folded]
        if not old_turns:
            return []

        scored = []
        for user, assistant in old_turns:
            text = f"用户: {user} 客服: {assistant}"
            score = _lexical_score(query, text)
            if score > 0.15:
                scored.append((score, text[:180]))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored[:top_k]]


def _lexical_score(query: str, text: str) -> float:
    """字符 bigram 重叠率（中文词法相关性粗打分）"""
    q = {query[i : i + 2] for i in range(len(query) - 1)}
    t = {text[i : i + 2] for i in range(len(text) - 1)}
    if not q:
        return 0.0
    return len(q & t) / len(q)


def _trim_context(context: str, max_tokens: int) -> str:
    """粗略按 token 裁剪（中文≈字符数，英文/数字偏少，取宽松）"""
    if not context:
        return ""
    budget = max(max_tokens * 2, 200)  # 宽松字符预算
    if len(context) <= budget:
        return context
    return context[:budget] + "\n[上下文过长，已截断]"


# ═══════════════════════════════════════
# 记忆管理器（会话级单例）
# ═══════════════════════════════════════

_MEMORY_SESSIONS: dict[str, SessionMemory] = {}


def get_session_memory(session_id: str) -> SessionMemory:
    """获取会话记忆（按 session_id，进程内缓存）"""
    if session_id not in _MEMORY_SESSIONS:
        _MEMORY_SESSIONS[session_id] = SessionMemory(session_id)
    return _MEMORY_SESSIONS[session_id]


def reset_memory() -> None:
    """清空所有会话记忆（测试用）"""
    _MEMORY_SESSIONS.clear()

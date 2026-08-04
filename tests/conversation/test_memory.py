"""三层会话记忆测试 — 实体ledger / 滚动摘要 / 历史检索"""

from src.conversation.memory import (
    Entity,
    EntityExtractor,
    SessionMemory,
    _lexical_score,
    _merge_ledger,
)


class TestEntityExtractor:
    def test_coupon_specific(self):
        ents = EntityExtractor().extract("我上周领了满300减50券")
        assert any(e.type == "coupon" and "满300减50" in e.value for e in ents)

    def test_coupon_generic(self):
        ents = EntityExtractor().extract("我的无门槛券还能用吗")
        assert any(e.type == "coupon" for e in ents)

    def test_order(self):
        ents = EntityExtractor().extract("订单号OD20260701001怎么还没到")
        assert any(e.type == "order" and "OD20260701001" in e.value for e in ents)

    def test_amount(self):
        ents = EntityExtractor().extract("退了我300元")
        assert any(e.type == "amount" and "300元" in e.value for e in ents)

    def test_empty_and_plain(self):
        assert EntityExtractor().extract("") == []
        assert EntityExtractor().extract("随便聊聊天气") == []


class TestMergeLedger:
    def test_dedupe_by_type_value_keep_latest(self):
        ledger = [Entity("coupon", "满300减50券", status="可用")]
        _merge_ledger(ledger, [Entity("coupon", "满300减50券", status="已用")])
        assert len(ledger) == 1
        assert ledger[0].status == "已用"

    def test_append_new_entities(self):
        ledger = []
        _merge_ledger(ledger, [Entity("coupon", "满300减50券")])
        _merge_ledger(ledger, [Entity("order", "OD20260701001")])
        assert len(ledger) == 2


class TestSessionMemory:
    def test_record_extracts_entities_from_both_sides(self):
        mem = SessionMemory("s1")
        mem.record_turn("我上周领了满300减50券", "您的满300减50券已记录")
        assert any(e.type == "coupon" for e in mem._entities)

    def test_build_context_includes_coupon_for_coupon_query(self):
        """核心场景: "上次那个券" → 上下文里能看到具体券"""
        mem = SessionMemory("s1")
        mem.record_turn("我上周领了满300减50券", "")
        ctx = mem.build_context("上次那个券怎么用")
        assert "满300减50券" in ctx

    def test_rolling_summary_folds_old_turns(self, monkeypatch):
        from src.conversation import memory as memory_mod

        monkeypatch.setattr(memory_mod, "RECENT_TURNS", 1)  # 收缩窗口加速
        mem = SessionMemory("s1")
        mem._summarize = lambda summary, u, a: f"{summary}[折:{u[:6]}]"
        for i in range(5):
            mem.record_turn(f"第{i}轮问题", f"第{i}轮回答")
        assert mem._folded > 0
        assert mem._summary  # 摘要非空

    def test_history_retrieval_recalls_old_topic(self, monkeypatch):
        """旧轮被挤出窗口后，历史检索仍能召回相关片段"""
        from src.conversation import memory as memory_mod

        monkeypatch.setattr(memory_mod, "RECENT_TURNS", 1)
        mem = SessionMemory("s1")
        mem._summarize = lambda summary, u, a: f"{summary}[摘要]"
        mem.record_turn("我说过想要一台蓝色手机", "")
        for i in range(4):
            mem.record_turn(f"其他问题{i}", f"回答{i}")
        ctx = mem.build_context("蓝色手机")
        assert "蓝色手机" in ctx

    def test_build_context_contains_recent_dialogue(self):
        mem = SessionMemory("s1")
        mem.record_turn("怎么退货？", "签收后7天内可退")
        ctx = mem.build_context("怎么退货？")
        assert "怎么退货" in ctx
        assert "7天内可退" in ctx


class TestLexicalScore:
    def test_relevant_text_scores_high(self):
        assert _lexical_score("蓝色手机", "用户说想要蓝色手机") > 0.5

    def test_unrelated_text_scores_zero(self):
        assert _lexical_score("退货", "讨论订单退款") == 0.0

    def test_empty_query(self):
        assert _lexical_score("", "任意文本") == 0.0

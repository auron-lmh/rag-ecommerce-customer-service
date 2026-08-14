"""human_in_loop 置信度判断测试 — 未提供 confidence 不误转人工"""

from src.conversation.human_in_loop import HumanInLoopHandler


def test_no_confidence_does_not_trigger_human():
    """P1 回归：不传 confidence 时，平静查询不误转人工（修复前默认 0.0 恒转人工）"""
    handler = HumanInLoopHandler()
    result = handler.check_needs_human(query="你好，在吗", intent="chitchat")
    assert result["needs_human"] is False


def test_low_confidence_triggers_human():
    """对照组：明确传低 confidence 才转人工"""
    handler = HumanInLoopHandler()
    result = handler.check_needs_human(query="你好", intent="chitchat", confidence=0.3)
    assert result["needs_human"] is True

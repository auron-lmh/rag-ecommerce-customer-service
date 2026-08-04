"""情绪识别测试 — 分级 + 置信度"""

from src.conversation.emotion import EmotionLevel, get_emotion_detector


class TestEmotionDetector:
    def test_calm(self):
        r = get_emotion_detector().detect("你好，请问怎么退货？")
        assert r.level == EmotionLevel.CALM

    def test_extreme_abuse(self):
        r = get_emotion_detector().detect("你们什么垃圾公司，我要去12315投诉曝光！")
        assert r.level == EmotionLevel.EXTREME
        assert r.confidence >= 0.7

    def test_extreme_legal_threat(self):
        r = get_emotion_detector().detect("不退钱我就去法院起诉你")
        assert r.level == EmotionLevel.EXTREME

    def test_angry_exclamations(self):
        r = get_emotion_detector().detect("怎么还没到！！过分！")
        assert r.level == EmotionLevel.ANGRY

    def test_angry_keyword(self):
        r = get_emotion_detector().detect("你们的服务真是气死我了")
        assert r.level == EmotionLevel.ANGRY

    def test_dissatisfied(self):
        r = get_emotion_detector().detect("发货太慢了，有点失望")
        assert r.level == EmotionLevel.DISSATISFIED

    def test_empty_returns_calm(self):
        r = get_emotion_detector().detect("")
        assert r.level == EmotionLevel.CALM

    def test_none_returns_calm(self):
        r = get_emotion_detector().detect(None)
        assert r.level == EmotionLevel.CALM

    def test_confidence_bounded(self):
        r = get_emotion_detector().detect("垃圾 骗子 黑店 滚 妈的")
        assert 0.0 <= r.confidence <= 1.0

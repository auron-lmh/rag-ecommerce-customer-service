"""模块 11.7 PII 脱敏 — 敏感信息自动检测与替换

对标: AdnanSattar/enterprise-rag-stack/security/pii_redaction.py

为什么 PII 脱敏是电商场景的必需:
  - 用户可能在客服对话中输入: 手机号、订单号、身份证号、银行卡号
  - 这些信息如果被存入 Milvus → 被检索出来 → 展示给其他用户 → 法律风险
  - 入库前脱敏 + 检索前脱敏 = 双重保障
  - GDPR / 个人信息保护法 的合规基本要求

使用:
    from src.engineering.pii_redactor import PIIRedactor

    redactor = PIIRedactor()
    safe_text, found = redactor.redact("我的手机是13800138000，请帮我查订单")
    # safe_text = "我的手机是[手机号]，请帮我查订单"
    # found = [{"type": "手机号", "original": "13800138000", "masked": "138***00"}]

    # 仅检测不替换
    items = redactor.detect("身份证 440101199001011234")
    # items = [{"type": "身份证", "masked": "440***34"}]
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════
# PII 正则模式（中国电商场景专用）
# ═══════════════════════════════════════════════

# 注意: Python 3 默认 re.UNICODE，中文字符被视为 \w
#       因此 \b 和 (?<!\w) 在中文字符和 ASCII 字符之间不会匹配
#       使用具体字符类做边界检查：(?<![a-zA-Z0-9]) / (?![a-zA-Z0-9])
#       或用 (?<!\d)...(?!\d) 防止数字串被截断

PII_PATTERNS: dict[str, str] = {
    # 手机号: 1[3-9] + 9 位数字，前后不能是数字（防止截断长数字串）
    "手机号": r"(?<!\d)1[3-9]\d{9}(?!\d)",
    # 身份证: 17 位数字 + 数字或 X，前后不能是数字
    "身份证": r"(?<!\d)\d{17}[\dXx](?!\d)",
    # 银行卡: 16-19 位纯数字
    "银行卡": r"(?<!\d)\d{16,19}(?!\d)",
    # 邮箱（前后不能是 ascii 字母数字，避免匹配 URL 中的）
    "邮箱": r"(?<![a-zA-Z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}(?![a-zA-Z0-9.])",
    # IP 地址：前后不能是数字
    "IP地址": r"(?<!\d)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?!\d)",
    # 常见电商订单号格式: 大写字母前缀 + 12-20 位数字，前缀前不能是字母
    "订单号": r"(?<![a-zA-Z])(?:DD|TB|JD|PDD|DY|MT|E)\d{12,20}(?!\d)",
    # 姓名模式（"姓名：XXX" 或 "我叫XXX" 后的 2-4 个汉字）
    # 捕获组1 是匹配的姓名文本
    "姓名": r"(?:姓名[：:]\s*)([一-龥]{2,4})(?:[\s，。,\.]|$)",
}

# 注意：详细地址模式太过激进（包含"号"等单字），容易误匹配替换标签如 [手机号]
# 改为仅在入库文档清洗时启用，不在对话入口使用
# 如需启用，取消下面的注释：
# _ADDRESS_PATTERN = r"(?:省|市|区|县|街道|路|号|栋|单元|室)\S{2,20}(?:省|市|区|县|街道|路|号|栋|单元|室)"


class PIIRedactor:
    """PII 脱敏器

    使用正则模式检测和替换文本中的敏感个人信息。

    设计决策:
      - 用正则而非 LLM：速度快（<1ms），确定性，无额外 API 成本
      - 覆盖中国电商主要 PII 类型：手机号/身份证/银行卡/邮箱/订单号/地址/姓名
      - 替换标签保留语义：[手机号] 而非直接删除 → 调试时知道这里曾有敏感信息
    """

    def __init__(self, custom_patterns: Optional[dict[str, str]] = None):
        """初始化脱敏器

        Args:
            custom_patterns: 额外的 PII 正则模式 {类型名: 正则}
                             会合并到默认模式中，覆盖同名模式
        """
        self._patterns = {**PII_PATTERNS}
        if custom_patterns:
            self._patterns.update(custom_patterns)

    # ── 公共 API ──

    def redact(self, text: str) -> tuple[str, list[dict]]:
        """脱敏文本中的敏感信息

        Args:
            text: 原始文本

        Returns:
            (脱敏后文本, 被脱敏项列表)
            脱敏项格式: {"type": "手机号", "original": "13800138000", "masked": "138***00"}
        """
        if not text:
            return text, []

        result = text
        found: list[dict] = []

        # 按模式顺序依次替换（避免订单号被银行卡模式先匹配）
        for pii_type, pattern in self._patterns.items():
            matches = list(re.finditer(pattern, result))
            # 从后往前替换，避免索引偏移
            for match in reversed(matches):
                # 如果模式有命名或捕获组，取组1；否则取整个匹配
                value = match.group(1) if match.lastindex else match.group()
                if not value:
                    value = match.group()  # fallback
                span_start = match.start(1) if match.lastindex else match.start()
                span_end = match.end(1) if match.lastindex else match.end()
                masked = self._mask_value(value, pii_type)
                found.append(
                    {
                        "type": pii_type,
                        "original": value,
                        "masked": masked,
                    }
                )
                result = result[:span_start] + f"[{pii_type}]" + result[span_end:]

        if found:
            logger.info(
                "PII 脱敏: 检测到 %d 项 (%s)",
                len(found),
                ", ".join(set(f["type"] for f in found)),
            )

        return result, found

    def detect(self, text: str) -> list[dict]:
        """仅检测敏感信息，不替换

        Args:
            text: 原始文本

        Returns:
            检测到的 PII 项列表（含脱敏预览值）
        """
        if not text:
            return []

        found: list[dict] = []
        seen: set[tuple[int, int]] = set()  # 防止同一段文本被多个模式重复报告

        for pii_type, pattern in self._patterns.items():
            for match in re.finditer(pattern, text):
                span = match.span()
                # 跳过已被其他模式匹配过的位置
                if any(s[0] <= span[0] < s[1] or s[0] < span[1] <= s[1] for s in seen):
                    continue
                seen.add(span)
                value = match.group()
                found.append(
                    {
                        "type": pii_type,
                        "masked": self._mask_value(value, pii_type),
                    }
                )

        return found

    def is_safe(self, text: str) -> bool:
        """检查文本是否不含任何 PII"""
        return len(self.detect(text)) == 0

    # ── 内部 ──

    @staticmethod
    def _mask_value(value: str, pii_type: str) -> str:
        """生成脱敏预览值（保留首尾用于调试）

        规则:
          - <=4 字符: 全部替换 ***
          - 5-8 字符: 保留首 2 + 尾 1，中间 ***
          - >8 字符:  保留首 3 + 尾 2，中间 ***
        """
        n = len(value)
        if n <= 4:
            return "***"
        if n <= 8:
            return value[:2] + "***" + value[-1:]
        return value[:3] + "***" + value[-2:]


# ═══════════════════════════════════════════════
# 模块级单例
# ═══════════════════════════════════════════════

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_pii_redactor() -> PIIRedactor:
    """获取 PIIRedactor 单例"""
    return PIIRedactor()


# ═══════════════════════════════════════════════
# 便捷函数（链式调用）
# ═══════════════════════════════════════════════


def redact_text(text: str) -> tuple[str, list[dict]]:
    """便捷函数：脱敏文本"""
    return get_pii_redactor().redact(text)


def detect_pii(text: str) -> list[dict]:
    """便捷函数：检测文本中的 PII"""
    return get_pii_redactor().detect(text)

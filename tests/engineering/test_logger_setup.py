"""logger setup 测试 — setup_root_logging 幂等（P1 修复）"""

import logging

from src.engineering.logger import setup_root_logging


def test_setup_root_logging_idempotent():
    root = logging.getLogger()
    setup_root_logging()
    first = len(root.handlers)
    setup_root_logging()
    second = len(root.handlers)

    assert first > 0  # 至少配置了 handler
    assert first == second  # 幂等，不重复加 handler

"""分块策略实验 — 对比不同策略/参数的效果

用法:
    python -m src.chunking.experiment
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .models import ChunkResult
from .router import chunk_document

logger = logging.getLogger(__name__)


@dataclass
class ExperimentResult:
    """单次实验的结果"""

    label: str
    doc_type: str
    strategy: str
    target_size: int
    overlap: int
    total_chunks: int
    total_tokens: int
    avg_chunk_size: float
    size_stddev: float
    min_chunk: int = 0
    max_chunk: int = 0

    @property
    def score(self) -> float:
        """综合评分 — 越高越好

        评分维度:
          1. 均匀度 (40%): chunk size stddev 越小越好
          2. 目标命中 (30%): avg 偏离 target 越小越好
          3. 块数合理 (30%): 不要太多碎片也不要太少大块
        """
        import math

        # 均匀度 (stddev / avg 归一化)
        if self.avg_chunk_size > 0:
            cv = self.size_stddev / self.avg_chunk_size  # 变异系数
            uniformity = max(0, 1.0 - cv)
        else:
            uniformity = 0.0

        # 目标命中
        if self.target_size > 0:
            deviation = abs(self.avg_chunk_size - self.target_size) / self.target_size
            target_hit = max(0, 1.0 - deviation)
        else:
            target_hit = 0.0

        # 块数合理 (5-50为合理区间)
        if 5 <= self.total_chunks <= 50:
            count_score = 1.0
        elif self.total_chunks < 5:
            count_score = self.total_chunks / 5.0
        else:
            count_score = max(0, 1.0 - (self.total_chunks - 50) / 100)

        return 0.4 * uniformity + 0.3 * target_hit + 0.3 * count_score

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "doc_type": self.doc_type,
            "strategy": self.strategy,
            "target_size": self.target_size,
            "overlap": self.overlap,
            "total_chunks": self.total_chunks,
            "total_tokens": self.total_tokens,
            "avg_chunk_size": round(self.avg_chunk_size, 1),
            "size_stddev": round(self.size_stddev, 1),
            "min_chunk": self.min_chunk,
            "max_chunk": self.max_chunk,
            "score": round(self.score, 3),
        }


def run_experiment(
    text: str,
    source_file: str = "sample.md",
    doc_type=None,
    target_sizes: list[int] | None = None,
) -> list[ExperimentResult]:
    """对比不同参数的实验矩阵

    Args:
        text: 待分块文本
        source_file: 来源文件名
        doc_type: 文档类型（自动选策略）
        target_sizes: 对比的目标大小列表，默认 [256, 512, 768, 1024]

    Returns:
        按 score 降序排列的实验结果
    """
    if target_sizes is None:
        target_sizes = [256, 512, 768, 1024]

    results: list[ExperimentResult] = []

    for target_size in target_sizes:
        overlap = int(target_size * 0.1)

        result = chunk_document(
            text,
            source_file,
            doc_type,
            target_size=target_size,
            max_size=int(target_size * 2),
        )

        if result.chunks:
            sizes = [c.char_count for c in result.chunks]
            min_c, max_c = min(sizes), max(sizes)
        else:
            sizes = []
            min_c = max_c = 0

        exp = ExperimentResult(
            label=f"{doc_type.value if doc_type else 'text'}_{target_size}",
            doc_type=doc_type.value if doc_type else "plain_text",
            strategy=result.strategy.value,
            target_size=target_size,
            overlap=overlap,
            total_chunks=len(result.chunks),
            total_tokens=result.total_tokens,
            avg_chunk_size=result.avg_chunk_size,
            size_stddev=result.size_stddev,
            min_chunk=min_c,
            max_chunk=max_c,
        )
        results.append(exp)

        logger.info(
            "实验 %s: %d chunks, avg=%.0f, std=%.0f, score=%.3f",
            exp.label,
            exp.total_chunks,
            exp.avg_chunk_size,
            exp.size_stddev,
            exp.score,
        )

    results.sort(key=lambda r: r.score, reverse=True)
    return results


def print_report(results: list[ExperimentResult]) -> None:
    """打印人类可读的实验报告"""
    print("\n" + "=" * 70)
    print("🧪 分块策略实验报告")
    print("=" * 70)

    if not results:
        print("  (无结果)")
        return

    # 表头
    header = (
        f"{'排名':<5} {'标签':<20} {'策略':<12} {'目标':<6} "
        f"{'块数':<5} {'平均':<8} {'标准差':<8} {'评分':<7}"
    )
    print(header)
    print("-" * 70)

    for rank, r in enumerate(results, 1):
        line = (
            f"{rank:<5} {r.label:<20} {r.strategy:<12} {r.target_size:<6} "
            f"{r.total_chunks:<5} {r.avg_chunk_size:<8.0f} {r.size_stddev:<8.0f} {r.score:<7.3f}"
        )
        if rank == 1:
            line = f"🏆 {line[2:]}"
        print(line)

    print("-" * 70)
    best = results[0]
    print(f"✅ 最佳配置: {best.label}")
    print(
        f"   策略={best.strategy}, 目标={best.target_size} token, "
        f"产出={best.total_chunks} chunks, 平均大小={best.avg_chunk_size:.0f} char"
    )


def run_on_test_data() -> list[ExperimentResult]:
    """使用内置测试数据运行实验"""
    test_text = _get_test_markdown()
    from src.ingestion.models import DocType

    return run_experiment(test_text, "退货政策.pdf", DocType.PDF)


def _get_test_markdown() -> str:
    """模拟一份电商售后政策文档"""
    return """# 售后服务政策

## 退货说明

用户可在签收后7天内申请退货。商品须保持原包装完好，不影响二次销售。
以下商品不支持退货：生鲜食品、定制商品、虚拟商品、已拆封的个人护理用品。

退货时请确保商品配件齐全，包括赠品、说明书、保修卡等。如有缺失将影响退款金额。

## 退款流程

商品退回仓库验收后，退款将在1-3个工作日内原路返回。
如超过3个工作日未收到退款，请联系客服查询退款进度。

退款金额包含商品金额和已支付的运费。如果是部分退货，退款按比例计算。

### 银行卡退款

银行卡退款到账时间为3-7个工作日，具体以银行处理速度为准。
如超过7个工作日未到账，请致电发卡银行查询。

### 支付宝/微信退款

支付宝和微信支付退款通常即时到账。退款将退回到原支付账户，请勿注销绑定账户。

## 换货说明

商品存在质量问题时，支持换货服务。换货有效期同退货政策，为签收后7天内。

换货流程：提交换货申请 → 审核通过 → 上门取件 → 仓库验收 → 发出新商品。
整个换货周期通常为5-7个工作日。

### 换货次数限制

同一订单同一商品仅支持换货一次。如换货后仍不满意，可申请退货退款。

## 质量争议处理

收到商品后如发现质量问题，请拍照保留证据并在24小时内联系客服。
客服将在2小时内给出初步处理方案。复杂问题将升级至质检部门，24小时内出具质检报告。

质量问题的认定以质检报告为准。轻微瑕疵（如线头、色差）不属于质量问题。

## 运费政策

### 退货运费

质量问题导致的退货，运费由平台承担。取件时请告知快递员费用由寄方付。
非质量问题的退货（如不喜欢、买错、尺码不合适），运费由买家承担。

### 换货运费

质量问题换货双向运费由平台承担。非质量问题换货运费由买家承担。

## 特殊商品政策

### 电子产品

电子产品保修期为购买之日起12个月。保修期内非人为损坏免费维修。
人为损坏（进水、摔落、自行拆修）不在保修范围内。

保修需提供有效购买凭证（订单截图或电子发票）。

### 服装鞋帽

服装鞋帽支持7天无理由退换货。试穿请保持商品清洁，不要撕掉标签。
鞋类商品请在干净地面试穿，鞋底如有磨损将影响退货。

### 食品保健

食品类商品一经售出概不退换。如发现包装破损或变质，请拍照联系客服。
保质期剩余不足1/3的商品，平台将在商品页面明确标注。

## 客服联系方式

在线客服：APP内「我的」→「客服中心」→「在线客服」
服务时间：每日 9:00-21:00
热线电话：400-xxx-xxxx (工作日 9:00-18:00)
"""

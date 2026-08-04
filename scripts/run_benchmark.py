"""Benchmark 运行脚本 — 跑评估数据集，输出 RAG 指标报告（面试必问 Recall@5）

用法:
    python scripts/run_benchmark.py                            # 仅检索 + Embedding 快速模式
    python scripts/run_benchmark.py --with-generation          # 完整 RAG（检索+生成）
    python scripts/run_benchmark.py --use-llm-eval             # LLM 精确评估忠实度
    python scripts/run_benchmark.py --limit 10                 # 只跑前10条（冒烟）
    python scripts/run_benchmark.py --save-dir reports         # 报告保存目录

前置条件（在部署环境 VM 上跑）:
    - Milvus 已启动且知识库已入库（scripts/upload_docs_final.py 或 Gradio 入库平台）
    - .env 配置了 BAILIAN_API_KEY（embedding）+ DEEPSEEK_API_KEY（LLM）

输出:
    - 控制台指标报告（Recall@5 / MRR / Faithfulness / Latency P50/P95/P99）
    - JSON 报告保存到 <save-dir>/benchmark_<mode>_<时间戳>.json
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# 允许直接从 scripts/ 目录运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG 检索/生成 benchmark")
    parser.add_argument(
        "--with-generation",
        action="store_true",
        help="运行完整 RAG（检索+生成），默认仅检索",
    )
    parser.add_argument(
        "--use-llm-eval",
        action="store_true",
        help="用 LLM 评估忠实度，默认 Embedding 快速模式",
    )
    parser.add_argument("--limit", type=int, default=0, help="只跑前 N 条（0=全部）")
    parser.add_argument("--save-dir", default="reports", help="报告保存目录")
    args = parser.parse_args()

    from src.evaluation import get_evaluator

    evaluator = get_evaluator()

    # ── 1. 加载数据集 ──
    test_cases = evaluator.load_dataset()
    if args.limit:
        test_cases = test_cases[: args.limit]
    if not test_cases:
        print("❌ 评估数据集为空")
        sys.exit(1)
    print(f"\n📊 加载评估数据: {len(test_cases)} 条")

    # ── 2. 运行评测 ──
    mode = "完整RAG" if args.with_generation else "仅检索"
    eval_mode = "LLM精确" if args.use_llm_eval else "Embedding快速"
    print(f"🔄 运行模式: {mode} / {eval_mode}")

    try:
        results = evaluator.evaluate_dataset(
            test_cases,
            use_llm_eval=args.use_llm_eval,
            with_generation=args.with_generation,
        )
    except Exception as e:
        print(f"\n❌ 评测失败: {e}")
        print(
            "请检查: 1) Milvus 是否启动  2) 知识库是否已入库  3) API Key 是否配置(.env)"
        )
        sys.exit(1)

    # ── 3. 输出报告 ──
    _print_report(results)

    # ── 4. 保存报告 ──
    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_tag = "gen" if args.with_generation else "retrieval"
    report_path = save_dir / f"benchmark_{mode_tag}_{ts}.json"
    report_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n💾 报告已保存: {report_path}")


def _print_report(results: dict) -> None:
    if "error" in results:
        print(f"\n❌ {results['error']}")
        return

    print("\n" + "=" * 56)
    print("  📈 RAG Benchmark 指标报告")
    print("=" * 56)
    quality_keys = [
        ("recall@5", "检索召回率"),
        ("precision@5", "检索精确率"),
        ("mrr", "平均倒数排名"),
        ("ndcg@5", "归一化折损累积"),
        ("faithfulness", "忠实度"),
        ("keyword_coverage", "关键词覆盖率"),
        ("hallucination_rate", "幻觉率"),
        ("avg_correction_rounds", "平均纠正轮数"),
    ]
    for key, label in quality_keys:
        if key in results:
            print(f"  {label:<8} {key:<16} {results[key]:.4f}")
    print("-" * 56)
    latency_keys = [
        "avg_latency_ms",
        "p50_latency_ms",
        "p95_latency_ms",
        "p99_latency_ms",
        "latency_score",
    ]
    for key in latency_keys:
        if key in results:
            print(
                f"  {'延迟' if 'latency_ms' in key else '延迟分':<8} {key:<16} {results[key]}"
            )
    print("=" * 56)


if __name__ == "__main__":
    main()

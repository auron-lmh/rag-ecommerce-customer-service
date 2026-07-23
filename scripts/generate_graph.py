"""LangGraph 流程图生成脚本 — 在 Windows 上运行，生成 PNG 图片

使用方式:
    cd D:\Rag_project\E-commerce_Customer_Service_System
    python scripts/generate_graph.py

依赖:
    pip install langgraph pygraphviz
    # Windows 上如果没有 graphviz，会自动降级为 mermaid 文本输出
"""

import sys
from pathlib import Path

# 添加项目根目录到 sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def generate_graph_image():
    """生成 LangGraph 流程图 PNG"""
    output_dir = PROJECT_ROOT / "docs" / "graphs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "langgraph_workflow.png"

    try:
        from src.graph.workflow import build_rag_workflow

        workflow = build_rag_workflow()
        app = workflow.compile()

        # 尝试生成 PNG
        try:
            png_data = app.get_graph().draw_mermaid_png()
            output_path.write_bytes(png_data)
            print(f"✅ 流程图已生成: {output_path}")
            print(f"   大小: {len(png_data) / 1024:.1f} KB")
            return True
        except Exception as e:
            print(f"⚠️  PNG 生成失败 ({e})，尝试 Mermaid 文本输出...")

        # 降级: 输出 Mermaid 文本
        mermaid_text = app.get_graph().draw_mermaid()
        mermaid_path = output_dir / "langgraph_workflow.mmd"
        mermaid_path.write_text(mermaid_text, encoding="utf-8")
        print(f"✅ Mermaid 文件已生成: {mermaid_path}")
        print("   可以用以下方式查看:")
        print("   1. 打开 https://mermaid.live 粘贴内容")
        print("   2. VS Code 安装 Mermaid Preview 插件")
        print("   3. 用 mmdc CLI 转换: mmdc -i input.mmd -o output.png")

        # 同时生成一个 HTML 预览文件
        html_path = output_dir / "langgraph_workflow.html"
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>LangGraph RAG Workflow</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; padding: 20px; background: #f5f5f5; }}
        h1 {{ color: #333; }}
        .mermaid {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .info {{ margin-top: 20px; color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <h1>电商智能客服 RAG 系统 — LangGraph 工作流</h1>
    <div class="mermaid">
{mermaid_text}
    </div>
    <div class="info">
        <p>生成时间: 自动生成</p>
        <p>项目: E-commerce Customer Service System</p>
    </div>
    <script>mermaid.initialize({{startOnLoad:true, theme:'default'}});</script>
</body>
</html>"""
        html_path.write_text(html_content, encoding="utf-8")
        print(f"✅ HTML 预览已生成: {html_path}")
        print("   双击即可在浏览器中查看流程图")

        return True

    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("   请确保已安装依赖: pip install langgraph")
        return False
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def print_graph_structure():
    """打印图结构文本（无需依赖）"""
    print("\n📊 LangGraph 工作流结构:")
    print("=" * 60)
    print("""
    [用户输入]
        │
        ▼
    ┌──────────────────┐
    │  classify_intent │  ← LLM Function Calling 意图分类
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │   check_human    │  ← 高风险场景预判
    └────────┬─────────┘
             │
     ┌───────┼───────┬──────────┐
     ▼       ▼       ▼          ▼
  [rag]   [sql]   [human]   [direct]
     │       │       │          │
     ▼       ▼       ▼          ▼
┌────────┐ ┌────┐ ┌──────┐ ┌────────┐
│retrieve│ │SQL │ │human │ │direct  │
│Hybrid  │ │查询│ │handle│ │ reply  │
└───┬───┬┘ └──┬─┘ └──┬───┘ └───┬────┘
    │   │      │       │         │
    │   └──────┼───────┼─────────┼──→ [END]
    │          │       │         │
 [有结果]  [无结果]   [END]     [END]
    │          │
    ▼          ▼
┌────────┐ ┌──────────┐
│generate│ │web_search│ ← 新增: 联网搜索
│+幻觉   │ │(智谱     │    独立图节点
│检测    │ │ /Tavily) │
└───┬────┘ └────┬─────┘
    │           │
    └─────┬─────┘
          │
          ▼
┌───────────────┐
│evaluate_quality│ ← 新增: 质量评估
│ (faithfulness │    (忠实度+检索质量)
│  + retrieval) │
└───┬───────┬───┘
    │       │
 [通过]  [不通过]
    │       │
    ▼       ▼
 [END]  ┌────────────────┐
        │ human_approval │ ← 新增: 真正 HITL
        │ (interrupt_    │    LangGraph 中断等待
        │  before)       │    外部注入人力决策
        └───┬───────┬────┘
            │       │
        [批准]   [拒绝]
            │       │
            ▼       ▼
          [END]  ┌───────────────────┐
                 │rewrite_and_retrieve│ ← 新增: 改写回路
                 │ (LLM 改写query    │
                 │  + 重新检索)       │
                 └────────┬──────────┘
                          │
                          ▼
                     ┌────────┐
                     │retrieve│ ← 回到检索节点
                     └────────┘   (最多3轮)
    """)
    print("节点说明:")
    print("  classify_intent      - LLM Function Calling 意图分类 (6类)")
    print("  check_human          - 高风险场景预判 (退款/投诉/法律)")
    print("  retrieve             - Hybrid Search (BM25+Dense+WeightedRanker)")
    print("  web_search        🆕 - 联网搜索兜底 (智谱优先, Tavily 备选)")
    print("  generate             - 生成 + 幻觉检测自纠正")
    print("  evaluate_quality  🆕 - 质量评估 (忠实度 + 检索质量)")
    print("  human_approval    🆕 - 真正 HITL (interrupt_before)")
    print("  rewrite_and_retrieve 🆕 - 改写回路 (LLM改写→重检索)")
    print("  human                - 高风险直接转人工")
    print("  sql                  - SQL 查询 (预留)")
    print("  direct               - 闲聊直接回复")
    print("  error                - 错误处理")
    print()
    print("  级联检索路径:")
    print("  - 第1级: retrieve (Hybrid) → 有结果 → generate")
    print("  - 第2级: retrieve (Hybrid) → 无结果 → web_search → generate")
    print("  - 第3级: web_search 也无结果 → generate 用兜底回复")
    print("  反馈回路:")
    print("  - Agentic 循环: evaluate → human → rewrite → retrieve → generate")
    print("  - Human-in-the-Loop: LangGraph interrupt_before 真正中断")
    print("  - 最多 3 轮自纠正 (MAX_LOOP_COUNT=3)")
    print("=" * 60)


if __name__ == "__main__":
    print("🚀 LangGraph 流程图生成器")
    print("-" * 40)

    success = generate_graph_image()
    print_graph_structure()

    if success:
        print("\n✅ 完成！图片已保存到 docs/graphs/ 目录")
    else:
        print("\n⚠️  PNG 生成需要安装 graphviz:")
        print("   Windows: choco install graphviz")
        print("   或者用 Mermaid 在线查看: https://mermaid.live")

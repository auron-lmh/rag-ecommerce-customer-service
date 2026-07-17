"""知识库构建平台 — Gradio 管理后台

Tab 1: 上传解析 — 拖拽文件 → 自动解析 → Markdown预览 → 清洗结果
Tab 2: 文档管理 — 已上传文档列表 / 状态 / 成本 / 删除
Tab 3: 知识库概览 — 统计 / 成本 / 文档类型分布

启动: python -m src.admin.gradio_app
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import gradio as gr

from src.ingestion.clean_markdown import clean_markdown
from src.ingestion.models import ParseStatus
from src.ingestion.router import parse_file

# ═══════════════════════════════════════
# 内存中的文档注册表
# ═══════════════════════════════════════


@dataclass
class DocRecord:
    """一条文档记录"""

    id: str
    filename: str
    doc_type: str
    file_size_kb: float
    status: str
    chunks: int
    markdown: str = ""
    preview: str = ""
    api_cost: float = 0.0
    parse_time_ms: float = 0.0
    uploaded_at: str = ""
    errors: list = field(default_factory=list)

    def to_row(self):
        return [
            self.filename,
            self.doc_type,
            f"{self.file_size_kb:.1f} KB",
            self.status,
            str(self.chunks),
            f"¥{self.api_cost:.4f}",
            self.parse_time_ms,
            self.uploaded_at,
        ]


class DocStore:
    """文档注册表（内存）"""

    def __init__(self):
        self.docs: dict[str, DocRecord] = {}
        self._counter = 0

    def add(self, record: DocRecord):
        self.docs[record.id] = record

    def get(self, doc_id: str) -> DocRecord | None:
        return self.docs.get(doc_id)

    def list_all(self) -> list[DocRecord]:
        return sorted(self.docs.values(), key=lambda d: d.uploaded_at, reverse=True)

    def delete(self, doc_id: str):
        self.docs.pop(doc_id, None)

    def stats(self) -> dict:
        docs = self.list_all()
        total_chunks = sum(d.chunks for d in docs)
        total_cost = sum(d.api_cost for d in docs)
        total_size = sum(d.file_size_kb for d in docs)
        return {
            "total_docs": len(docs),
            "total_chunks": total_chunks,
            "total_cost": round(total_cost, 4),
            "total_size_kb": round(total_size, 1),
            "success": sum(1 for d in docs if d.status == "成功"),
            "failed": sum(1 for d in docs if d.status == "失败"),
            "by_type": _count_by(docs, "doc_type"),
        }


store = DocStore()


def _count_by(docs: list[DocRecord], key: str) -> dict:
    counts: dict[str, int] = {}
    for d in docs:
        v = getattr(d, key, "unknown")
        counts[v] = counts.get(v, 0) + 1
    return counts


# ═══════════════════════════════════════
# Tab 1: 上传解析
# ═══════════════════════════════════════


def handle_upload(files: list[str] | None):
    """处理文件上传 → 解析 → 清洗 → 返回预览"""
    if not files:
        return [], "请上传文件", "", _render_stats()

    results = []
    all_preview = []
    summary_lines = []

    for file_path in files:
        if file_path is None:
            continue

        path = Path(file_path)
        filename = path.name
        file_size_kb = path.stat().st_size / 1024

        # 解析
        t0 = time.time()
        result = parse_file(str(path))
        elapsed_ms = round((time.time() - t0) * 1000)

        # 清洗
        chunks = []
        if result.status == ParseStatus.SUCCESS and result.markdown:
            cleaned = clean_markdown(
                result.markdown, filename, result.document.doc_type
            )
            chunks = cleaned

        # 记录
        doc_id = f"doc_{int(time.time() * 1000)}_{filename}"
        record = DocRecord(
            id=doc_id,
            filename=filename,
            doc_type=result.document.doc_type.value,
            file_size_kb=round(file_size_kb, 1),
            status=(
                "成功"
                if result.status == ParseStatus.SUCCESS
                else ("部分成功" if result.status == ParseStatus.PARTIAL else "失败")
            ),
            chunks=len(chunks),
            markdown=result.markdown[:5000] if result.markdown else "",
            preview=result.markdown[:800] if result.markdown else "",
            api_cost=result.api_cost_estimate,
            parse_time_ms=elapsed_ms,
            uploaded_at=datetime.now().strftime("%H:%M:%S"),
            errors=result.errors,
        )
        store.add(record)

        # 构建预览
        status_icon = (
            "✅"
            if record.status == "成功"
            else ("⚠️" if record.status == "部分成功" else "❌")
        )
        summary_lines.append(
            f"{status_icon} **{filename}** | {record.doc_type} | "
            f"{record.chunks} 个chunk | ¥{record.api_cost:.4f} | {elapsed_ms}ms"
        )
        if record.errors:
            for e in record.errors[:3]:
                summary_lines.append(f"  > ⚠️ {e}")

        all_preview.append(f"## 📄 {filename}\n\n")

        if record.markdown:
            all_preview.append(record.markdown[:3000])
        else:
            all_preview.append("*(无内容)*")

        all_preview.append("\n\n---\n")

        # 构建表格行
        results.append(record.to_row())

    return (
        results,
        "\n".join(summary_lines),
        "\n".join(all_preview),
        _render_stats(),
    )


def refresh_preview(doc_choice: str):
    """下拉选择文档 → 显示Markdown预览"""
    if not doc_choice:
        return "", ""

    doc_id = doc_choice.split(" | ")[0] if " | " in doc_choice else doc_choice
    record = store.get(doc_id)
    if record:
        info = (
            f"**文件**: {record.filename}\n"
            f"**类型**: {record.doc_type} | **大小**: {record.file_size_kb:.1f} KB\n"
            f"**状态**: {record.status} | **Chunks**: {record.chunks} | "
            f"**费用**: ¥{record.api_cost:.4f} | **耗时**: {record.parse_time_ms}ms"
        )
        return info, record.markdown[:8000] if record.markdown else "*(无内容)*"
    return "未找到文档", ""


# ═══════════════════════════════════════
# Tab 2: 文档管理
# ═══════════════════════════════════════


def list_docs():
    """列出所有文档"""
    docs = store.list_all()
    if not docs:
        return [["(暂无文档)", "", "", "", "", "", "", ""]]
    return [d.to_row() for d in docs]


def delete_doc(doc_choice: str):
    """删除文档"""
    if not doc_choice:
        return list_docs(), _get_doc_choices(), _render_stats()

    doc_id = doc_choice.split(" | ")[0] if " | " in doc_choice else doc_choice
    store.delete(doc_id)
    return list_docs(), _get_doc_choices(), _render_stats()


def _get_doc_choices() -> list[str]:
    docs = store.list_all()
    return [f"{d.id} | {d.filename} ({d.chunks} chunks)" for d in docs]


# ═══════════════════════════════════════
# Tab 3: 知识库概览
# ═══════════════════════════════════════


def _render_stats() -> str:
    s = store.stats()
    if s["total_docs"] == 0:
        return "### 📊 知识库为空\n\n上传文件开始构建知识库。"

    type_md = "\n".join(f"- **{t}**: {c} 个" for t, c in s["by_type"].items())

    return f"""### 📊 知识库概览

| 指标 | 数值 |
|------|------|
| 📁 文档总数 | {s['total_docs']} |
| ✅ 成功 | {s['success']} |
| ❌ 失败 | {s['failed']} |
| 📝 清洗后Chunk | {s['total_chunks']} |
| 💰 API总费用 | ¥{s['total_cost']:.4f} |
| 💾 文件总大小 | {s['total_size_kb']:.1f} KB |

### 📂 文档类型分布

{type_md}
"""


# ═══════════════════════════════════════
# Gradio UI
# ═══════════════════════════════════════

HEADER = """
# 🏪 电商客服知识库构建平台

上传商品信息、售后政策、FAQ问答对，自动解析为结构化知识。
"""

CSS = """
.gradio-container { max-width: 1200px !important; }
footer { visibility: hidden; }
"""


def create_app() -> gr.Blocks:
    with gr.Blocks(title="知识库构建平台") as app:
        gr.Markdown(HEADER)

        # ── 共享状态栏 ──
        stats_md = gr.Markdown(_render_stats())

        with gr.Tabs():
            # ═══════════════════════════
            # Tab 1: 上传解析
            # ═══════════════════════════
            with gr.Tab("📤 上传解析"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown(
                            "### 选择文件\n支持 PDF / Word / Excel / 图片 / JSON"
                        )
                        upload = gr.File(
                            label="拖拽或点击上传",
                            file_count="multiple",
                            file_types=[
                                ".pdf",
                                ".docx",
                                ".xlsx",
                                ".pptx",
                                ".png",
                                ".jpg",
                                ".jpeg",
                                ".webp",
                                ".json",
                                ".txt",
                                ".md",
                            ],
                        )
                        upload_btn = gr.Button(
                            "🔍 开始解析", variant="primary", size="lg"
                        )

                        gr.Markdown("---")
                        gr.Markdown("### 📋 解析摘要")
                        summary = gr.Markdown("等待上传...")

                    with gr.Column(scale=2):
                        gr.Markdown("### 📝 Markdown预览")
                        preview = gr.Markdown(
                            "选择文件并点击「开始解析」查看预览", label="预览"
                        )

                gr.Markdown("---")
                gr.Markdown("### 📋 本次上传记录")
                result_table = gr.Dataframe(
                    headers=[
                        "文件名",
                        "类型",
                        "大小",
                        "状态",
                        "Chunks",
                        "费用",
                        "耗时ms",
                        "时间",
                    ],
                    label="解析记录",
                    interactive=False,
                )

                upload_btn.click(
                    fn=handle_upload,
                    inputs=[upload],
                    outputs=[result_table, summary, preview, stats_md],
                )

            # ═══════════════════════════
            # Tab 2: 文档管理
            # ═══════════════════════════
            with gr.Tab("📂 文档管理"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 选择文档预览")
                        tab2_doc_selector = gr.Dropdown(
                            label="已上传文档",
                            choices=_get_doc_choices(),
                            interactive=True,
                        )
                        doc_info = gr.Markdown("选择一个文档查看详情")

                        with gr.Row():
                            refresh_btn = gr.Button("🔄 刷新预览", variant="secondary")
                            delete_btn = gr.Button("🗑️ 删除文档", variant="stop")

                    with gr.Column(scale=2):
                        doc_preview = gr.Markdown(
                            "### 📝 文档内容\n\n选择一个文档查看Markdown内容",
                            label="文档内容",
                        )

                gr.Markdown("---")
                gr.Markdown("### 📋 全部文档")
                doc_list = gr.Dataframe(
                    headers=[
                        "文件名",
                        "类型",
                        "大小",
                        "状态",
                        "Chunks",
                        "费用",
                        "耗时ms",
                        "时间",
                    ],
                    label="文档列表",
                    interactive=False,
                    value=list_docs(),
                )

                refresh_table_btn = gr.Button("🔄 刷新列表", variant="secondary")

                refresh_btn.click(
                    fn=refresh_preview,
                    inputs=[tab2_doc_selector],
                    outputs=[doc_info, doc_preview],
                )
                delete_btn.click(
                    fn=delete_doc,
                    inputs=[tab2_doc_selector],
                    outputs=[doc_list, tab2_doc_selector, stats_md],
                )
                refresh_table_btn.click(
                    fn=list_docs,
                    inputs=[],
                    outputs=[doc_list],
                )

            # ═══════════════════════════
            # Tab 3: 知识库概览
            # ═══════════════════════════
            with gr.Tab("📊 知识库概览"):
                stats_md_tab = gr.Markdown(_render_stats())
                refresh_stats_btn = gr.Button("🔄 刷新统计", variant="secondary")
                refresh_stats_btn.click(
                    fn=lambda: _render_stats(), outputs=[stats_md_tab]
                )

    return app


def main():
    app = create_app()
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
        theme=gr.themes.Soft(),
        css=CSS,
    )


if __name__ == "__main__":
    main()

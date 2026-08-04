"""知识库入库平台

支持的文档类型 (电商场景):
  PDF    — 售后政策、操作手册、产品说明书
  Word   — 合同条款、培训资料
  Excel  — 商品目录、价目表、规格表
  PPT    — 培训课件、产品推介
  图片   — 商品图片 (VLM生成文字描述)
  JSON   — FAQ问答对
  网页   — 竞品信息、行业政策抓取
  TXT/MD — 纯文本知识

流程: 批量上传 → 逐个解析 → 预览小窗口 → 存入Milvus（单个/批量）
优化 (2026-08):
  - 支持多文件批量上传
  - 预览固定高度可滚动小窗口（不用拉到底部才能点入库）
  - 入库成功/失败状态清晰展示

启动: python -m src.admin.gradio_app
"""

import logging
import time
from pathlib import Path
from typing import Optional

import gradio as gr

from src.ingestion.models import DocType, ParseStatus
from src.ingestion.router import parse_file

logger = logging.getLogger(__name__)

SUPPORTED_TYPES = {
    "pdf": "售后政策/操作手册/产品说明书",
    "word": "合同条款/培训资料",
    "excel": "商品目录/价目表/规格表",
    "ppt": "培训课件/产品推介",
    "image": "商品图片/截图",
    "faq_json": "FAQ问答对",
    "web": "网页抓取",
    "plain_text": "纯文本知识",
}


def _get_filename(path: str, with_ext: bool = True) -> str:
    p = Path(path)
    return p.name if with_ext else p.stem


# ═══════════════════════════════════════


class ProcessorApp:

    def __init__(self):
        self.current_file: Optional[str] = None  # 当前选中的文件名
        self.parsed_docs: dict[str, dict] = {}  # basename -> {markdown, doc_type}

    # ── 预览 HTML：固定高度可滚动小窗口 ──

    def _wrap_preview(self, markdown: str) -> str:
        """Markdown → HTML，包成固定高度可滚动容器（预览小窗口）"""
        import re

        html = re.sub(
            r"!\[([^\]]*)\]\(data:([^)]+)\)",
            r'<img src="data:\2" style="max-width:100%">',
            markdown or "",
        )
        html = re.sub(r"^#### (.+)$", r"<h4>\1</h4>", html, flags=re.MULTILINE)
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
        html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
        html = html.replace("\n\n", "<br><br>")
        return (
            f'<div style="font-family:sans-serif;line-height:1.8;'
            f"max-height:420px;overflow:auto;border:1px solid #ddd;"
            f'padding:10px;border-radius:6px;background:#fafafa;">{html}</div>'
        )

    # ── 批量上传 + 解析 ──

    def upload_and_parse(self, files):
        """批量上传 → 逐个解析 → 预览"""
        if not files:
            return [
                "请上传文件",
                gr.Dropdown(choices=[], interactive=False),
                "",
                gr.Button(interactive=False),
            ]

        file_list = files if isinstance(files, list) else [files]
        file_list = [f for f in file_list if f is not None]
        if not file_list:
            return [
                "请上传文件",
                gr.Dropdown(choices=[], interactive=False),
                "",
                gr.Button(interactive=False),
            ]

        self.parsed_docs = {}
        errors = []
        for file in file_list:
            file_path = file if isinstance(file, str) else file.name
            basename = Path(file_path).name
            try:
                result = parse_file(file_path)
                if (
                    result.status in (ParseStatus.SUCCESS, ParseStatus.PARTIAL)
                    and (result.markdown or "").strip()
                ):
                    self.parsed_docs[basename] = {
                        "markdown": result.markdown,
                        "doc_type": (
                            result.document.doc_type.value
                            if result.document
                            else "plain_text"
                        ),
                    }
                else:
                    err = result.errors[0] if result.errors else "解析结果为空"
                    errors.append(f"{basename}: {err}")
            except Exception as e:
                errors.append(f"{basename}: {e}")

        ok_count = len(self.parsed_docs)
        names = list(self.parsed_docs.keys())
        self.current_file = names[0] if names else None

        status_msg = f"✅ 解析成功 {ok_count}/{len(file_list)} 个文件"
        if errors:
            status_msg += f"  ❌ 失败: {'; '.join(errors[:3])}"
        if not names:
            return [
                status_msg,
                gr.Dropdown(choices=[], interactive=False),
                "",
                gr.Button(interactive=False),
            ]

        current = self.parsed_docs[self.current_file]
        return [
            status_msg,
            gr.Dropdown(choices=names, label="选择文件预览", interactive=True),
            self._wrap_preview(current["markdown"]),
            gr.Button(interactive=True),
        ]

    # ── 切换预览文件 ──

    def select_file(self, name: str):
        self.current_file = name
        if name and name in self.parsed_docs:
            return self._wrap_preview(self.parsed_docs[name]["markdown"])
        return "选择文件查看内容"

    # ── 存入 Milvus ──

    def _save_one(self, basename: str) -> str:
        """单个文件入库，返回清晰状态"""
        info = self.parsed_docs.get(basename)
        if not info:
            return f"❌ 未找到文件 {basename}"
        t0 = time.time()
        try:
            from src.embedding.pipeline import IndexingPipeline
            from src.ingestion.models import DocType

            pipeline = IndexingPipeline()
            store = pipeline.store

            deleted = store.delete_by_source(basename)
            dedup = f"（清除旧数据 {deleted} 条）" if deleted > 0 else ""

            try:
                doc_type = DocType(info["doc_type"])
            except ValueError:
                doc_type = DocType.PLAIN_TEXT

            report = pipeline.run_from_text(info["markdown"], basename, doc_type)
            elapsed = time.time() - t0
            inserted = report.get("inserted", 0)
            st = report.get("status", "unknown")

            if st == "ok":
                return (
                    f"✅ {dedup}入库成功: {basename} → {inserted} 向量 ({elapsed:.0f}s)"
                )
            if st == "partial":
                return f"⚠️ 部分入库: {basename} → {inserted} 向量, 错误: {report.get('errors', [])}"
            return f"❌ 入库失败: {basename}: {report.get('error', '未知')}"
        except Exception as e:
            return f"❌ 入库异常: {basename}: {e}"

    def save_to_milvus(self) -> str:
        """存入当前选中文件"""
        if not self.current_file or self.current_file not in self.parsed_docs:
            return "❌ 请先上传文件"
        return self._save_one(self.current_file)

    def save_all_to_milvus(self) -> str:
        """批量入库全部已解析文件"""
        if not self.parsed_docs:
            return "❌ 没有可入库的文件，请先上传"
        results = [self._save_one(name) for name in self.parsed_docs]
        ok = sum(1 for r in results if r.startswith("✅"))
        summary = f"📦 批量入库完成: {ok}/{len(results)} 成功"
        return summary + "\n\n" + "\n\n".join(results)

    # ── UI ──

    def create_interface(self):
        with gr.Blocks(title="知识库入库平台") as app:
            gr.Markdown("""## 📥 电商客服知识库 · 入库平台

支持所有电商场景文档: **PDF**(售后政策/手册) **Word**(合同/培训) **Excel**(商品目录/价目表) **PPT**(课件) **图片**(商品图→文字描述) **JSON**(FAQ问答对) **网页**(竞品抓取) **TXT/MD**(纯文本)

支持**批量上传**，预览为固定高度小窗口，入库状态实时显示。
            """)

            # 上传（多选）
            upload = gr.File(
                label="上传文件（可多选，拖拽或点击）",
                file_count="multiple",
                file_types=[
                    ".pdf",
                    ".docx",
                    ".doc",
                    ".xlsx",
                    ".xls",
                    ".pptx",
                    ".ppt",
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".webp",
                    ".gif",
                    ".bmp",
                    ".json",
                    ".txt",
                    ".md",
                ],
            )

            status = gr.Textbox(label="解析状态", interactive=False)

            # 文件选择 + 预览小窗口
            with gr.Row():
                file_dropdown = gr.Dropdown(
                    choices=[], label="选择文件预览", interactive=False, scale=1
                )
                content = gr.HTML(label="文件内容预览（小窗口）", scale=3)

            # 入库操作（与预览并排，不用拉到底）
            with gr.Row():
                save_btn = gr.Button(
                    "🚀 存入当前文件", variant="primary", interactive=False
                )
                save_all_btn = gr.Button(
                    "📦 批量全部入库", variant="secondary", interactive=False
                )
                save_result = gr.Textbox(label="入库结果", interactive=False, scale=2)

            # ── 事件 ──
            upload.change(
                fn=self.upload_and_parse,
                inputs=upload,
                outputs=[status, file_dropdown, content, save_btn],
            )
            file_dropdown.change(
                fn=self.select_file,
                inputs=file_dropdown,
                outputs=content,
            )
            save_btn.click(
                fn=self.save_to_milvus,
                inputs=[],
                outputs=save_result,
            )
            save_all_btn.click(
                fn=self.save_all_to_milvus,
                inputs=[],
                outputs=save_result,
            )

        return app


def main():
    app = ProcessorApp()
    app.create_interface().launch(server_name="0.0.0.0", server_port=7860)


if __name__ == "__main__":
    main()

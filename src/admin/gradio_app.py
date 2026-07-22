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

流程: 上传文件 → 解析预览 → 存入Milvus

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

BASE_OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "processed"

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


def _split_and_save(
    markdown: str, save_dir: Path, basename: str, doc_type: str
) -> list[str]:
    """按文档类型拆分并保存，返回文件名列表

    不同格式拆分规则不同:
      PDF/PPT → 按 "## 第N页" 拆分
      Excel   → 按 "## Sheet名" 拆分
      FAQ     → 按 "## QN:" 拆分
      其他    → 单文件
    """
    save_dir.mkdir(parents=True, exist_ok=True)

    if doc_type in ("pdf", "ppt"):
        # 按页拆分
        parts = markdown.split("## 第")
        if len(parts) <= 1:
            (save_dir / f"{basename}.md").write_text(markdown, encoding="utf-8")
            return [f"{basename}.md"]
        files = []
        for i, part in enumerate(parts):
            if i == 0:
                if part.strip():
                    (save_dir / f"{basename}_page_0.md").write_text(
                        part.strip(), encoding="utf-8"
                    )
                    files.append(f"{basename}_page_0.md")
                continue
            filename = f"{basename}_page_{i}.md"
            (save_dir / filename).write_text(f"## 第{part.strip()}", encoding="utf-8")
            files.append(filename)
        return files

    elif doc_type == "excel":
        # 按 Sheet 拆分
        parts = markdown.split("## ")
        if len(parts) <= 1:
            (save_dir / f"{basename}.md").write_text(markdown, encoding="utf-8")
            return [f"{basename}.md"]
        files = []
        for part in parts:
            if not part.strip():
                continue
            sheet_name = part.split("\n")[0].strip()
            safe_name = sheet_name.replace("/", "_").replace("\\", "_")
            filename = f"{basename}_{safe_name}.md"
            (save_dir / filename).write_text(f"## {part.strip()}", encoding="utf-8")
            files.append(filename)
        return files

    elif doc_type == "faq_json":
        # Q&A 列表，不拆分 (预览整体结构即可)
        (save_dir / f"{basename}.md").write_text(markdown, encoding="utf-8")
        return [f"{basename}.md"]

    else:
        # Word / Image / Web / TXT → 单文件
        (save_dir / f"{basename}.md").write_text(markdown, encoding="utf-8")
        return [f"{basename}.md"]


# ═══════════════════════════════════════


class ProcessorApp:

    def __init__(self):
        self.current_file: Optional[str] = None
        self.current_markdown: str = ""
        self.current_doc_type: str = ""
        self.preview_dir: Optional[Path] = None
        self.preview_files: list[Path] = []
        self.file_contents: dict[str, str] = {}

    # ── 上传 + 解析 (合并为一步, 上传即解析) ──

    def upload_and_parse(self, file):
        """上传文件 → 自动解析 → 预览"""
        if file is None:
            return [
                "请上传文件",
                gr.Dropdown(choices=[], interactive=False),
                "",
                "",
                gr.Button(interactive=False),
            ]

        file_path = file if isinstance(file, str) else file.name
        self.current_file = file_path
        basename = Path(file_path).name
        ext = Path(file_path).suffix.lower()

        # 显示文件类型说明
        type_hint = ""
        for key, hint in SUPPORTED_TYPES.items():
            if key in ext or (
                ext in (".jpg", ".jpeg", ".png", ".gif", ".webp") and key == "image"
            ):
                type_hint = hint
                break
        if not type_hint and file_path.startswith("http"):
            type_hint = SUPPORTED_TYPES["web"]

        # ── 解析 ──
        t0 = time.time()
        try:
            result = parse_file(file_path)
            elapsed = time.time() - t0

            if result.status == ParseStatus.FAILED:
                error = result.errors[0] if result.errors else "未知错误"
                return [
                    f"❌ 解析失败: {error}",
                    gr.Dropdown(choices=[], interactive=False),
                    "",
                    f"{type_hint} | {elapsed:.0f}s | ❌",
                    gr.Button(interactive=False),
                ]

            markdown = result.markdown or ""
            if not markdown.strip():
                return [
                    "⚠️ 解析结果为空",
                    gr.Dropdown(choices=[], interactive=False),
                    "",
                    f"{type_hint} | {elapsed:.0f}s | ⚠️",
                    gr.Button(interactive=False),
                ]

            self.current_markdown = markdown
            self.current_doc_type = (
                result.document.doc_type.value if result.document else "unknown"
            )

            # 按文档类型拆分 + 保存 MD
            stem = Path(file_path).stem
            preview_dir = BASE_OUTPUT_DIR / stem
            file_names = _split_and_save(
                markdown, preview_dir, stem, self.current_doc_type
            )

            # PDF/PPT: 同时收集 .jpg 页面原图 (拷贝到预览目录)
            if self.current_doc_type in ("pdf", "ppt"):
                jpg_dir = Path(file_path).parent / f"{stem}_pages"
                if jpg_dir.exists():
                    import shutil

                    for jpg in sorted(jpg_dir.glob("page_*.jpg")):
                        dest = preview_dir / jpg.name
                        shutil.copy2(jpg, dest)
                        file_names.append(jpg.name)

            self.preview_dir = preview_dir
            self.preview_files = [preview_dir / fn for fn in file_names]
            self.file_contents = {}
            for f in self.preview_files:
                try:
                    if f.suffix == ".jpg":
                        # 图片文件不读取内容，渲染时特殊处理
                        self.file_contents[f.name] = f"![{f.name}]({f.name})"
                    else:
                        self.file_contents[f.name] = f.read_text(encoding="utf-8")
                except Exception as e:
                    self.file_contents[f.name] = f"读取出错: {e}"

            # 统计（按格式给不同标签）
            unit = {"pdf": "页", "ppt": "页", "excel": "Sheet", "faq_json": "条QA"}
            unit_name = unit.get(self.current_doc_type, "段")
            item_count = len(self.preview_files)
            char_count = len(markdown)
            cost = result.api_cost_estimate

            info_line = f"{type_hint} | {item_count}{unit_name} | {char_count}字 | ¥{cost:.4f} | {elapsed:.0f}s | ✅"

            # 下拉框标签按格式区分
            dropdown_label = {
                "pdf": "预览页面",
                "ppt": "预览幻灯片",
                "excel": "预览Sheet",
                "faq_json": "预览内容",
            }.get(self.current_doc_type, "预览文件")

            # 首页预览 (转HTML)
            first_html = ""
            if file_names:
                raw = self.file_contents.get(file_names[0], "")
                import re

                html = re.sub(
                    r"!\[([^\]]*)\]\(data:([^)]+)\)",
                    r'<img src="data:\2" style="max-width:100%">',
                    raw,
                )
                html = html.replace("\n\n", "<br><br>")
                first_html = (
                    f'<div style="font-family:sans-serif;line-height:1.8;">{html}</div>'
                )

            return [
                f"✅ {basename} 解析完成",
                gr.Dropdown(choices=file_names, label=dropdown_label, interactive=True),
                first_html,
                info_line,
                gr.Button(interactive=True),
            ]

        except Exception as e:
            logger.exception("解析异常")
            return [
                f"❌ 解析异常: {e}",
                gr.Dropdown(choices=[], interactive=False),
                "",
                f"❌ {e}",
                gr.Button(interactive=False),
            ]

    # ── 预览：选择文件 ──

    def select_file(self, selected: str):
        if selected and selected in self.file_contents:
            raw = self.file_contents[selected]
            # 将 Markdown 转为 HTML (Gradio HTML 组件支持 data URI 图片)
            import re

            # 图片: ![...](data:...) → <img src="data:...">
            html = re.sub(
                r"!\[([^\]]*)\]\(data:([^)]+)\)",
                r'<img src="data:\2" style="max-width:100%">',
                raw,
            )
            # 标题: # → <h1>, ## → <h2>
            html = re.sub(r"^#### (.+)$", r"<h4>\1</h4>", html, flags=re.MULTILINE)
            html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
            html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
            html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
            # 粗体
            html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
            # 换行
            html = html.replace("\n\n", "<br><br>")
            return (
                f'<div style="font-family: sans-serif; line-height:1.8;">{html}</div>'
            )
        return "选择文件查看内容"

    # ── 存入Milvus ──

    def save_to_milvus(self):
        if not self.current_markdown:
            return "❌ 没有可入库的内容，请先上传文件"

        t0 = time.time()
        try:
            from src.chunking.router import chunk_document
            from src.embedding.milvus_store import MilvusStore
            from src.embedding.pipeline import IndexingPipeline
            from src.ingestion.models import DocType

            pipeline = IndexingPipeline()
            store = pipeline.store
            basename = _get_filename(self.current_file, with_ext=True)

            # ── 去重: 检查是否已入库, 有则先删 ──
            deleted_count = store.delete_by_source(basename)
            dedup_msg = (
                f"(已清除旧数据 {deleted_count} 条) " if deleted_count > 0 else ""
            )

            try:
                doc_type = DocType(self.current_doc_type)
            except ValueError:
                doc_type = DocType.PLAIN_TEXT

            report = pipeline.run_from_text(self.current_markdown, basename, doc_type)

            elapsed = time.time() - t0
            inserted = report.get("inserted", 0)
            status = report.get("status", "unknown")

            if status == "ok":
                return f"✅ {dedup_msg}已入库: {inserted} 个向量, 耗时 {elapsed:.0f}s"
            elif status == "partial":
                return f"⚠️ {dedup_msg}部分入库: {inserted} 个向量, 错误: {report.get('errors', [])}"
            else:
                return f"❌ 入库失败: {report.get('error', '未知')}"
        except Exception as e:
            return f"❌ 入库异常: {e}"

    # ── UI ──

    def create_interface(self):
        with gr.Blocks(title="知识库入库平台") as app:
            gr.Markdown("""## 📥 电商客服知识库 · 入库平台

支持所有电商场景文档: **PDF**(售后政策/手册) **Word**(合同/培训) **Excel**(商品目录/价目表) **PPT**(课件) **图片**(商品图→文字描述) **JSON**(FAQ问答对) **网页**(竞品抓取) **TXT/MD**(纯文本)
            """)

            with gr.Row():
                upload = gr.File(
                    label="上传文件 (拖拽或点击)",
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

            status = gr.Textbox(label="状态", value="等待上传...", interactive=False)

            with gr.Row():
                file_dropdown = gr.Dropdown(
                    choices=[],
                    label="预览文件 (选择查看不同页面)",
                    interactive=False,
                )
                content = gr.HTML(label="文件内容")

            info_line = gr.Textbox(label="文件信息", interactive=False)

            save_btn = gr.Button("🚀 存入知识库", variant="primary", interactive=False)
            save_result = gr.Textbox(label="入库结果", interactive=False)

            # ── 事件 ──
            upload.change(
                fn=self.upload_and_parse,
                inputs=upload,
                outputs=[status, file_dropdown, content, info_line, save_btn],
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

        return app


def main():
    app = ProcessorApp()
    app.create_interface().launch(server_name="0.0.0.0", server_port=7860)


if __name__ == "__main__":
    main()

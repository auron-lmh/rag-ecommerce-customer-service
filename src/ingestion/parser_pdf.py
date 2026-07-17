"""PDF解析器 — 阿里云百炼 qwen-vl-ocr + PyMuPDF图片提取 + 质量评估

防御层次:
  1. 文件预检 (validate_file) — 大小/MIME/可读性
  2. 逐页质量评估 (assess_pdf_quality) — 文本量/图片数/是否扫描
  3. 嵌入式图片提取 (extract_pdf_images) — 保存到 data/images/
  4. API提交+轮询 — 双路径(base64/multipart)，指数退避重试
  5. 结果质量校验 — 空内容检测，逐页状态记录
"""

import base64
import time
from pathlib import Path

import requests

from src.config import settings

from .defenses import (
    assess_pdf_quality,
    extract_pdf_images,
    inject_placeholders_into_markdown,
    retry_with_backoff,
    validate_file,
)
from .models import ParseResult, ParseStatus, RawDocument


def parse_pdf_bailian(doc: RawDocument) -> ParseResult:
    """PDF → 百炼API解析 → Markdown + 图片提取 + 质量报告"""
    t0 = time.time()
    result = ParseResult(document=doc, status=ParseStatus.SUCCESS)

    # ═══════════════════════════════════════
    # 第1层：文件预检
    # ═══════════════════════════════════════
    validation = validate_file(doc.file_path, "pdf")
    result.file_validation = validation

    if not validation.is_valid:
        result.status = ParseStatus.FAILED
        result.errors.extend(validation.errors)
        result.parse_time_ms = (time.time() - t0) * 1000
        return result
    if validation.warnings:
        result.warnings.extend(validation.warnings)

    # ═══════════════════════════════════════
    # 第2层：逐页质量评估
    # ═══════════════════════════════════════
    page_qualities = assess_pdf_quality(doc.file_path)
    result.page_qualities = page_qualities

    scanned_pages = [p for p in page_qualities if p.is_scanned]
    poor_pages = [p for p in page_qualities if p.quality_label == "poor"]

    if scanned_pages:
        result.is_scanned = True
        result.warnings.append(
            f"检测到 {len(scanned_pages)} 页扫描件（第"
            f"{','.join(str(p.page_num) for p in scanned_pages[:5])}"
            f"{'...' if len(scanned_pages) > 5 else ''}页），将调用OCR"
        )
    if poor_pages:
        result.warnings.append(f"检测到 {len(poor_pages)} 页质量较差（内容极少或空白）")

    # ═══════════════════════════════════════
    # 第3层：提取PDF中嵌入的图片 + 位置信息
    # ═══════════════════════════════════════
    try:
        extracted_images, page_placeholders = extract_pdf_images(
            doc.file_path, enhance=True
        )
        result.extracted_images = extracted_images

        if extracted_images:
            blurry_imgs = [
                e for e in extracted_images if e.quality and e.quality.is_blurry
            ]
            if blurry_imgs:
                result.warnings.append(
                    f"PDF中 {len(blurry_imgs)}/{len(extracted_images)} 张图片清晰度较低，"
                    "已自动锐化处理"
                )
    except Exception as e:
        result.warnings.append(f"图片提取失败（不阻塞文本解析）: {e}")
        extracted_images = []
        page_placeholders = {}

    # ═══════════════════════════════════════
    # 第4层：API调用（带重试）
    # ═══════════════════════════════════════
    api_key = settings.bailian_api_key
    if not api_key:
        result.status = ParseStatus.FAILED
        result.errors.append("缺少 BAILIAN_API_KEY，请检查 .env 配置")
        result.parse_time_ms = (time.time() - t0) * 1000
        return result

    # 带指数退避的API调用
    markdown_text, api_error = retry_with_backoff(
        lambda: _call_bailian_parse(doc.file_path, api_key),
        max_retries=3,
        base_delay=2.0,
        max_delay=15.0,
    )

    if api_error:
        result.status = ParseStatus.FAILED
        result.errors.append(_format_api_error(api_error))
        result.parse_time_ms = (time.time() - t0) * 1000
        return result

    if not markdown_text or len(markdown_text.strip()) < 20:
        result.status = ParseStatus.PARTIAL
        result.warnings.append(
            "PDF解析结果为空或内容极少（可能为空白页或扫描质量过差）"
        )
        result.markdown = markdown_text or ""
        result.total_pages = len(page_qualities)
        result.parsed_pages = 0
        result.parse_time_ms = (time.time() - t0) * 1000
        return result

    # ═══════════════════════════════════════
    # 第5层：组装结果 — 图片占位符注入Markdown原文
    # ═══════════════════════════════════════
    if page_placeholders:
        result.markdown = inject_placeholders_into_markdown(
            markdown_text, page_placeholders, page_qualities
        )
    else:
        result.markdown = markdown_text
    result.total_pages = len(page_qualities)
    result.parsed_pages = sum(1 for p in page_qualities if p.has_text or p.is_scanned)
    result.api_calls = 1
    result.api_cost_estimate = sum(
        0.01 if p.is_scanned else 0.0 for p in page_qualities
    )
    result.parse_time_ms = (time.time() - t0) * 1000

    # 成功率告警
    if result.parsed_pages < result.total_pages * 0.5 and result.total_pages > 2:
        result.warnings.append(
            f"仅成功解析 {result.parsed_pages}/{result.total_pages} 页（成功率 < 50%），"
            "建议检查PDF质量"
        )

    return result


def _call_bailian_parse(file_path: str, api_key: str) -> str:
    """调用百炼文档解析API → 返回Markdown文本

    双路径:
      路径1: multipart/form-data 文件上传（主方案）
      路径2: base64编码内联（备选，部分网络环境multipart受限）
    """
    path = Path(file_path)

    # 路径1：multipart上传
    try:
        with open(path, "rb") as f:
            file_content = f.read()

        resp = requests.post(
            "https://dashscope.aliyuncs.com/api/v1/services/fileparser/parse",
            headers={"Authorization": f"Bearer {api_key}"},
            files={
                "file": (path.name, file_content, "application/pdf"),
            },
            data={
                "parameters": '{"max_pages": 50, "ocr_enabled": true, "output_format": "markdown"}',
            },
            timeout=settings.doc_parse_timeout,
        )
        resp.raise_for_status()
        body = resp.json()

        task_id = body.get("task_id") or body.get("id")
        if not task_id:
            raise RuntimeError(f"百炼API未返回task_id: {body}")

        # 轮询结果
        markdown = _poll_bailian_task(task_id, api_key)
        if markdown:
            return markdown
    except Exception:
        # 路径1失败→降级到路径2
        pass

    # 路径2：base64内联（备选）
    with open(path, "rb") as f:
        b64_content = base64.b64encode(f.read()).decode()

    resp = requests.post(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "qwen-vl-ocr-latest",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:application/pdf;base64,{b64_content}"
                            },
                        },
                        {
                            "type": "text",
                            "text": "请提取此文档的全部文字内容，保留标题层级和表格结构，输出Markdown格式。",
                        },
                    ],
                }
            ],
            "max_tokens": 16384,
        },
        timeout=settings.doc_parse_timeout,
    )
    resp.raise_for_status()
    body = resp.json()
    return body["choices"][0]["message"]["content"]


def _poll_bailian_task(task_id: str, api_key: str, max_retries: int = 15) -> str:
    """轮询百炼异步解析任务 → 返回Markdown"""
    for i in range(max_retries):
        time.sleep(2)

        resp = requests.get(
            f"https://dashscope.aliyuncs.com/api/v1/services/fileparser/parse/{task_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()

        status = body.get("status") or body.get("task_status", "")

        if status in ("SUCCESS", "success", "SUCCEEDED", "completed"):
            output = body.get("output", {})
            markdown = (
                output.get("text")
                or output.get("markdown")
                or output.get("content", "")
            )
            if not markdown and "data" in body:
                data = body["data"]
                markdown = data.get("text") or data.get("markdown", "")
            return markdown

        if status in ("FAILED", "failed", "ERROR", "error"):
            raise RuntimeError(
                f"百炼解析任务失败: {body.get('message', body.get('error', 'unknown'))}"
            )

    raise TimeoutError(f"百炼解析任务超时（等待{max_retries * 2}秒未完成）")


def _format_api_error(error: Exception) -> str:
    """将API异常转为用户可读的错误信息"""
    msg = str(error)
    if "429" in msg:
        return "API请求过于频繁（429限流），请稍后再试"
    if "401" in msg or "403" in msg:
        return "百炼API Key无效或已过期，请检查 BAILIAN_API_KEY"
    if "timeout" in msg.lower() or "Timeout" in msg:
        return f"百炼API响应超时（{settings.doc_parse_timeout}秒），PDF可能过大或网络不稳定"
    if "connection" in msg.lower():
        return "无法连接百炼API，请检查网络连接"
    return f"百炼API调用失败: {msg[:200]}"

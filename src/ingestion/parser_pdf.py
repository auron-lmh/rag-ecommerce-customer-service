"""PDF解析器 — 完整照搬 RAG 项目 dots_ocr/parser.py 的架构

流程 (与 RAG 项目完全一致):
  1. load_images_from_pdf → 逐页渲染为 PIL Image 列表
  2. 构建 tasks 列表
  3. ThreadPool.imap_unordered → 每页: fetch_image → smart_resize → API → 返回结果
  4. tqdm 实时显示进度
  5. 按 page_no 排序合并

API: 千问 qwen3.7-plus (OpenAI 兼容格式) 替代已下线 qwen-vl-max
图片传递: PIL Image (各函数间) → base64 (仅 API 调用前)
"""

import base64
import json as _json_mod
import logging
import math
import sys
import time
from io import BytesIO
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Optional

import fitz
import requests
from PIL import Image

from src.config import settings

from .defenses import validate_file
from .layout_parser import LAYOUT_PROMPT, _clean_model_output, _layoutjson2md
from .models import ParseResult, ParseStatus, RawDocument

_log = logging.getLogger(__name__)

# ═══════════════════════════════════════
# 常量 (与 dots_ocr/utils/consts.py 一致)
# ═══════════════════════════════════════
MIN_PIXELS = 3136
MAX_PIXELS = 11289600
IMAGE_FACTOR = 28
NUM_THREAD = 8  # API 并发线程数
PDF_DPI = 200  # PDF 渲染 DPI

# OCR Prompt — 结构化 Layout JSON (参考 dots_ocr prompt_layout_all_en)
# ═══════════════════════════════════════
# 主入口
# ═══════════════════════════════════════


def parse_pdf_bailian(doc: RawDocument) -> ParseResult:
    """PDF → 逐页并发 OCR → Markdown"""
    t0 = time.time()
    result = ParseResult(document=doc, status=ParseStatus.SUCCESS)

    validation = validate_file(doc.file_path, "pdf")
    result.file_validation = validation
    if not validation.is_valid:
        result.status = ParseStatus.FAILED
        result.errors.extend(validation.errors)
        result.parse_time_ms = (time.time() - t0) * 1000
        return result

    api_key = settings.bailian_api_key
    if not api_key:
        result.status = ParseStatus.FAILED
        result.errors.append("缺少 BAILIAN_API_KEY")
        result.parse_time_ms = (time.time() - t0) * 1000
        return result

    try:
        markdown_text, page_count, cost = _parse_pdf(doc.file_path, api_key)
        result.markdown = markdown_text
        result.total_pages = page_count
        result.parsed_pages = page_count
        result.api_calls = page_count
        result.api_cost_estimate = cost
    except Exception as e:
        _log.exception("PDF 解析失败")
        result.status = ParseStatus.FAILED
        result.errors.append(f"PDF解析失败: {e}")
        result.parse_time_ms = (time.time() - t0) * 1000
        return result

    if not markdown_text or len(markdown_text.strip()) < 20:
        result.status = ParseStatus.PARTIAL
        result.warnings.append("PDF解析结果为空或内容极少")

    result.parse_time_ms = (time.time() - t0) * 1000
    return result


# ═══════════════════════════════════════
# 图片工具 (与 dots_ocr/utils/image_utils.py 一致)
# ═══════════════════════════════════════


def _round_by_factor(n: int, factor: int) -> int:
    return round(n / factor) * factor


def _floor_by_factor(n: int, factor: int) -> int:
    return math.floor(n / factor) * factor


def _ceil_by_factor(n: int, factor: int) -> int:
    return math.ceil(n / factor) * factor


def _smart_resize(height: int, width: int) -> tuple[int, int]:
    """与 dots_ocr smart_resize 完全一致"""
    h_bar = max(IMAGE_FACTOR, _round_by_factor(height, IMAGE_FACTOR))
    w_bar = max(IMAGE_FACTOR, _round_by_factor(width, IMAGE_FACTOR))
    if h_bar * w_bar > MAX_PIXELS:
        beta = math.sqrt((height * width) / MAX_PIXELS)
        h_bar = max(IMAGE_FACTOR, _floor_by_factor(height / beta, IMAGE_FACTOR))
        w_bar = max(IMAGE_FACTOR, _floor_by_factor(width / beta, IMAGE_FACTOR))
    elif h_bar * w_bar < MIN_PIXELS:
        beta = math.sqrt(MIN_PIXELS / (height * width))
        h_bar = _ceil_by_factor(height * beta, IMAGE_FACTOR)
        w_bar = _ceil_by_factor(width * beta, IMAGE_FACTOR)
        if h_bar * w_bar > MAX_PIXELS:
            beta = math.sqrt((h_bar * w_bar) / MAX_PIXELS)
            h_bar = max(IMAGE_FACTOR, _floor_by_factor(h_bar / beta, IMAGE_FACTOR))
            w_bar = max(IMAGE_FACTOR, _floor_by_factor(w_bar / beta, IMAGE_FACTOR))
    return h_bar, w_bar


def _fetch_image(image: Image.Image) -> Image.Image:
    """与 dots_ocr fetch_image 一致: 转RGB + smart_resize"""
    if image.mode != "RGB":
        image = image.convert("RGB")
    w, h = image.size
    new_h, new_w = _smart_resize(h, w)
    if (new_w, new_h) != (w, h):
        image = image.resize((new_w, new_h), Image.LANCZOS)
    return image


def _image_to_base64(image: Image.Image) -> str:
    """与 dots_ocr image_to_base64 一致: PIL → JPEG → base64"""
    if image.mode != "RGB":
        image = image.convert("RGB")
    buf = BytesIO()
    image.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ═══════════════════════════════════════
# PDF 渲染 (与 dots_ocr/doc_utils.py 一致)
# ═══════════════════════════════════════


def _fitz_doc_to_image(page, target_dpi: int = 200) -> Image.Image:
    """与 dots_ocr fitz_doc_to_image 一致"""
    mat = fitz.Matrix(target_dpi / 72, target_dpi / 72)
    pm = page.get_pixmap(matrix=mat, alpha=False)
    if pm.width > 4500 or pm.height > 4500:
        mat = fitz.Matrix(1, 1)
        pm = page.get_pixmap(matrix=mat, alpha=False)
    return Image.frombytes("RGB", (pm.width, pm.height), pm.samples)


def _load_images_from_pdf(pdf_path: str, dpi: int = 200) -> list[Image.Image]:
    """与 dots_ocr load_images_from_pdf 一致"""
    images = []
    with fitz.open(pdf_path) as doc:
        for index in range(doc.page_count):
            img = _fitz_doc_to_image(doc[index], target_dpi=dpi)
            images.append(img)
    return images


# ═══════════════════════════════════════
# 核心: 与 ZhipuOCRParser 同款架构
# ═══════════════════════════════════════


def _parse_pdf(file_path: str, api_key: str):
    """完整照搬 ZhipuOCRParser.parse_pdf 的架构

    与源码的区别: _inference_with_zhipu → _inference_with_qwen (API 换成千问)
    """
    # ── 步骤1: 渲染所有页面为 PIL Image (与 load_images_from_pdf 一致) ──
    print(f"[PDF OCR] 正在加载 PDF: {file_path}")
    images_origin = _load_images_from_pdf(file_path, dpi=PDF_DPI)
    total_pages = len(images_origin)
    print(f"[PDF OCR] 共 {total_pages} 页, {NUM_THREAD} 线程并发")

    if total_pages == 0:
        raise RuntimeError("PDF 页数为 0，文件可能为空或损坏")

    # ── 步骤2: 构建任务列表 ──
    jpg_dir = str(Path(file_path).parent / f"{Path(file_path).stem}_pages")
    tasks = [
        {"origin_image": img, "page_idx": i, "save_dir": jpg_dir}
        for i, img in enumerate(images_origin)
    ]

    def _execute_task(task_args: dict):
        """与 ZhipuOCRParser._execute_task 一致 → 调用 _parse_single_image"""
        return _parse_single_image(
            origin_image=task_args["origin_image"],
            page_idx=task_args["page_idx"],
            api_key=api_key,
            save_dir=task_args.get("save_dir"),
        )

    # ── 步骤3: ThreadPool.imap_unordered 并发 ──
    results = []
    with ThreadPool(NUM_THREAD) as pool:
        # 用 iter+print 替代 tqdm (避免额外依赖)
        iterator = pool.imap_unordered(_execute_task, tasks)
        for i, result in enumerate(iterator):
            results.append(result)
            # 实时进度输出
            progress = (i + 1) / total_pages * 100
            print(f"\r[PDF OCR] 进度: {i + 1}/{total_pages} ({progress:.0f}%)", end="")
            sys.stdout.flush()
    print()  # 换行

    # ── 步骤4: 按页码排序合并 ──
    results.sort(key=lambda x: x["page_no"])

    failed_count = sum(1 for r in results if r["text"].startswith("[OCR 失败"))
    if failed_count == total_pages:
        raise RuntimeError(
            f"全部 {total_pages} 页 OCR 均失败。"
            "请检查: 1) API Key 是否有效 2) API 额度是否耗尽 3) 网络是否可达"
        )

    # ── 保存每页原图 .jpg (与 RAG 项目 output 格式一致) ──
    jpg_dir = Path(file_path).parent / f"{Path(file_path).stem}_pages"
    jpg_dir.mkdir(parents=True, exist_ok=True)

    markdown_parts = []
    for r in results:
        page_num = r["page_no"] + 1
        markdown_parts.append(f"## 第{page_num}页\n\n{r['text']}")

        # 保存页面原图
        if r.get("image"):
            img_path = jpg_dir / f"page_{page_num}.jpg"
            try:
                img: Image.Image = r["image"]
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(str(img_path), "JPEG", quality=85)
            except Exception:
                pass

    api_cost = 0.005 * total_pages
    markdown_text = "\n\n".join(markdown_parts)
    print(f"[PDF OCR] 完成: {total_pages} 页, {len(markdown_text)} 字符")
    return markdown_text, total_pages, api_cost


def _parse_single_image(
    origin_image: Image.Image,
    page_idx: int,
    api_key: str,
    save_dir: str = "",
) -> dict:
    """与 ZhipuOCRParser._parse_single_image 一致

    处理流程:
      1. fetch_image → 图片预处理 (smart_resize, 被28整除)
      2. smart_resize → 计算目标尺寸
      3. _inference_with_qwen → API OCR (替代 _inference_with_zhipu)
    """
    # ── fetch_image: 确保图片符合模型要求 ──
    image = _fetch_image(origin_image)
    input_h, input_w = _smart_resize(image.height, image.width)

    # ── API 调用 ──
    response = _inference_with_qwen(image, api_key)

    # ── 结构化 JSON → Markdown + 保存文件 (与 RAG 项目完全一致) ──
    cells = _clean_model_output(response)
    markdown = (
        _layoutjson2md(cells, origin_image, page_idx, save_dir) if cells else response
    )

    # 保存 .json (布局结构化数据, 多模态嵌入需要)
    if save_dir and cells:
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        json_path = Path(save_dir) / f"page_{page_idx}.json"
        json_path.write_text(
            _json_mod.dumps(cells, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # 保存 .md
    if save_dir:
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        md_path = Path(save_dir) / f"page_{page_idx}.md"
        md_path.write_text(markdown, encoding="utf-8")

    # 保存 .jpg (页面原图)
    if save_dir:
        jpg_path = Path(save_dir) / f"page_{page_idx}.jpg"
        if origin_image.mode != "RGB":
            origin_image = origin_image.convert("RGB")
        origin_image.save(str(jpg_path), "JPEG", quality=85)

    return {
        "page_no": page_idx,
        "input_height": input_h,
        "input_width": input_w,
        "text": markdown,
        "image": origin_image,
        "cells": cells,  # 布局结构化数据
    }


def _inference_with_qwen(image: Image.Image, api_key: str) -> str:
    """与 ZhipuOCRParser._inference_with_zhipu 一致, 但调用千问 API

    使用 layout_parser.LAYOUT_PROMPT (与 RAG 项目 prompt_layout_all_en 等价)
    参数: temperature=0.1, top_p=0.1 (与 RAG 项目一致, 保证确定性输出)
    """
    base64_img = _image_to_base64(image)

    try:
        resp = requests.post(
            f"{settings.bailian_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.ocr_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_img}"
                                },
                            },
                            {"type": "text", "text": LAYOUT_PROMPT},
                        ],
                    }
                ],
                "temperature": 0.1,
                "top_p": 0.1,
                "max_tokens": 4096,
            },
            timeout=120,
        )
        if not resp.ok:
            _log.error("千问 API (%d): %s", resp.status_code, resp.text[:300])
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  [错误] API 调用失败: {e}")
        return f"[OCR 失败: {e}]"

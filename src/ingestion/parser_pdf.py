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


def _page_has_meaningful_images(doc, page_idx: int, min_size: int = 50) -> bool:
    """检测页面是否含"有效"图片（非装饰性小图）

    图文混排页（含截图/表格图/商品图）需要走 VLM OCR 同时提取文字+图片，
    只取文本会丢失图片里的信息。
    装饰性小图（图标/分隔线）过滤掉，避免误判为图文页浪费 OCR。
    """
    try:
        for img in doc.get_page_images(page_idx):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            w, h = pix.width, pix.height
            if w >= min_size and h >= min_size:
                return True
    except Exception:
        pass
    return False


# ═══════════════════════════════════════
# 核心: 与 ZhipuOCRParser 同款架构
# ═══════════════════════════════════════


def _parse_pdf(file_path: str, api_key: str):
    """PDF → 文本快路径 + 扫描页 OCR

    修复 (P1):
      - 纯文本页用 fitz.get_text() 零成本提取，只有扫描页才走 VLM OCR（省成本/速度）
      - 强制 settings.pdf_max_pages 上限
      - OCR 失败页剔除（不把错误串入库）
    """
    # ── 步骤1: 打开 PDF，逐页分类（文本页 vs 图文/扫描页）──
    # 优化: 先分类，只渲染需要 OCR 的页（纯文本 PDF 不再渲染全部页）
    print(f"[PDF] 正在加载 PDF: {file_path}")
    text_map: dict[int, str] = {}
    ocr_pages: list[int] = []
    total_pages = 0
    with fitz.open(file_path) as doc:
        total_pages = doc.page_count
        if total_pages == 0:
            raise RuntimeError("PDF 页数为 0，文件可能为空或损坏")

        # 页数上限
        max_pages = getattr(settings, "pdf_max_pages", 50) or 50
        limit = min(total_pages, max_pages)
        if total_pages > max_pages:
            print(f"[PDF] 超过 {max_pages} 页，截断到前 {max_pages} 页")

        # 判断逻辑:
        #   纯文本页(无有效图片 + 文本充足) → fitz 提取（零成本）
        #   图文混排页(含有效图片) / 扫描页(文本不足) → VLM OCR（同时提取文字+图片）
        for idx in range(limit):
            t = doc[idx].get_text().strip()
            has_img = _page_has_meaningful_images(doc, idx)
            if len(t) >= 50 and not has_img:
                text_map[idx] = t
            else:
                ocr_pages.append(idx)

        # 优化: 只渲染需要 OCR 的页
        ocr_images: dict[int, Image.Image] = {
            idx: _fitz_doc_to_image(doc[idx], target_dpi=PDF_DPI) for idx in ocr_pages
        }

    print(f"[PDF] 文本页 {len(text_map)} 个, 图文/扫描页 {len(ocr_pages)} 个")

    # ── 步骤2: 只对图文/扫描页 OCR（复用 ThreadPool）──
    ocr_results: dict[int, dict] = {}
    if ocr_pages:
        jpg_dir = str(Path(file_path).parent / f"{Path(file_path).stem}_pages")
        tasks = [
            {"origin_image": ocr_images[idx], "page_idx": idx, "save_dir": jpg_dir}
            for idx in ocr_pages
        ]

        def _execute_task(task_args: dict):
            return _parse_single_image(
                origin_image=task_args["origin_image"],
                page_idx=task_args["page_idx"],
                api_key=api_key,
                save_dir=task_args.get("save_dir"),
            )

        with ThreadPool(NUM_THREAD) as pool:
            iterator = pool.imap_unordered(_execute_task, tasks)
            for i, result in enumerate(iterator):
                ocr_results[result["page_no"]] = result
                print(f"\r[PDF OCR] 进度: {i + 1}/{len(ocr_pages)}", end="")
                sys.stdout.flush()
        print()

    if not ocr_results and not text_map:
        raise RuntimeError(f"PDF {total_pages} 页均无法提取内容")

    # ── 步骤4: 按页码合并（剔除 OCR 失败页）──
    jpg_dir = Path(file_path).parent / f"{Path(file_path).stem}_pages"
    failed_count = 0
    markdown_parts = []
    for idx in range(limit):
        page_num = idx + 1
        if idx in text_map:
            markdown_parts.append(f"## 第{page_num}页\n\n{text_map[idx]}")
            continue

        r = ocr_results.get(idx)
        if r is None or r["text"].startswith("[OCR 失败"):
            failed_count += 1
            continue  # 修复: 剔除 OCR 失败页

        markdown_parts.append(f"## 第{page_num}页\n\n{r['text']}")
        # 保存页面原图
        if r.get("image"):
            try:
                jpg_dir.mkdir(parents=True, exist_ok=True)
                img: Image.Image = r["image"]
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(str(jpg_dir / f"page_{page_num}.jpg"), "JPEG", quality=85)
            except Exception:
                pass

    if failed_count == limit and limit > 0:
        raise RuntimeError(
            f"全部 {limit} 页解析均失败。"
            "请检查: 1) API Key 是否有效 2) API 额度是否耗尽 3) 网络是否可达"
        )

    # 成本只算 OCR 页（文本页零成本）
    api_cost = 0.005 * len(ocr_pages)
    markdown_text = "\n\n".join(markdown_parts)
    print(
        f"[PDF] 完成: {len(markdown_text)} 字符, OCR {len(ocr_pages)} 页, 失败 {failed_count} 页"
    )
    return markdown_text, limit, api_cost


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

    模型自动切换: 主模型失败时，自动尝试备选模型
    """
    base64_img = _image_to_base64(image)

    # 构建模型列表: 主模型 + 备选模型
    models_to_try = [settings.ocr_model]
    if settings.ocr_model_fallback:
        models_to_try.extend(
            [m.strip() for m in settings.ocr_model_fallback.split(",") if m.strip()]
        )

    last_error = None

    for model_name in models_to_try:
        try:
            resp = requests.post(
                f"{settings.bailian_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_name,
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

            if resp.ok:
                # 成功，记录使用的模型（仅在切换时打印）
                if model_name != settings.ocr_model:
                    print(f"  [切换] 使用备选模型: {model_name}")
                return resp.json()["choices"][0]["message"]["content"].strip()

            # 失败，记录错误
            error_msg = resp.text[:200]
            _log.warning(
                "千问 API (%s, %d): %s", model_name, resp.status_code, error_msg
            )

            # 如果是 403/429（额度耗尽/限流），尝试下一个模型
            if resp.status_code in (403, 429):
                last_error = f"{model_name}: {resp.status_code}"
                print(
                    f"  [切换] {model_name} 不可用 (HTTP {resp.status_code})，尝试下一个模型..."
                )
                continue

            # 其他错误，不重试
            resp.raise_for_status()

        except Exception as e:
            last_error = f"{model_name}: {e}"
            _log.warning("千问 API (%s) 异常: %s", model_name, e)
            continue

    # 所有模型都失败
    print(f"  [错误] 所有 OCR 模型均失败，最后错误: {last_error}")
    return f"[OCR 失败: 所有模型均不可用 ({last_error})]"

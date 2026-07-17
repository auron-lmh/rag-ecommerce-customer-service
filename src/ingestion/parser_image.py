"""图片解析器 — 智谱GLM-4V / 阿里Qwen-VL + 智能缩放 + 质量检测

防御层次:
  1. 文件预检 — 大小/MIME/可读性
  2. 质量评估 — 尺寸/模糊度/可用性
  3. 智能缩放 — 过大图片自动压缩后再送API
  4. API调用 — 双供应商兜底
"""

import base64
import time
from pathlib import Path

import requests

from src.config import settings

from .defenses import assess_image_quality, smart_resize, validate_file
from .models import ParseResult, ParseStatus, RawDocument


def parse_image(doc: RawDocument) -> ParseResult:
    """图片 → 质量检测 → 智能缩放 → VLM多模态API → 文字描述"""
    t0 = time.time()
    result = ParseResult(document=doc, status=ParseStatus.SUCCESS)

    # ═══════════════════════════════════════
    # 第1层：文件预检
    # ═══════════════════════════════════════
    validation = validate_file(doc.file_path, "image")
    result.file_validation = validation

    if not validation.is_valid:
        result.status = ParseStatus.FAILED
        result.errors.extend(validation.errors)
        result.parse_time_ms = (time.time() - t0) * 1000
        return result
    if validation.warnings:
        result.warnings.extend(validation.warnings)

    # ═══════════════════════════════════════
    # 第2层：图片质量评估
    # ═══════════════════════════════════════
    quality = assess_image_quality(doc.file_path)
    result.image_quality = quality

    if not quality.is_usable:
        result.status = ParseStatus.FAILED
        result.errors.extend(quality.issues)
        result.parse_time_ms = (time.time() - t0) * 1000
        return result

    if quality.is_blurry:
        result.warnings.append(
            f"图片清晰度较低（评分: {quality.blur_score:.0f}），" "文字描述可能不够准确"
        )
    if quality.is_too_large:
        result.warnings.extend(quality.issues)

    # ═══════════════════════════════════════
    # 第3层：智能缩放
    # ═══════════════════════════════════════
    image_to_process = doc.file_path
    if quality.needs_resize:
        resized_path, resize_info = smart_resize(doc.file_path)
        result.was_resized = resize_info["was_resized"]
        result.resize_info = resize_info
        image_to_process = resized_path

        if resize_info["was_resized"]:
            result.warnings.append(f"图片已被智能缩放: {resize_info.get('action', '')}")

    # ═══════════════════════════════════════
    # 第4层：读取并编码图片
    # ═══════════════════════════════════════
    try:
        with open(image_to_process, "rb") as f:
            image_data = f.read()
    except Exception as e:
        result.status = ParseStatus.FAILED
        result.errors.append(f"读取图片失败: {e}")
        result.parse_time_ms = (time.time() - t0) * 1000
        return result

    image_b64 = base64.b64encode(image_data).decode()

    ext = Path(doc.file_path).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    mime_type = mime_map.get(ext, "image/png")

    prompt = (
        "请用一段简短的中文描述这张图片的内容。"
        "如果是商品图片，请描述：商品名称、颜色、材质、款式、品牌logo等可见特征。"
        "如果是图表，请提取其中的关键数据和标题。"
        "如果是截图，请提取其中的文字信息。"
        "只需输出描述，不要加'这张图片展示的是...'之类的前缀。"
    )

    # ═══════════════════════════════════════
    # 第5层：API调用（智谱优先，百炼备选）
    # ═══════════════════════════════════════
    description = ""
    api_used = ""

    # 尝试智谱GLM-4V-Flash
    if settings.zhipu_api_key:
        try:
            description = _call_zhipu(image_b64, mime_type, prompt)
            if description:
                api_used = "zhipu"
                result.api_cost_estimate = 0.002
        except Exception as e:
            result.warnings.append(f"智谱API失败，尝试备选: {e}")

    # 备选百炼Qwen-VL
    if not description and settings.bailian_api_key:
        try:
            description = _call_bailian_vision(image_b64, mime_type, prompt)
            if description:
                api_used = "bailian"
                result.api_cost_estimate = 0.005
        except Exception as e:
            result.warnings.append(f"百炼API也失败: {e}")

    # ═══════════════════════════════════════
    # 第6层：结果校验
    # ═══════════════════════════════════════
    if not description:
        result.status = ParseStatus.FAILED
        result.errors.append(
            "所有图片理解API均失败，请检查 ZHIPU_API_KEY 或 BAILIAN_API_KEY"
        )
        result.parse_time_ms = (time.time() - t0) * 1000
        return result

    if len(description) < 5:
        result.warnings.append("生成的图片描述过短，可能不完整")

    result.markdown = description
    result.api_calls = 1
    result.parse_time_ms = (time.time() - t0) * 1000

    return result


def _call_zhipu(image_b64: str, mime_type: str, prompt: str) -> str:
    resp = requests.post(
        f"{settings.zhipu_base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.zhipu_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}"
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "max_tokens": 512,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _call_bailian_vision(image_b64: str, mime_type: str, prompt: str) -> str:
    resp = requests.post(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.bailian_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "qwen-vl-plus",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}"
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "max_tokens": 512,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()

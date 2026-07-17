"""模块1 企业级防御层 — 文件校验 / 图片质量检测 / 智能缩放 / 模糊检测

生产环境中，用户上传的文件千奇百怪。此模块在解析前拦截已知问题，
在解析中记录质量信号，确保系统"能降级但从不崩溃"。
"""

import hashlib
import io
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError

from src.config import settings

# ═══════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════


@dataclass
class FileValidation:
    """文件预检结果"""

    is_valid: bool
    file_path: str
    file_size_bytes: int = 0
    file_size_mb: float = 0.0
    mime_type: str = ""
    extension: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ImageQuality:
    """图片质量评估"""

    is_usable: bool
    width: int = 0
    height: int = 0
    file_size_mb: float = 0.0
    blur_score: float = 0.0  # Laplacian方差，越高越清晰
    is_blurry: bool = False  # < 100 视为模糊
    is_too_small: bool = False  # 任一边 < 50px
    is_too_large: bool = False  # 任一边 > 4096px 或 文件 > 10MB
    needs_resize: bool = False
    quality_label: str = "good"  # good / fair / poor
    issues: list[str] = field(default_factory=list)


@dataclass
class PageQuality:
    """PDF逐页质量"""

    page_num: int
    has_text: bool = True
    text_length: int = 0
    image_count: int = 0
    dpi_estimate: int = 0
    is_scanned: bool = False
    quality_label: str = "good"  # good / fair / poor / unreadable
    issues: list[str] = field(default_factory=list)


@dataclass
class ExtractedImage:
    """从PDF中提取的图片"""

    image_id: str
    source_pdf: str
    page_num: int
    index_on_page: int
    saved_path: str
    format: str  # png / jpeg
    width: int
    height: int
    file_size_bytes: int
    quality: ImageQuality | None = None
    markdown_ref: str = ""  # ![img](./images/xxx.png)


# ═══════════════════════════════════════
# 文件预检
# ═══════════════════════════════════════

# 允许的文件大小上限
MAX_FILE_SIZE_MB = {
    "pdf": 50,
    "word": 20,
    "excel": 20,
    "ppt": 30,
    "image": 10,
    "json": 5,
    "default": 20,
}

# MIME类型白名单
ALLOWED_MIME = {
    ".pdf": ["application/pdf"],
    ".docx": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ],
    ".doc": ["application/msword"],
    ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
    ".xls": ["application/vnd.ms-excel"],
    ".pptx": [
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ],
    ".png": ["image/png"],
    ".jpg": ["image/jpeg"],
    ".jpeg": ["image/jpeg"],
    ".webp": ["image/webp"],
    ".gif": ["image/gif"],
    ".json": ["application/json"],
    ".txt": ["text/plain"],
}


def validate_file(file_path: str, doc_type: str = "") -> FileValidation:
    """预检文件——大小、MIME、是否可读

    在解析前调用。不合规的文件直接拒绝，不给下游解析器添乱。
    """
    result = FileValidation(file_path=file_path, is_valid=True)

    path = Path(file_path)
    result.extension = path.suffix.lower()

    # 1. 文件存在
    if not path.exists():
        result.is_valid = False
        result.errors.append(f"文件不存在: {file_path}")
        return result

    # 2. 非空
    result.file_size_bytes = path.stat().st_size
    result.file_size_mb = round(result.file_size_bytes / (1024 * 1024), 2)

    if result.file_size_bytes == 0:
        result.is_valid = False
        result.errors.append("文件为空 (0 bytes)")
        return result

    # 3. 大小上限
    max_mb = MAX_FILE_SIZE_MB.get(doc_type, MAX_FILE_SIZE_MB["default"])
    if result.file_size_mb > max_mb:
        result.is_valid = False
        result.errors.append(
            f"文件过大 ({result.file_size_mb:.1f}MB), 上限 {max_mb}MB. "
            f"建议压缩后重新上传"
        )
        return result

    # 4. MIME类型校验（读取文件头魔数）
    mime = _detect_mime(path)
    result.mime_type = mime

    expected = ALLOWED_MIME.get(result.extension, [])
    if expected and mime not in expected:
        # MIME不匹配——可能是伪装文件，但不直接拒绝（有些工具生成的MIME不标准）
        result.warnings.append(
            f"MIME类型不匹配: 扩展名{result.extension}但文件头为{mime}"
        )

    # 5. 文件可读性
    try:
        with open(file_path, "rb") as f:
            f.read(1024)
    except (PermissionError, OSError) as e:
        result.is_valid = False
        result.errors.append(f"文件不可读: {e}")

    return result


def _detect_mime(path: Path) -> str:
    """读文件头魔数判断真实类型"""
    try:
        with open(path, "rb") as f:
            header = f.read(16)

        # 常见魔数
        if header[:4] == b"%PDF":
            return "application/pdf"
        if header[:2] == b"PK":
            # ZIP-based formats (docx/xlsx/pptx都是ZIP)
            # 进一步检查内部文件
            return _check_zip_type(path)
        if header[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if header[:2] == b"\xff\xd8":
            return "image/jpeg"
        if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
            return "image/webp"
        if header[:4] == b"GIF8":
            return "image/gif"
        if header[:4] == b"\xd0\xcf\x11\xe0":
            return "application/msword"  # 旧版Office格式
    except Exception:
        pass
    return "application/octet-stream"


def _check_zip_type(path: Path) -> str:
    """ZIP内部检查区分docx/xlsx/pptx"""
    import zipfile

    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            if any("word/document.xml" in n for n in names):
                return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if any("xl/workbook.xml" in n for n in names):
                return (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            if any("ppt/presentation.xml" in n for n in names):
                return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    except (zipfile.BadZipFile, Exception):
        pass
    return "application/zip"


# ═══════════════════════════════════════
# 图片质量检测
# ═══════════════════════════════════════


def assess_image_quality(image_path: str) -> ImageQuality:
    """评估图片质量——尺寸/模糊度/可用性

    规则:
      - 任一边 < 50px  → too_small (无法有效描述)
      - 任一边 > 4096px → too_large (VLM API限制，需缩放)
      - 文件 > 10MB     → too_large (API限制)
      - 模糊度 < 100     → blurry (Laplacian方差阈值)
    """
    result = ImageQuality(is_usable=True)
    path = Path(image_path)

    try:
        img = Image.open(image_path)
        result.width, result.height = img.size
        result.file_size_mb = round(path.stat().st_size / (1024 * 1024), 2)

        # ── 尺寸检测 ──
        if result.width < 50 or result.height < 50:
            result.is_too_small = True
            result.is_usable = False
            result.issues.append(
                f"图片过小 ({result.width}×{result.height}px)，"
                f"无法生成有意义的文字描述"
            )
            result.quality_label = "poor"
            return result

        if result.width > 4096 or result.height > 4096:
            result.is_too_large = True
            result.needs_resize = True
            result.issues.append(
                f"图片尺寸过大 ({result.width}×{result.height}px)，"
                f"将被缩放到 2048px 以内"
            )
            # 不标记为unusable——缩放后可用

        if result.file_size_mb > 10:
            result.is_too_large = True
            result.needs_resize = True
            result.issues.append(
                f"图片文件过大 ({result.file_size_mb:.1f}MB)，将被压缩"
            )
        elif result.file_size_mb > 5:
            result.needs_resize = True
            result.issues.append(
                f"图片较大 ({result.file_size_mb:.1f}MB)，建议压缩后上传"
            )

        # ── 模糊检测 ──
        result.blur_score = _calculate_blur_score(img)
        if result.blur_score < 100:
            result.is_blurry = True
            result.issues.append(
                f"图片较模糊 (清晰度评分: {result.blur_score:.0f}/100+)，"
                f"VLM描述可能不准确"
            )
            # 模糊不标记为unusable——VLM可能仍能提取部分信息
            if result.quality_label == "good":
                result.quality_label = "fair"

        if result.blur_score < 50:
            result.quality_label = "poor"
            result.issues.append("图片严重模糊，文字提取可能失败")

        img.close()

    except UnidentifiedImageError:
        result.is_usable = False
        result.quality_label = "poor"
        result.issues.append("无法识别图片格式（文件可能已损坏）")
    except Exception as e:
        result.is_usable = False
        result.quality_label = "poor"
        result.issues.append(f"图片质量检测异常: {e}")

    return result


def _calculate_blur_score(img: Image.Image) -> float:
    """Laplacian方差法计算清晰度

    算法: 转灰度 → 手动Laplacian卷积 → 方差
    方差越高 = 边缘越多 = 图片越清晰
    阈值经验值: < 50 严重模糊 / 50-100 轻微模糊 / > 100 清晰

    纯numpy实现，零额外依赖。numpy已在项目依赖中。
    """
    try:
        gray = img.convert("L")
        arr = np.array(gray, dtype=np.float64)

        # 手工3x3 Laplacian核: [[0,1,0],[1,-4,1],[0,1,0]]
        h, w = arr.shape
        lap = np.zeros_like(arr)

        # 内层区域（避免边界，速度优先）
        if h > 2 and w > 2:
            lap[1:-1, 1:-1] = (
                arr[0:-2, 1:-1]  # 上
                + arr[2:, 1:-1]  # 下
                + arr[1:-1, 0:-2]  # 左
                + arr[1:-1, 2:]  # 右
                - 4 * arr[1:-1, 1:-1]  # 中心×4
            )

        variance = float(lap.var())
        return round(variance, 1)
    except Exception:
        return 200.0  # 无法检测时返回默认高分，不阻塞流程


# ═══════════════════════════════════════
# 智能缩放
# ═══════════════════════════════════════


def smart_resize(
    image_path: str,
    max_dim: int = 2048,
    max_mb: float = 5.0,
    quality: int = 85,
) -> tuple[str, dict]:
    """智能缩放图片——超过阈值才缩放，否则原样透传

    Returns:
        (处理后图片路径, 缩放信息dict)
    """
    path = Path(image_path)
    info = {
        "was_resized": False,
        "original_size": path.stat().st_size,
        "original_dims": (0, 0),
        "new_size": path.stat().st_size,
        "new_dims": (0, 0),
        "action": "none",
    }

    try:
        img = Image.open(image_path)
        info["original_dims"] = img.size
        w, h = img.size

        need_resize = w > max_dim or h > max_dim
        file_too_big = path.stat().st_size > max_mb * 1024 * 1024

        if not need_resize and not file_too_big:
            img.close()
            info["new_dims"] = (w, h)
            info["new_size"] = path.stat().st_size
            return str(path), info

        # ── 尺寸缩放 ──
        if need_resize:
            ratio = min(max_dim / w, max_dim / h)
            new_w, new_h = int(w * ratio), int(h * ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            info["was_resized"] = True
            info["new_dims"] = (new_w, new_h)
            info["action"] = f"resize: {w}×{h} → {new_w}×{new_h}"
        else:
            info["new_dims"] = (w, h)

        # ── 保存处理后的图片 ──
        suffix = path.suffix.lower()
        if suffix not in (".jpg", ".jpeg", ".png", ".webp"):
            suffix = ".png"

        temp_fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix="resized_")
        import os

        os.close(temp_fd)

        if suffix in (".jpg", ".jpeg"):
            img = img.convert("RGB")  # JPEG无alpha通道
            img.save(temp_path, "JPEG", quality=quality)
        elif suffix == ".webp":
            img.save(temp_path, "WEBP", quality=quality)
        else:
            img.save(temp_path, "PNG", optimize=True)

        info["new_size"] = Path(temp_path).stat().st_size

        # 如果压缩后仍然超过限制
        if info["new_size"] > max_mb * 1024 * 1024:
            # 二次压缩，降低质量
            if suffix in (".jpg", ".jpeg"):
                img.save(temp_path, "JPEG", quality=60)
            elif suffix == ".webp":
                img.save(temp_path, "WEBP", quality=60)
            info["new_size"] = Path(temp_path).stat().st_size
            info["action"] += f" + recompress: quality {quality}→60"

        img.close()

        # 如果处理后的文件比原文件还大，保留原文件
        if info["new_size"] >= info["original_size"] and not need_resize:
            Path(temp_path).unlink(missing_ok=True)
            info["action"] = "kept_original (compression didn't help)"
            info["new_size"] = info["original_size"]
            return str(path), info

        return temp_path, info

    except Exception as e:
        # 缩放失败→透传原文件
        info["action"] = f"resize_failed: {e}, using original"
        info["new_size"] = info["original_size"]
        return str(path), info


# ═══════════════════════════════════════
# 图片智能增强
# ═══════════════════════════════════════


def enhance_image(
    image_path: str,
    quality: ImageQuality,
    output_dir: str | None = None,
) -> tuple[str, dict]:
    """根据质量评估结果，智能增强图片

    处理策略:
      - 模糊 (blur_score < 100)  → Unsharp Mask 锐化
      - 过小 (width < 100)       → Lanczos 2x 超分辨率
      - 偏暗 (mean < 60)         → 自动对比度拉伸
      - 同时存在多个问题         → 先缩放→再锐化→再调光

    Returns:
        (增强后图片路径, 增强信息dict)
    """
    if output_dir is None:
        output_dir = str(settings.data_dir / "images" / "enhanced")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    info = {
        "was_enhanced": False,
        "actions": [],
        "original_path": image_path,
        "output_path": image_path,
    }

    try:
        img = Image.open(image_path)
        enhanced = False

        # ── 步骤1: 超分辨率（小图先放大）──
        if quality.is_too_small and quality.width > 10:
            new_w = min(quality.width * 2, 400)
            new_h = min(quality.height * 2, 400)
            ratio = min(new_w / quality.width, new_h / quality.height)
            if ratio > 1.0:
                img = img.resize(
                    (int(quality.width * ratio), int(quality.height * ratio)),
                    Image.LANCZOS,
                )
                info["actions"].append(
                    f"upscale: {quality.width}×{quality.height} → {img.size[0]}×{img.size[1]}"
                )
                enhanced = True

        # ── 步骤2: 锐化（模糊图恢复边缘）──
        if quality.is_blurry:
            img = _apply_sharpen(img)
            info["actions"].append(
                f"sharpen: blur_score {quality.blur_score:.0f} → unsharp_mask applied"
            )
            enhanced = True

        # ── 步骤3: 自动对比度（暗图提亮）──
        img_gray = img.convert("L")
        mean_brightness = np.array(img_gray).mean()
        if mean_brightness < 60:
            img = _apply_auto_contrast(img)
            info["actions"].append(
                f"auto_contrast: mean_brightness {mean_brightness:.0f} → stretched"
            )
            enhanced = True

        # ── 保存增强后图片 ──
        if enhanced:
            stem = Path(image_path).stem
            ext = Path(image_path).suffix.lower()
            if ext not in (".png", ".jpg", ".jpeg", ".webp"):
                ext = ".png"

            save_path = str(Path(output_dir) / f"{stem}_enhanced{ext}")
            if ext in (".jpg", ".jpeg"):
                img = img.convert("RGB")
                img.save(save_path, "JPEG", quality=90)
            elif ext == ".webp":
                img.save(save_path, "WEBP", quality=90)
            else:
                img.save(save_path, "PNG")

            info["was_enhanced"] = True
            info["output_path"] = save_path
        else:
            info["output_path"] = image_path

        img.close()

    except Exception as e:
        info["actions"].append(f"enhancement_failed: {e}")
        info["output_path"] = image_path

    return info["output_path"], info


def _apply_sharpen(img: Image.Image) -> Image.Image:
    """Unsharp Mask 锐化

    原理: 原图 + (原图 - 高斯模糊) × amount
    这比直接加Laplacian边缘更自然，不易出现光晕。
    """
    from PIL import ImageFilter

    # 三步法Unsharp Mask
    blurred = img.filter(ImageFilter.GaussianBlur(radius=2))
    # 原图 - 模糊图 = 高频细节
    # 原图 + 高频细节 × 1.5 = 锐化图
    img_sharp = Image.blend(img, blurred, alpha=-0.3)  # 负alpha = 原图+(原图-模糊)×0.3

    # 手动实现（更可控）
    arr = np.array(img).astype(np.float64)
    blur_arr = np.array(blurred).astype(np.float64)
    sharpened = arr + (arr - blur_arr) * 1.5  # amount = 1.5
    sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)

    return Image.fromarray(sharpened)


def _apply_auto_contrast(img: Image.Image) -> Image.Image:
    """自动对比度拉伸——裁切2%的极端值后拉伸到[0,255]"""
    arr = np.array(img.convert("L")).astype(np.float64)

    # 裁切上下2%
    low = np.percentile(arr, 2)
    high = np.percentile(arr, 98)

    if high - low < 10:
        return img  # 对比度已经很低，拉伸无意义

    # 拉伸到[0, 255]
    arr_stretched = (arr - low) * 255.0 / (high - low)
    arr_stretched = np.clip(arr_stretched, 0, 255).astype(np.uint8)

    # 转回RGB
    gray_stretched = Image.fromarray(arr_stretched)

    if img.mode in ("RGB", "RGBA"):
        # 保留原始色相，在HSV的V通道做拉伸
        try:
            hsv = img.convert("HSV")
            hsv_arr = np.array(hsv)
            v_channel = hsv_arr[:, :, 2].astype(np.float64)
            v_stretched = (v_channel - low) * 255.0 / max(high - low, 1)
            v_stretched = np.clip(v_stretched, 0, 255).astype(np.uint8)
            hsv_arr[:, :, 2] = v_stretched
            return Image.fromarray(hsv_arr, "HSV").convert("RGB")
        except Exception:
            pass

    return gray_stretched.convert("RGB") if img.mode != "L" else gray_stretched


# ═══════════════════════════════════════
# PDF质量评估
# ═══════════════════════════════════════


def assess_pdf_quality(file_path: str) -> list[PageQuality]:
    """逐页评估PDF质量——文本量/图片数/DPI/是否扫描件

    返回每页的PageQuality，供上层决定哪些页需要OCR。
    """
    pages = []
    try:
        import fitz

        doc = fitz.open(file_path)

        for i in range(len(doc)):
            page = doc[i]
            pq = PageQuality(page_num=i + 1)

            # 文本量
            text = page.get_text("text")
            pq.text_length = len(text.strip())
            pq.has_text = pq.text_length > 50

            # 图片数
            images = page.get_images()
            pq.image_count = len(images)

            # 判断是否扫描件：文字很少 + 图片多 = 扫描
            if pq.text_length < 50 and pq.image_count >= 1:
                pq.is_scanned = True
                pq.quality_label = "fair"
                pq.issues.append(
                    f"可能为扫描页（文字量{pq.text_length}字，{pq.image_count}张图片）"
                )

            if pq.text_length == 0 and pq.image_count == 0:
                pq.quality_label = "poor"
                pq.issues.append("空白页")
            elif pq.text_length < 20 and pq.image_count == 0:
                pq.quality_label = "poor"
                pq.issues.append(f"内容极少（{pq.text_length}字）")

            pages.append(pq)

        doc.close()
    except ImportError:
        pass  # PyMuPDF未安装时跳过
    except Exception:
        pass

    return pages


# ═══════════════════════════════════════
# PDF图片提取
# ═══════════════════════════════════════


def extract_pdf_images(
    pdf_path: str,
    output_dir: str | None = None,
    min_size: int = 100,
    enhance: bool = True,
) -> tuple[list[ExtractedImage], dict[int, list[str]]]:
    """从PDF中提取所有嵌入图片，记录页面位置，自动增强质量问题图片

    图片命名规则: {pdf_stem}_p{page}_{index}.{ext}
    占位符格式: <!-- IMG_P{p}_{idx} -->![描述](./images/xxx.png)

    Args:
        pdf_path: PDF文件路径
        output_dir: 图片输出目录
        min_size: 最小尺寸(px)，图标/装饰图跳过
        enhance: 是否自动增强模糊/过小/偏暗的图片

    Returns:
        (
            提取的图片列表 (含位置元数据),
            {page_num: [placeholder_str, ...]}  # 按页分组的占位符
        )
    """
    if output_dir is None:
        output_dir = str(settings.data_dir / "images")

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    extracted: list[ExtractedImage] = []
    page_placeholders: dict[int, list[str]] = {}
    pdf_stem = Path(pdf_path).stem

    try:
        import fitz

        doc = fitz.open(pdf_path)

        for page_num in range(len(doc)):
            page = doc[page_num]
            images = page.get_images(full=True)

            page_refs: list[str] = []

            for img_idx, img_info in enumerate(images):
                xref = img_info[0]
                base_image = doc.extract_image(xref)

                if base_image is None:
                    continue

                img_bytes = base_image["image"]
                ext = base_image["ext"]

                # 获取图片在页面上的位置（bbox）
                # img_info[1:] = (x0, y0, x1, y1) 在部分版本中可用
                # 用 get_image_bbox 更可靠
                try:
                    bbox = page.get_image_bbox(img_info)
                except Exception:
                    bbox = None

                try:
                    pil_img = Image.open(io.BytesIO(img_bytes))
                    w, h = pil_img.size
                    pil_img.close()
                except Exception:
                    continue

                if w < min_size and h < min_size:
                    continue

                # 保存原始图片
                filename = f"{pdf_stem}_p{page_num + 1}_{img_idx + 1}.{ext}"
                save_path = str(Path(output_dir) / filename)

                with open(save_path, "wb") as f:
                    f.write(img_bytes)

                # 质量评估
                quality = assess_image_quality(save_path)

                # 智能增强
                if (
                    enhance
                    and quality.is_usable
                    and (quality.is_blurry or quality.is_too_small)
                ):
                    enhanced_path, enhance_info = enhance_image(save_path, quality)
                    if enhance_info["was_enhanced"]:
                        save_path = enhanced_path
                        # 重新评估增强后的质量
                        quality = assess_image_quality(save_path)

                # 位置标记 — 用于模块10图文对齐
                position_meta = ""
                if bbox:
                    y_rel = round(bbox.y0 / page.rect.height, 3)  # 0.0=页顶, 1.0=页底
                    position_meta = f"pos:{y_rel}"

                # HTML注释占位符 — 下游模块可解析，渲染时不可见
                placeholder = (
                    f"<!-- IMG_P{page_num + 1}_{img_idx + 1} "
                    f"src={filename} "
                    f"size={w}x{h} "
                    f"quality={quality.quality_label} "
                    f"blur={quality.blur_score:.0f} "
                    f"{position_meta}"
                    f" -->\n"
                    f"![{filename}](./images/{filename})"
                )

                extracted_img = ExtractedImage(
                    image_id=hashlib.md5(
                        f"{pdf_path}#p{page_num}#i{img_idx}".encode()
                    ).hexdigest()[:12],
                    source_pdf=str(Path(pdf_path).resolve()),
                    page_num=page_num + 1,
                    index_on_page=img_idx + 1,
                    saved_path=save_path,
                    format=ext,
                    width=w,
                    height=h,
                    file_size_bytes=len(img_bytes),
                    quality=quality,
                    markdown_ref=placeholder,
                )

                extracted.append(extracted_img)
                page_refs.append(placeholder)

            if page_refs:
                page_placeholders[page_num + 1] = page_refs

        doc.close()

    except ImportError:
        pass
    except Exception:
        pass

    return extracted, page_placeholders


def inject_placeholders_into_markdown(
    markdown: str,
    page_placeholders: dict[int, list[str]],
    page_qualities: list[PageQuality],
) -> str:
    """将图片占位符注入到Markdown中对应页面的位置

    策略:
      1. 遍历Markdown行，查找页面边界标记（如 "## Page N" / 页码）
      2. 在每页内容末尾插入该页的图片占位符
      3. 如果Markdown中没有页面标记，按文本比例估算插入位置

    Args:
        markdown: API返回的Markdown文本
        page_placeholders: {page_num: [placeholder_str, ...]}
        page_qualities: 逐页质量列表

    Returns:
        注入占位符后的Markdown
    """
    if not page_placeholders:
        return markdown

    lines = markdown.split("\n")
    total_pages = len(page_qualities)
    if total_pages == 0:
        return markdown

    # ── 策略1: 查找明确的分页标记 ──
    page_markers: dict[int, int] = {}  # page_num → line_index
    import re

    for i, line in enumerate(lines):
        # 匹配 "## 第N页" / "## Page N" / "--- Page N ---" 等
        for m in re.finditer(r"(?:第|Page\s*)(\d+)(?:\s*页)?", line, re.IGNORECASE):
            pn = int(m.group(1))
            if 1 <= pn <= total_pages:
                page_markers[pn] = i

    # ── 策略2: 按比例估算（无明确分页标记时）──
    if not page_markers:
        # 每页约占总行数的 1/total_pages
        lines_per_page = len(lines) / max(total_pages, 1)
        for pn in range(1, total_pages + 1):
            page_markers[pn] = int(lines_per_page * (pn - 1))

    # ── 注入占位符 ──
    # 按行号从大到小插入（避免插入后行号变化）
    injections: list[tuple[int, str]] = []
    for page_num, placeholders in page_placeholders.items():
        if page_num in page_markers:
            insert_at = min(page_markers[page_num] + 5, len(lines))  # 分页标记后5行
        else:
            # 估算位置
            insert_at = int(len(lines) * (page_num - 1) / max(total_pages, 1))

        block = "\n\n<!-- ═══ 第{}页图片 ═══ -->\n{}\n".format(
            page_num,
            "\n".join(placeholders),
        )
        injections.append((min(insert_at, len(lines)), block))

    # 从后往前插入
    injections.sort(key=lambda x: x[0], reverse=True)
    for insert_at, block in injections:
        lines.insert(insert_at, block)

    return "\n".join(lines)


# ═══════════════════════════════════════
# API重试工具
# ═══════════════════════════════════════


def retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
):
    """指数退避重试——专门处理API 429(限流)和5xx(服务不可用)

    Args:
        func: 要重试的无参函数
        max_retries: 最大重试次数
        base_delay: 初始等待秒数
        max_delay: 最大等待秒数上限
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            result = func()
            return result, None
        except Exception as e:
            last_error = e
            if attempt == max_retries:
                break

            # 判断是否可重试的错误
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            if status_code == 429:
                # 限流——读Retry-After头
                retry_after = getattr(getattr(e, "response", None), "headers", {}).get(
                    "Retry-After", ""
                )
                if retry_after:
                    delay = min(float(retry_after), max_delay)
                else:
                    delay = min(base_delay * (2**attempt), max_delay)
            elif status_code and status_code >= 500:
                delay = min(base_delay * (2**attempt), max_delay)
            else:
                # 4xx客户端错误不重试
                break

            time.sleep(delay)

    return None, last_error

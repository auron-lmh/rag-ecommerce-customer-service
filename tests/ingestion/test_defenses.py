"""模块1防御层测试"""

import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from src.ingestion.defenses import (
    _calculate_blur_score,
    assess_image_quality,
    smart_resize,
    validate_file,
)


class TestFileValidation:
    """文件预检"""

    def test_nonexistent_file(self):
        v = validate_file("nonexistent_xyz.pdf")
        assert not v.is_valid
        assert any("不存在" in e for e in v.errors)

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pass  # 0 bytes
        v = validate_file(f.name)
        Path(f.name).unlink()
        assert not v.is_valid
        assert any("空" in e for e in v.errors)

    def test_valid_json(self):
        import json

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump([{"q": "test"}], f)
            tmp = f.name
        v = validate_file(tmp)
        Path(tmp).unlink()
        assert v.is_valid


class TestBlurDetection:
    """模糊检测"""

    def test_sharp_image(self):
        # 生成纯黑白棋盘图（高方差=清晰）
        arr = np.zeros((200, 200), dtype=np.uint8)
        arr[::20, :] = 255
        arr[:, ::20] = 255
        img = Image.fromarray(arr)
        score = _calculate_blur_score(img)
        assert score > 100, f"Expected sharp, got {score}"

    def test_blurry_image(self):
        # 生成均匀灰色图（低方差=模糊）
        arr = np.ones((200, 200), dtype=np.uint8) * 128
        img = Image.fromarray(arr)
        score = _calculate_blur_score(img)
        assert score < 100, f"Expected blurry, got {score}"


class TestImageQuality:
    """图片质量评估"""

    def test_tiny_image(self):
        # 10x10 的图片太小说
        img = Image.new("RGB", (10, 10), "red")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img.save(f, "PNG")
            tmp = f.name
        q = assess_image_quality(tmp)
        Path(tmp).unlink()
        assert not q.is_usable
        assert q.is_too_small

    def test_normal_image(self):
        img = Image.new("RGB", (500, 500), "blue")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img.save(f, "PNG")
            tmp = f.name
        q = assess_image_quality(tmp)
        Path(tmp).unlink()
        assert q.is_usable


class TestSmartResize:
    """智能缩放"""

    def test_normal_image_no_resize(self):
        img = Image.new("RGB", (500, 500), "green")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img.save(f, "PNG")
            tmp = f.name
        path, info = smart_resize(tmp, max_dim=2048)
        Path(tmp).unlink()
        assert not info["was_resized"]
        assert info["action"] == "none"

    def test_large_image_gets_resized(self):
        # 创建超限图片
        img = Image.new("RGB", (3000, 3000), "red")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img.save(f, "PNG")
            tmp = f.name
        path, info = smart_resize(tmp, max_dim=2048)
        # 清理缩放产生的临时文件
        Path(tmp).unlink()
        if path != tmp:
            Path(path).unlink(missing_ok=True)
        assert info["was_resized"]

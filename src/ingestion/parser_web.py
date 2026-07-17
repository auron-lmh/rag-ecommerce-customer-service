"""网页解析器 — requests + BeautifulSoup

抓取商品详情页 → 提取正文 → 去噪
"""

import time

import requests
from bs4 import BeautifulSoup

from .models import ParseResult, ParseStatus, RawDocument


def parse_webpage(doc: RawDocument) -> ParseResult:
    """抓取网页并提取正文"""
    t0 = time.time()
    result = ParseResult(document=doc, status=ParseStatus.SUCCESS)

    url = doc.file_path

    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            timeout=15,
        )
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"

        soup = BeautifulSoup(resp.text, "lxml")

        # 移除无用标签
        for tag in soup(
            ["script", "style", "nav", "footer", "header", "aside", "noscript"]
        ):
            tag.decompose()

        # 尝试提取正文区域 (常见电商页面结构)
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", class_="detail")
            or soup.find("div", id="detail")
            or soup.find("body")
        )

        if main_content:
            text = main_content.get_text(separator="\n")
        else:
            text = soup.get_text(separator="\n")

        # 清理
        lines = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped and len(stripped) > 2:
                lines.append(stripped)

        result.markdown = "\n".join(lines)
        result.parse_time_ms = (time.time() - t0) * 1000

    except requests.exceptions.Timeout:
        result.status = ParseStatus.FAILED
        result.errors.append(f"网页请求超时: {url}")
    except requests.exceptions.RequestException as e:
        result.status = ParseStatus.FAILED
        result.errors.append(f"网页请求失败: {e}")
    except Exception as e:
        result.status = ParseStatus.FAILED
        result.errors.append(f"网页解析失败: {e}")

    result.parse_time_ms = (time.time() - t0) * 1000
    return result

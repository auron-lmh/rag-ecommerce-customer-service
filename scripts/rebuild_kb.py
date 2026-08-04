"""用新鲜进程重建知识库（确定性 dc9a 空间，与 benchmark 新进程一致）

用法: 在容器内执行
    python /app/scripts/rebuild_kb.py

读取 /app/data/raw/*.md → 解析 → 分块 → 向量化 → 入库
"""

import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.embedding.pipeline import IndexingPipeline
from src.ingestion.router import parse_file

pipeline = IndexingPipeline()
pipeline.store.create_collection(drop_if_exists=True)
print("已重建 collection")

files = sorted(
    f
    for f in glob.glob("/app/data/raw/*.md")
    if not f.endswith(("api_upload.py", "rebuild_kb.py"))
)
print(f"发现 {len(files)} 个 MD 文件")

total = 0
for f in files:
    name = Path(f).name
    try:
        result = parse_file(f)
        if not (result.markdown or "").strip():
            print(f"{name}: 跳过(解析为空)")
            continue
        report = pipeline.run_from_text(result.markdown, name, result.document.doc_type)
        total += report.get("inserted", 0)
        print(f"{name}: {report.get('status')} ({report.get('inserted', 0)} 向量)")
    except Exception as e:
        print(f"{name}: 错误 {e}")

print(f"\n总计: {total} 向量")

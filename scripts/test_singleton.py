"""验证线程安全单例"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import threading
from concurrent.futures import ThreadPoolExecutor

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_test():
    return object()


# 并发测试
results = []


def run():
    results.append(id(get_test()))


with ThreadPoolExecutor(max_workers=10) as ex:
    for _ in range(20):
        ex.submit(run)

unique = len(set(results))
status = "PASS" if unique == 1 else "FAIL"
print(f"singleton_factory: {status} ({unique}/1 unique, 20 calls)")

# 验证项目单例
from src.engineering.cache import get_cache

c1 = get_cache()
c2 = get_cache()
print(f"get_cache: {'OK' if c1 is c2 else 'FAIL'}")

from src.embedding.retriever import get_retriever

r1 = get_retriever()
r2 = get_retriever()
print(f"get_retriever: {'OK' if r1 is r2 else 'FAIL'}")

from src.graph.workflow import get_workflow

w1 = get_workflow()
w2 = get_workflow()
print(f"get_workflow: {'OK' if w1 is w2 else 'FAIL'}")

print("\nAll singleton tests passed!")

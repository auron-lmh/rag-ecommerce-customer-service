"""线程安全的模块级单例工具

消除项目中 20+ 处无锁单例模式，提供统一的线程安全实现。

模式对比:
    # 旧模式（无锁）
    _instance = None
    def get_xxx():
        global _instance
        if _instance is None:
            _instance = Xxx()
        return _instance

    # 新模式（线程安全）
    from src.engineering.singleton import singleton_factory

    @singleton_factory
    def get_xxx():
        return Xxx()

使用:
    from src.engineering.singleton import singleton

    @singleton  # 装饰类本身
    class MyService:
        def __init__(self):
            ...

    service = MyService()  # 返回同一个实例
"""

import threading
from functools import wraps
from typing import Any, Callable, Type, TypeVar

T = TypeVar("T")


def singleton_factory(factory: Callable[[], T]) -> Callable[[], T]:
    """装饰工厂函数，使其成为线程安全的单例

    使用双重检查锁定模式（DCL），避免每次调用都获取锁。

    Example:
        @singleton_factory
        def get_retriever():
            from src.embedding.retriever import Retriever
            return Retriever()
    """
    instance: T | None = None
    lock = threading.Lock()

    @wraps(factory)
    def wrapper() -> T:
        nonlocal instance
        if instance is None:
            with lock:
                if instance is None:
                    instance = factory()
        return instance

    wrapper._singleton_lock = lock  # type: ignore
    wrapper._singleton_instance = instance  # type: ignore
    return wrapper


class SingletonMeta(type):
    """线程安全的单例元类

    使用方式:
        class MyService(metaclass=SingletonMeta):
            def __init__(self):
                ...
    """

    _instances: dict[type, Any] = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in SingletonMeta._instances:
            with SingletonMeta._lock:
                if cls not in SingletonMeta._instances:
                    instance = super().__call__(*args, **kwargs)
                    SingletonMeta._instances[cls] = instance
        return SingletonMeta._instances[cls]


def singleton(cls):
    """类装饰器，将类变为线程安全的单例

    使用方式:
        @singleton
        class MyService:
            def __init__(self):
                ...

        s1 = MyService()
        s2 = MyService()
        assert s1 is s2  # True
    """
    cls.__new_original__ = cls.__new__  # type: ignore

    _instance = None
    _lock = threading.Lock()

    @wraps(cls.__new_original__)  # type: ignore
    def _new(cls_, *args, **kwargs):
        nonlocal _instance
        if _instance is None:
            with _lock:
                if _instance is None:
                    _instance = cls.__new_original__(cls_)  # type: ignore
        return _instance

    cls.__new__ = classmethod(_new)
    return cls


def reset_singleton(factory: Callable) -> None:
    """重置单例实例（仅用于测试）"""
    if hasattr(factory, "_singleton_instance"):
        with getattr(factory, "_singleton_lock", threading.Lock()):
            object.__setattr__(factory, "_singleton_instance", None)

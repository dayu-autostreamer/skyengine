"""
@Project ：tiangong 
@File    ：dc_helper.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/20 23:11 
"""

from typing import Any, Optional, List
from diskcache import Cache
import config


class DiskCacheHelper:
    def __init__(self, cache_dir: str = config.CACHE_DIR, expire: Optional[int] = None):
        """
        初始化缓存工具
        :param cache_dir: 缓存目录，默认 ./cache
        :param expire: 默认过期时间（秒），None 表示不过期
        """
        self.cache = Cache(cache_dir)
        self.expire = expire

    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        新增/更新缓存
        :param key: 缓存键
        :param value: 缓存值
        :param expire: 过期时间（秒）
        :return: 是否成功
        """
        return self.cache.set(key, value, expire=expire or self.expire)

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存
        :param key: 缓存键
        :param default: 缓存不存在时返回的默认值
        :return: 缓存值或 default
        """
        return self.cache.get(key, default)

    def delete(self, key: str) -> bool:
        """
        删除缓存
        :param key: 缓存键
        :return: 是否成功删除
        """
        return self.cache.delete(key)

    def exists(self, key: str) -> bool:
        """
        判断键是否存在
        """
        return key in self.cache

    def keys(self) -> List[str]:
        """
        获取所有键
        """
        return list(self.cache.iterkeys())

    def clear(self) -> None:
        """
        清空所有缓存
        """
        self.cache.clear()

    def close(self) -> None:
        """
        关闭缓存（释放资源）
        """
        self.cache.close()

    def append_to_list(self, key: str, value: Any, time, max_length: int = 100, expire: Optional[int] = None):
        """
        向缓存中的 list 追加数据
        :param key: 缓存键
        :param value: 新增数据
        :param max_length: list 最大长度，超过后丢弃最早的数据
        :param expire: 过期时间（秒）
        """
        data = self.get(key, [])
        if not isinstance(data, list):
            data = []
        data.append({"ts": time, "value": value})
        if len(data) > max_length:
            data = data[-max_length:]  # 只保留最新 N 条
        self.set(key, data, expire=expire or self.expire)
        return True

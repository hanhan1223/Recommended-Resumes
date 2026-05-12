"""
缓存管理模块
减少重复计算，提高系统性能
"""

import json
import hashlib
from pathlib import Path
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import os


class CacheManager:
    """缓存管理器"""

    def __init__(self, cache_dir: str = None, default_ttl: int = 3600):
        """
        初始化缓存管理器

        Args:
            cache_dir: 缓存目录路径
            default_ttl: 默认缓存有效期（秒），默认1小时
        """
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / "temp" / "cache"
        else:
            cache_dir = Path(cache_dir)

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self._memory_cache: Dict[str, tuple] = {}  # 内存缓存: {key: (value, expiry_time)}

    def _get_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """
        生成缓存键
        """
        # 创建唯一键
        key_data = {
            'prefix': prefix,
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return f"{prefix}_{hashlib.md5(key_str.encode()).hexdigest()}"

    def _get_cache_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.json"

    def get(self, prefix: str, *args, **kwargs) -> Optional[Any]:
        """
        获取缓存值

        Args:
            prefix: 缓存前缀
            *args, **kwargs: 用于生成缓存键的参数

        Returns:
            缓存值，如果不存在或已过期返回None
        """
        cache_key = self._get_cache_key(prefix, *args, **kwargs)

        # 先检查内存缓存
        if cache_key in self._memory_cache:
            value, expiry = self._memory_cache[cache_key]
            if datetime.now() < expiry:
                print(f"[CACHE] 命中内存缓存: {prefix}")
                return value
            else:
                del self._memory_cache[cache_key]

        # 检查文件缓存
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                expiry_time = datetime.fromisoformat(cache_data['expiry'])
                if datetime.now() < expiry_time:
                    # 更新内存缓存
                    value = cache_data['data']
                    self._memory_cache[cache_key] = (value, expiry_time)
                    print(f"[CACHE] 命中文件缓存: {prefix}")
                    return value
                else:
                    # 已过期，删除文件
                    cache_path.unlink()
            except Exception as e:
                print(f"[CACHE] 读取缓存失败: {e}")

        return None

    def set(self, prefix: str, value: Any, ttl: int = None, *args, **kwargs) -> bool:
        """
        设置缓存值

        Args:
            prefix: 缓存前缀
            value: 缓存值
            ttl: 缓存有效期（秒）
            *args, **kwargs: 用于生成缓存键的参数

        Returns:
            是否设置成功
        """
        if ttl is None:
            ttl = self.default_ttl

        cache_key = self._get_cache_key(prefix, *args, **kwargs)
        expiry_time = datetime.now() + timedelta(seconds=ttl)

        # 保存到内存缓存
        self._memory_cache[cache_key] = (value, expiry_time)

        # 保存到文件缓存
        cache_path = self._get_cache_path(cache_key)
        try:
            cache_data = {
                'data': value,
                'created': datetime.now().isoformat(),
                'expiry': expiry_time.isoformat(),
                'key': cache_key
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            print(f"[CACHE] 设置缓存成功: {prefix}")
            return True
        except Exception as e:
            print(f"[CACHE] 保存缓存失败: {e}")
            return False

    def invalidate(self, prefix: str, *args, **kwargs) -> bool:
        """
        使缓存失效

        Args:
            prefix: 缓存前缀
            *args, **kwargs: 用于生成缓存键的参数
        """
        cache_key = self._get_cache_key(prefix, *args, **kwargs)

        # 删除内存缓存
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]

        # 删除文件缓存
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            cache_path.unlink()
            print(f"[CACHE] 已失效缓存: {prefix}")
            return True

        return False

    def invalidate_prefix(self, prefix: str) -> int:
        """
        使指定前缀的所有缓存失效

        Args:
            prefix: 缓存前缀

        Returns:
            删除的缓存数量
        """
        count = 0

        # 清理内存缓存
        keys_to_delete = [k for k in self._memory_cache.keys() if k.startswith(prefix)]
        for k in keys_to_delete:
            del self._memory_cache[k]
            count += 1

        # 清理文件缓存
        for cache_file in self.cache_dir.glob(f"{prefix}_*.json"):
            cache_file.unlink()
            count += 1

        if count > 0:
            print(f"[CACHE] 已失效 {count} 个缓存: {prefix}*")

        return count

    def clear_all(self) -> int:
        """
        清空所有缓存

        Returns:
            删除的缓存数量
        """
        count = 0

        # 清空内存缓存
        count = len(self._memory_cache)
        self._memory_cache.clear()

        # 清空文件缓存
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1

        print(f"[CACHE] 已清空 {count} 个缓存")
        return count

    def get_cache_stats(self) -> Dict:
        """
        获取缓存统计信息
        """
        memory_count = len(self._memory_cache)
        file_count = len(list(self.cache_dir.glob("*.json")))

        return {
            'memory_cache_count': memory_count,
            'file_cache_count': file_count,
            'total_count': memory_count + file_count,
            'cache_dir': str(self.cache_dir)
        }


# 全局缓存实例
_global_cache: Optional[CacheManager] = None


def get_cache_manager(cache_dir: str = None) -> CacheManager:
    """获取全局缓存管理器实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheManager(cache_dir)
    return _global_cache


def cached(prefix: str, ttl: int = 3600):
    """
    缓存装饰器

    Args:
        prefix: 缓存前缀
        ttl: 缓存有效期（秒）

    Usage:
        @cached("user_data", ttl=1800)
        def get_user_data(user_id):
            return fetch_from_db(user_id)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache = get_cache_manager()

            # 尝试获取缓存
            cached_value = cache.get(prefix, *args, **kwargs)
            if cached_value is not None:
                return cached_value

            # 执行函数
            result = func(*args, **kwargs)

            # 保存缓存
            cache.set(prefix, result, ttl, *args, **kwargs)

            return result

        return wrapper
    return decorator

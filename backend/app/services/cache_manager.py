import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from ..core.logging import logger

class CacheManager:
    """In-memory cache manager with TTL support"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cleanup_task = None
        
    async def start(self):
        """Start cache cleanup task"""
        self._cleanup_task = asyncio.create_task(self._cleanup_expired())
        
    async def stop(self):
        """Stop cache cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now() < entry['expires']:
                return entry['data']
            else:
                del self._cache[key]
        return None
        
    async def set(self, key: str, data: Any, ttl: int = 30):
        """Set cached value with TTL in seconds"""
        self._cache[key] = {
            'data': data,
            'expires': datetime.now() + timedelta(seconds=ttl)
        }
        
    async def get_or_fetch(self, key: str, fetch_func: Callable, ttl: int = 30) -> Any:
        """Get from cache or fetch and cache"""
        cached = await self.get(key)
        if cached is not None:
            return cached
            
        data = await fetch_func()
        if data is not None:
            await self.set(key, data, ttl)
        return data
        
    async def _cleanup_expired(self):
        """Background task to cleanup expired entries"""
        while True:
            try:
                now = datetime.now()
                expired_keys = [
                    key for key, entry in self._cache.items()
                    if now >= entry['expires']
                ]
                for key in expired_keys:
                    del self._cache[key]
                    
                await asyncio.sleep(60)  # Cleanup every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(60)

# Global cache instance
cache_manager = CacheManager()
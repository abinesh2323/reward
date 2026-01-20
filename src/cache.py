

import json
import time
from typing import Optional, Any, Dict
from abc import ABC, abstractmethod


class CacheBackend(ABC):
    """Abstract cache backend."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass
    
    @abstractmethod
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment numeric value."""
        pass


class InMemoryCache(CacheBackend):
    """Simple in-memory cache with TTL support."""
    
    def __init__(self):
        """Initialize in-memory cache."""
        self._data: Dict[str, tuple[Any, Optional[float]]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._data:
            return None
        
        value, expiry = self._data[key]
        
        # Check if expired
        if expiry is not None and time.time() > expiry:
            del self._data[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        expiry = None
        if ttl is not None:
            expiry = time.time() + ttl
        self._data[key] = (value, expiry)
        return True
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if key in self._data:
            del self._data[key]
            return True
        return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if key not in self._data:
            return False
        
        value, expiry = self._data[key]
        
        # Check if expired
        if expiry is not None and time.time() > expiry:
            del self._data[key]
            return False
        
        return True
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment numeric value."""
        current = self.get(key)
        if current is None:
            current = 0
        
        new_value = current + amount
        self._data[key] = (new_value, self._data.get(key, (None, None))[1])
        return new_value


class RedisCache(CacheBackend):
    """Redis-based cache backend."""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        """Initialize Redis cache."""
        try:
            import redis
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )
            # Test connection
            self.redis_client.ping()
            self.available = True
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            self.available = False
            self.redis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.available:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
            # Try to parse as JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            print(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        if not self.available:
            return False
        
        try:
            # Serialize to JSON
            if not isinstance(value, (str, int, float)):
                value = json.dumps(value)
            
            if ttl is not None:
                self.redis_client.setex(key, ttl, value)
            else:
                self.redis_client.set(key, value)
            return True
        except Exception as e:
            print(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.available:
            return False
        
        try:
            return self.redis_client.delete(key) > 0
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.available:
            return False
        
        try:
            return self.redis_client.exists(key) > 0
        except Exception as e:
            print(f"Redis exists error: {e}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment numeric value."""
        if not self.available:
            return 0
        
        try:
            return self.redis_client.incrby(key, amount)
        except Exception as e:
            print(f"Redis increment error: {e}")
            return 0


class Cache:
    """Cache factory with Redis fallback to in-memory."""
    
    def __init__(self, use_redis: bool = False, host: str = "localhost", 
                 port: int = 6379, db: int = 0):
        """Initialize cache with Redis or in-memory backend."""
        if use_redis:
            redis_cache = RedisCache(host=host, port=port, db=db)
            if redis_cache.available:
                self._backend = redis_cache
            else:
                print("Redis unavailable, falling back to in-memory cache")
                self._backend = InMemoryCache()
        else:
            self._backend = InMemoryCache()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return self._backend.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        return self._backend.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        return self._backend.delete(key)
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return self._backend.exists(key)
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment numeric value."""
        return self._backend.increment(key, amount)


# Global cache instance
_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """Get or create the global cache instance."""
    global _cache
    if _cache is None:
        from src.config import Settings
        settings = Settings()
        _cache = Cache(
            use_redis=settings.use_redis,
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db
        )
    return _cache

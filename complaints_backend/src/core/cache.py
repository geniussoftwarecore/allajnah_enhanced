# type: ignore
import os
import json
from datetime import datetime, timedelta

try:
    from redis import Redis
    redis_url = os.environ.get('REDIS_URL', '')
    if redis_url:
        redis_client = Redis.from_url(redis_url)
        redis_client.ping()
        use_redis = True
    else:
        use_redis = False
        redis_client = None
except:
    use_redis = False
    redis_client = None

_memory_cache = {}

def cache_get(key):
    """Get value from cache"""
    if use_redis and redis_client:
        try:
            value = redis_client.get(key)
            if value:
                return json.loads(value)
        except:
            pass
    
    if key in _memory_cache:
        item = _memory_cache[key]
        if item['expires_at'] > datetime.utcnow():
            return item['value']
        else:
            del _memory_cache[key]
    
    return None

def cache_set(key, value, timeout=3600):
    """Set value in cache with timeout in seconds"""
    if use_redis and redis_client:
        try:
            redis_client.setex(key, timeout, json.dumps(value))
        except:
            pass
    
    _memory_cache[key] = {
        'value': value,
        'expires_at': datetime.utcnow() + timedelta(seconds=timeout)
    }

def cache_clear_pattern(pattern):
    """Clear cache keys matching pattern"""
    cleared = 0
    
    if use_redis and redis_client:
        try:
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
                cleared = len(keys)
        except:
            pass
    
    if pattern.endswith('*'):
        prefix = pattern[:-1]
        keys_to_delete = [k for k in _memory_cache.keys() if k.startswith(prefix)]
        for key in keys_to_delete:
            del _memory_cache[key]
        cleared = max(cleared, len(keys_to_delete))
    
    return cleared

def invalidate_cache_key(key):
    """Delete a specific cache key"""
    if use_redis and redis_client:
        try:
            redis_client.delete(key)
        except:
            pass
    
    if key in _memory_cache:
        del _memory_cache[key]

def invalidate_cache_pattern(pattern):
    """Alias for cache_clear_pattern"""
    return cache_clear_pattern(pattern)

import json
import os
from functools import wraps
import asyncio
from typing import Any, Callable

CACHE_FILE = 'query_cache.json'

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, default=make_serializable)

persistent_cache = load_cache()

def persistent_cache_decorator(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args, **kwargs):
        key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
        
        if key in persistent_cache:
            print(f"Cache hit for {key}")
            return persistent_cache[key]
        
        result = await func(*args, **kwargs)
        persistent_cache[key] = result
        save_cache(persistent_cache)
        return result
        
    return wrapper

def memory_cache_decorator(func: Callable) -> Any:
    cache = {}
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
        if key not in cache:
            cache[key] = await func(*args, **kwargs)
        return cache[key]
    
    return wrapper

def clear_persistent_cache():
    global persistent_cache
    persistent_cache.clear()
    save_cache(persistent_cache)

def clear_memory_cache():
    print("Memory cache clearing is not fully implemented. You may need to restart the application.")

def make_serializable(obj):
    if asyncio.iscoroutine(obj):
        return "coroutine"
    elif callable(obj):
        return "function"
    elif isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    else:
        return obj

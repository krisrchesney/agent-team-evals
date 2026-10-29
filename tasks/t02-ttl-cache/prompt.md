`cachekit.lru.LRUCache` is a working least-recently-used cache. Add optional time-based expiry:

1. `LRUCache(capacity, ttl=None, clock=time.monotonic)`. `ttl` is seconds (float) or `None` for no expiry.
   `clock` is a zero-argument callable returning the current time; tests inject a fake clock.
2. An entry expires when `clock() - time_it_was_set >= ttl`. Expired entries behave as if absent:
   `get()` returns the default, `key in cache` is False, and `len(cache)` does not count them.
3. `set(key, value, ttl=...)` accepts a per-entry `ttl` that overrides the cache default for that
   entry (`ttl=None` there means "never expires"). Setting an existing key resets its timer.
4. `get()` on a live entry does NOT extend its lifetime (it still refreshes LRU order).
5. When inserting into a full cache, evict expired entries first; only evict the least-recently-used
   live entry if the cache is still full.
6. New method `purge_expired() -> int` removes all expired entries and returns how many it removed.
7. Existing behaviour without `ttl` must not change. Keep `capacity` validation as it is.

Standard library only. Existing tests are in `tests/`.

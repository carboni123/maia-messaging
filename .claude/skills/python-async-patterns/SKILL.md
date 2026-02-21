---
name: python-async-patterns
description: >
  Async Python patterns and best practices for building high-performance, non-blocking systems
  with asyncio. Use when: (1) writing or reviewing async Python code, (2) implementing concurrent
  I/O operations (database, HTTP, file), (3) building async web APIs (FastAPI, aiohttp, Litestar),
  (4) creating real-time applications (WebSockets, chat), (5) orchestrating microservices with
  scatter-gather patterns, (6) debugging async hangs, deadlocks, or performance issues,
  (7) bridging sync and async code, (8) implementing rate limiting or background tasks.
  Triggers: "async", "await", "asyncio", "concurrent", "non-blocking", "event loop",
  "TaskGroup", "semaphore", "to_thread", "send_async", "async patterns".
---

# Async Python Patterns (Python 3.11+)

## Sync vs Async Decision

| Workload | Example | Approach |
|:--|:--|:--|
| I/O-bound, high concurrency | Web API, scraper | `asyncio` |
| CPU-bound | Image processing, ML | `multiprocessing` |
| Mixed I/O + CPU | DB fetch + heavy math | `asyncio.to_thread()` for CPU |
| Simple / low concurrency | CLI scripts, cron | Sync |

## Core Patterns

### TaskGroup (replaces `gather`)

```python
async with asyncio.TaskGroup() as tg:
    tasks = [tg.create_task(fetch(uid)) for uid in user_ids]
results = [t.result() for t in tasks]
```

All tasks complete or all cancel on first failure. Strict concurrency boundary.

### Timeouts

```python
async with asyncio.timeout(2.0):
    result = await slow_operation()  # TimeoutError if > 2s
```

### Semaphore Rate Limiting

```python
sem = asyncio.Semaphore(3)  # Max 3 concurrent

async def api_call(url: str):
    async with sem:
        return await client.get(url)

async with asyncio.TaskGroup() as tg:
    tasks = [tg.create_task(api_call(url)) for url in urls]
```

### Bridge Sync to Async

Never block the event loop. Offload sync/blocking code to a thread:

```python
result = await asyncio.to_thread(blocking_sync_function, arg1, arg2)
```

### Fire-and-Forget (Safe)

```python
background_tasks = set()  # Strong reference prevents GC

task = asyncio.create_task(track_analytics("login"))
background_tasks.add(task)
task.add_done_callback(background_tasks.discard)
```

### Context Variables (async thread-locals)

```python
import contextvars
request_id = contextvars.ContextVar("request_id", default="UNKNOWN")

async def handle_request():
    token = request_id.set(str(uuid4())[:8])
    try:
        await process()  # request_id.get() works in nested calls
    finally:
        request_id.reset(token)
```

### Eager Task Factory (3.12+ optimization)

```python
loop = asyncio.get_running_loop()
loop.set_task_factory(asyncio.eager_task_factory)
```

Coroutines that return without suspending (cache hits) execute synchronously, skipping loop scheduling overhead. 20-30% boost in high-throughput apps.

## Anti-Patterns

**Blocking the loop** -- Use `httpx.AsyncClient` or `aiohttp`, never sync `requests` or `time.sleep` in async code. Use `asyncio.to_thread()` for unavoidable sync calls.

**Unawaited coroutines** -- `do_work()` returns a coroutine object but doesn't run it. Always `await do_work()`.

**Unbounded concurrency** -- 10,000 simultaneous `create_task` calls exhaust file descriptors and memory. Always use `Semaphore` or chunking.

**Lost background tasks** -- `asyncio.create_task()` without saving a reference lets GC destroy the task mid-execution. Always keep a strong reference.

## Testing

```python
# With asyncio_mode=auto in pytest.ini:
async def test_concurrent_fetch():
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(fetch("a"))
        t2 = tg.create_task(fetch("b"))
    assert t1.result()["status"] == "ok"

async def test_timeout():
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.01):
            await asyncio.sleep(1)
```

For detailed patterns, examples, and Python 3.13-specific features, see [references/advanced-patterns.md](references/advanced-patterns.md).

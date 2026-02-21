# Advanced Async Python Patterns

## Table of Contents

- [Runner API](#runner-api)
- [Eager Task Execution Details](#eager-task-execution-details)
- [Producer-Consumer with Queues](#producer-consumer-with-queues)
- [Graceful Shutdown](#graceful-shutdown)
- [Async Generators](#async-generators)
- [Async Context Managers for Resources](#async-context-managers-for-resources)
- [Structured Concurrency Patterns](#structured-concurrency-patterns)
- [httpx AsyncClient Patterns](#httpx-asyncclient-patterns)
- [Database Connection Pooling](#database-connection-pooling)
- [Free-Threaded Python 3.13](#free-threaded-python-313)

---

## Runner API

`asyncio.Runner` (3.11+) gives granular control over the event loop lifecycle. Useful for test suites or CLI apps that run multiple async operations sequentially.

```python
with asyncio.Runner() as runner:
    res1 = runner.run(fetch("https://api.example.com/1"))
    res2 = runner.run(fetch("https://api.example.com/2"))
    # Same loop reused across calls, context preserved
```

## Eager Task Execution Details

When `eager_task_factory` is enabled, `create_task()` runs the coroutine synchronously until its first `await`. If the coroutine completes without suspending (e.g., cache hit, validation failure), no event loop scheduling occurs at all.

```python
async def get_user(user_id: int, cache: dict):
    if user_id in cache:
        return cache[user_id]  # Returns immediately, never suspends
    await db.fetch(user_id)    # Suspends here on cache miss

async def main():
    loop = asyncio.get_running_loop()
    loop.set_task_factory(asyncio.eager_task_factory)

    cache = {1: "Cached User 1"}
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(get_user(1, cache))  # Synchronous, no scheduling
        t2 = tg.create_task(get_user(2, cache))  # Suspends, scheduled normally
```

Best for: High-throughput apps where many coroutines return without I/O (caches, validations, early returns).

## Producer-Consumer with Queues

```python
async def producer(queue: asyncio.Queue, items: list):
    for item in items:
        await queue.put(item)
    await queue.put(None)  # Sentinel

async def consumer(queue: asyncio.Queue, worker_id: int):
    while True:
        item = await queue.get()
        if item is None:
            queue.task_done()
            break
        await process(item)
        queue.task_done()

async def main():
    queue: asyncio.Queue = asyncio.Queue(maxsize=10)
    async with asyncio.TaskGroup() as tg:
        tg.create_task(producer(queue, data))
        for i in range(3):
            tg.create_task(consumer(queue, i))
```

`maxsize` creates backpressure -- producer blocks when queue is full.

## Graceful Shutdown

```python
async def main():
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(server(stop_event))
        tg.create_task(background_worker(stop_event))
    # All tasks clean up when stop_event is set
```

## Async Generators

```python
async def paginate(url: str):
    page = 1
    while True:
        data = await fetch_page(url, page)
        if not data["results"]:
            return
        for item in data["results"]:
            yield item
        page += 1

async def main():
    async for user in paginate("/api/users"):
        print(user["name"])
```

## Async Context Managers for Resources

```python
class DatabasePool:
    async def __aenter__(self):
        self.pool = await asyncpg.create_pool(dsn="postgres://...")
        return self.pool

    async def __aexit__(self, *args):
        await self.pool.close()

async def main():
    async with DatabasePool() as pool:
        async with pool.acquire() as conn:
            result = await conn.fetch("SELECT * FROM users")
```

## Structured Concurrency Patterns

### Fan-out / Fan-in (Scatter-Gather)

```python
async def scatter_gather(urls: list[str]) -> list[dict]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch(url)) for url in urls]
    return [t.result() for t in tasks]
```

### Pipeline stages

```python
async def pipeline(raw_items: list):
    q1: asyncio.Queue = asyncio.Queue()
    q2: asyncio.Queue = asyncio.Queue()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(stage_fetch(raw_items, q1))
        tg.create_task(stage_transform(q1, q2))
        tg.create_task(stage_save(q2))
```

### Retry with exponential backoff

```python
async def retry(coro_fn, *, max_attempts=3, base_delay=1.0):
    for attempt in range(max_attempts):
        try:
            return await coro_fn()
        except Exception:
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(base_delay * (2 ** attempt))
```

## httpx AsyncClient Patterns

### Reusable client with connection pooling

```python
async def main():
    async with httpx.AsyncClient(
        timeout=10.0,
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    ) as client:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(client.get(url)) for url in urls]
```

### Rate-limited client wrapper

```python
class RateLimitedClient:
    def __init__(self, client: httpx.AsyncClient, max_concurrent: int = 5):
        self._client = client
        self._sem = asyncio.Semaphore(max_concurrent)

    async def get(self, url: str) -> httpx.Response:
        async with self._sem:
            return await self._client.get(url)
```

## Database Connection Pooling

```python
# asyncpg
pool = await asyncpg.create_pool(dsn, min_size=5, max_size=20)
async with pool.acquire() as conn:
    rows = await conn.fetch("SELECT * FROM users WHERE active = $1", True)

# SQLAlchemy async
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
engine = create_async_engine("postgresql+asyncpg://...", pool_size=20)
async with AsyncSession(engine) as session:
    result = await session.execute(select(User).where(User.active == True))
```

## Free-Threaded Python 3.13

The experimental No-GIL build changes the `asyncio.to_thread()` story significantly:

- Standard CPython: `to_thread()` offloads blocking I/O to a thread, but CPU-bound work still contends with the GIL
- Free-threaded build: `to_thread()` achieves true parallelism for CPU-bound work

```python
# On free-threaded 3.13, these run in true parallel:
async with asyncio.TaskGroup() as tg:
    tg.create_task(asyncio.to_thread(cpu_heavy_task_1, data1))
    tg.create_task(asyncio.to_thread(cpu_heavy_task_2, data2))
    tg.create_task(fetch_from_api())  # I/O runs concurrently too
```

This is experimental. For production, continue using `multiprocessing` for CPU-bound parallelism unless you've validated the free-threaded build for your use case.

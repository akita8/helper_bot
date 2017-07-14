import asyncio

import pytest
import redis
import aioredis

from aiotg.mock import MockBot


@pytest.fixture
def bot():
    return MockBot()


@pytest.fixture
def redis_async(request, event_loop):
    conn = event_loop.run_until_complete(aioredis.create_redis(('localhost', 6379), encoding="utf-8", db=10))

    def redis_async_cleanup():
        conn.close()
    request.addfinalizer(redis_async_cleanup)
    return conn


@pytest.fixture(scope='session')
def redis_sync(request):
    conn = redis.Redis(decode_responses=True, db=10)

    def redis_sync_cleanup():
        conn.flushdb()
    request.addfinalizer(redis_sync_cleanup)
    return conn
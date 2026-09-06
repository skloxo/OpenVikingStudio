import pytest

from openviking.server.identity import RequestContext, Role
from openviking.service.search_service import SearchService
from openviking_cli.session.user_id import UserIdentifier


@pytest.mark.asyncio
async def test_search_service_find_cache():
    class CountingFS:
        def __init__(self):
            self.call_count = 0

        async def find(self, **kwargs):
            self.call_count += 1
            return [{"uri": "viking://test", "score": 0.9}]

    fs = CountingFS()
    service = SearchService(fs)
    ctx = RequestContext(user=UserIdentifier("acc", "user"), role=Role.USER)

    # 1. First call: cache miss, calls fs.find
    res1 = await service.find(query="hello", ctx=ctx)
    assert fs.call_count == 1
    assert res1 == [{"uri": "viking://test", "score": 0.9}]

    # 2. Second call with identical query: cache hit, does not call fs.find
    res2 = await service.find(query="hello", ctx=ctx)
    assert fs.call_count == 1
    assert res2 == [{"uri": "viking://test", "score": 0.9}]

    # 3. Third call with different query: cache miss, calls fs.find
    res3 = await service.find(query="world", ctx=ctx)
    assert fs.call_count == 2
    assert res3 == [{"uri": "viking://test", "score": 0.9}]

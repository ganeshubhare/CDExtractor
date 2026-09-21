import asyncio
from datetime import datetime, timezone
from dap.api import DAPClient
from dap.dap_types import IncrementalQuery, Format


async def test_incremental():
    async with DAPClient() as session:

        query = IncrementalQuery(
            since=datetime(2026, 4, 21, 8, 11, 45, tzinfo=timezone.utc),
            until=None,
            mode=None,
            format=Format.JSONL
        )
        result = await session.get_table_data("canvas", "accounts", query)
        print(result)

asyncio.run(test_incremental())

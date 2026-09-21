import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import aiofiles

from dap.api import DAPClient
from dap.dap_types import SnapshotQuery, IncrementalQuery, Format
from dap.replicator.sql import SQLReplicator
from dap.integration.database import DatabaseConnection

# ---------------------------------------------------------
# Stream and save DAP resource
# ---------------------------------------------------------
async def save_resource(session, resource, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = os.path.basename(urlparse(str(resource.url)).path)
    dest = out_dir / filename

    async for stream in session.stream_resource(resource):
        async with aiofiles.open(dest, "wb") as f:
            async for chunk in stream.iter_chunked(64 * 1024):
                await f.write(chunk)

    logging.info(f"Downloaded: {dest}")
    return dest


# ---------------------------------------------------------
# SNAPSHOT (run once per table)
# ---------------------------------------------------------
async def run_snapshot(session, dataset, table, out_dir: Path):
    logging.info(f"Running snapshot for {dataset}.{table}...")

    query = SnapshotQuery(format=Format.JSONL, mode=None)
    result = await session.get_table_data(dataset, table, query)
    resources = await session.get_resources(result.objects)

    for r in resources.values():
        await save_resource(session, r, out_dir)

    logging.info(f"Snapshot completed for {dataset}.{table}")


# ---------------------------------------------------------
# INCREMENTAL (daily/recurring)
# ---------------------------------------------------------
async def run_incremental(session, dataset, table, since_timestamp, out_dir: Path):
    logging.info(f"Running incremental for {dataset}.{table} since {since_timestamp.isoformat()}")

    query = IncrementalQuery(
        format=Format.JSONL,
        mode=None,
        since=since_timestamp,
        until=None
    )
    result = await session.get_table_data(dataset, table, query)
    resources = await session.get_resources(result.objects)

    for r in resources.values():
        await save_resource(session, r, out_dir)

    next_since = getattr(result, "until", datetime.now(timezone.utc))
    logging.info(f"Incremental complete for {dataset}.{table}. NEXT SINCE={next_since.isoformat()}")
    return next_since


# ---------------------------------------------------------
# AUTO initialize or synchronize the SQL table
# ---------------------------------------------------------
async def auto_replicate(session, db_conn: DatabaseConnection, dataset, table):
    replicator = SQLReplicator(session, db_conn)
    await replicator.version_upgrade()

    try:
        logging.info(f"Initializing replication for {dataset}.{table}")
        await replicator.initialize(dataset, table)
        logging.info(f"Initialization complete for {dataset}.{table}")
    except ValueError as e:
        if "Table already initialized" in str(e):
            logging.info(f"Table already initialized — synchronizing instead: {dataset}.{table}")
            await replicator.synchronize(dataset, table)
            logging.info(f"Synchronization complete for {dataset}.{table}")
        else:
            raise
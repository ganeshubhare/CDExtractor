import json
import sys
from pathlib import Path
from logging_setup import configure_cd2_logging
from file_cleanup import cleanup_old_files
import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine, text

from dap.api import DAPClient
from dap.integration.database import DatabaseConnection, DatabaseConnectionConfig
from dap.replicator.sql import SQLReplicator

from etl_extract import (
    run_snapshot,
    run_incremental,
    auto_replicate
) 

from db_connector import DatabaseConnector



# ---------------------------------------------------------
# Load tables.json
# ---------------------------------------------------------
def load_table_list(path="config/tables.json"):
    with open(path, "r") as f:
        return json.load(f)


async def process_table(dataset: str, table_name: str):
    logging.info(f"Processing {dataset}.{table_name}")

    # 1. READ SECRETS MANUALLY (Exactly like Testdb.py)
    # This ensures we have the correct credentials for our manual check
    secrets_path = "config/secrets.json"
    try:
        with open(secrets_path, "r") as f:
            secrets = json.load(f)
        
        user = secrets.get("DAP_DB_USERNAME")
        pwd = secrets.get("DAP_DB_PASSWORD")
        host = secrets.get("DAP_DB_HOST")
        db = secrets.get("DAP_DB_DATABASE")
        
        if not all([user, pwd, host, db]):
            logging.critical(f"FATAL: Missing keys in {secrets_path}")
            sys.exit(1)
            
        db_url = f"mssql+pyodbc://{user}:{pwd}@{host}:1433/{db}?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes"
    except Exception as e:
        logging.critical(f"FATAL: Failed to load secrets for manual check: {e}")
        sys.exit(1)

    # 2. THE GATEKEEPER CHECK (The Testdb.py logic)
    exists = False
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            check_sql = text("""
                SELECT 1 FROM instructure_dap.table_sync 
                WHERE source_table = :t AND source_namespace = :ns
            """)
            result = conn.execute(check_sql, {"t": table_name, "ns": dataset}).fetchone()
            if result:
                exists = True
        engine.dispose()
    except Exception as e:
        logging.critical(f"FATAL: Database connectivity check failed: {e}")
        sys.exit(1)

    # 3. INITIALIZE LIBRARY AND EXECUTE
    # Now we use the library for the actual work
    connector = DatabaseConnector.from_secrets(secrets_path)
    db_conn = connector.create_connection()
    
    async with DAPClient() as session:
        replicator = SQLReplicator(session, db_conn)
        await replicator.version_upgrade()

        if exists:
            logging.info(f"Table {table_name} confirmed in table_sync. Syncing...")
            try:
                await replicator.synchronize(dataset, table_name)
            except Exception as e:
                logging.error(f"Sync failed for {table_name}: {e}")
                # We don't sys.exit here so the loop can move to the next table
        else:
            logging.info(f"Table {table_name} not found in metadata. Running Initial Load.")
            out_dir = Path(f"E:/CD2SQL/{dataset}/{table_name}")
            out_dir.mkdir(parents=True, exist_ok=True)
            try:
                await run_snapshot(session, dataset, table_name, out_dir)
                await replicator.initialize(dataset, table_name)
            except Exception as e:
                logging.error(f"Initialization failed for {table_name}: {e}")




# ---------------------------------------------------------
# Main entry point
# ---------------------------------------------------------
async def main():
    # Start logging
    configure_cd2_logging()
    logging.info("===== CD2 DAP ETL RUN STARTED =====")

    # Load tables
    table_list = load_table_list()
    logging.info(f"Loaded {len(table_list)} tables from tables.json")

    # Loop
    for entry in table_list:
        dataset = entry["dataset"]
        table = entry["table"]

        logging.info(f"--- Starting ETL for {dataset}.{table} ---")
        try:
            await process_table(dataset, table)
            logging.info(f"✔ Completed {dataset}.{table}")
        except Exception as e:
            logging.error(f"❌ ERROR processing {dataset}.{table}: {e}", exc_info=True)

    


# Cleanup old files (e.g., older than 7 days)
cleanup_old_files("E:/CD2SQL", days=7)
logging.info("===== CD2 DAP ETL RUN COMPLETE =====")


# ---------------------------------------------------------
# Allow command-line execution
# ---------------------------------------------------------
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
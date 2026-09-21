import sys
import json
import logging
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def test_connection_from_secrets():
    # 1. Load the same secrets your main script uses
    try:
        with open("config/secrets.json", "r") as f:
            secrets = json.load(f)
    except Exception as e:
        logging.error(f"Could not read secrets.json: {e}")
        return

    # 2. Map the secrets to the connection string
    # We use the 'Database' secret for the DB name and 'Password' for the pass
    user = secrets.get("DAP_DB_USERNAME")
    pwd = secrets.get("DAP_DB_PASSWORD")
    host = secrets.get("DAP_DB_HOST", "wea-sql-ebs-02")
    db = secrets.get("DAP_DB_DATABASE", "WeaCd2")

    logging.info(f"Attempting connection as {user} to {host}/{db}...")

    # Connection string for SQL Server 
    db_url = f"mssql+pyodbc://{user}:{pwd}@{host}:1433/{db}?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes"
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Test query
            query = text("SELECT TOP 1 source_table FROM instructure_dap.table_sync")
            result = conn.execute(query).fetchone()
            
            if result:
                logging.info(f"SUCCESS! Found table entry: {result[0]}")
            else:
                logging.warning("SUCCESS! Connected, but table_sync is empty.")
                
        engine.dispose()
    except Exception as e:
        logging.error(f"Connection failed again: {e}")

if __name__ == "__main__":
    test_connection_from_secrets()
import json
from pathlib import Path
from dap.integration.database import (
    DatabaseConnection,
    DatabaseConnectionConfig
)

class DatabaseConnector:

    @classmethod
    def from_secrets(cls, secrets_path="config/secrets.json"):
        secrets_file = Path(secrets_path)
        with secrets_file.open("r") as f:
            secrets = json.load(f)

        cfg = DatabaseConnectionConfig(
            dialect=secrets["DAP_DB_DIALECT"],
            host=secrets["DAP_DB_HOST"],
            port=int(secrets["DAP_DB_PORT"]),
            username=secrets["DAP_DB_USERNAME"],
            password=secrets["DAP_DB_PASSWORD"],
            database=secrets["DAP_DB_DATABASE"],
        )
        return cls(cfg)

    def __init__(self, config: DatabaseConnectionConfig):
        self._config = config

    def create_connection(self):
        # Build a connection string for pysqlsync
        conn_str = (
            f"{self._config.dialect}://"
            f"{self._config.username}:{self._config.password}"
            f"@{self._config.host}:{self._config.port}/"
            f"{self._config.database}"
        )
        return DatabaseConnection(conn_str)

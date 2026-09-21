import logging
from pathlib import Path

def configure_cd2_logging():
    # Ensure logs directory exists
    base_dir = Path(__file__).resolve().parent.parent
    log_dir = base_dir / "logs"
    log_dir.mkdir(exist_ok=True)


    logging.basicConfig(
        filename=log_dir / "cd2dap_etl.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        force=True
    )


    # Also log to console (optional but useful during testing)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(console)

    logging.info("Logging initialized. Writing to logs/cd2dap_etl.log")
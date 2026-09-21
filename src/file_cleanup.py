import os
import logging
from pathlib import Path
from datetime import datetime, timedelta

def cleanup_old_files(base_dir: str, days: int = 7):
    """
    Deletes files older than X days under the data directory.
    """

    data_root = Path(base_dir)

    if not data_root.exists():
        logging.warning(f"Cleanup skipped — folder not found: {data_root}")
        return

    cutoff = datetime.now() - timedelta(days=days)
    removed_count = 0

    for root, dirs, files in os.walk(data_root):
        for filename in files:
            file_path = Path(root) / filename
            modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)

            if modified_time < cutoff:
                try:
                    file_path.unlink()
                    removed_count += 1
                except Exception as e:
                    ## logging.error(f"Could not delete {file_path}: {e}")
                    logging.warning(f"Skipped locked file {file_path}: {e}")
    logging.info(f"Cleanup complete — removed {removed_count} file(s) older than {days} days.")
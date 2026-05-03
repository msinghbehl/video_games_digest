import os
from datetime import datetime, timezone

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


def fetch(path: str, column_map: dict) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Metacritic CSV not found at: {path}")

    logger.info(f"Reading Metacritic CSV from {path}")
    raw = pd.read_csv(path, dtype=str)
    logger.info(f"Metacritic CSV loaded: {len(raw)} rows, columns: {list(raw.columns)}")

    rename = {v: k for k, v in column_map.items() if v in raw.columns}
    df = raw.rename(columns=rename)

    schema_cols = ["title", "platform", "critic_score", "release_date", "genre", "url"]
    for col in schema_cols:
        if col not in df.columns:
            logger.warning(f"Metacritic CSV missing expected column '{col}' — filling with None")
            df[col] = None

    df = df[schema_cols].copy()
    df["source"] = "metacritic"
    df["notes"] = None
    df["personal_rating"] = None
    df["status"] = None
    df["community_rating"] = None
    df["fetched_at"] = datetime.now(timezone.utc)

    return df

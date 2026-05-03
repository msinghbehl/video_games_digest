import hashlib
from datetime import datetime, timezone

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)

SCHEMA_COLS = [
    "id", "source", "title", "platform", "genre", "release_date",
    "critic_score", "community_rating", "personal_rating",
    "status", "notes", "url", "fetched_at",
]


def _make_id(source: str, title: str) -> str:
    key = f"{source}:{title.lower().strip()}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def normalize(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    if df.empty:
        logger.warning(f"[{source_name}] Empty DataFrame received — skipping normalization")
        return pd.DataFrame(columns=SCHEMA_COLS)

    logger.info(f"[{source_name}] Normalizing {len(df)} rows")

    df = df.copy()

    # String fields
    for col in ["title", "platform", "genre", "status", "notes", "url"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace({"None": None, "nan": None, "": None})
        else:
            df[col] = None

    # Drop rows without a title — nothing to enrich
    before = len(df)
    df = df[df["title"].notna() & (df["title"] != "")]
    dropped = before - len(df)
    if dropped:
        logger.warning(f"[{source_name}] Dropped {dropped} rows with missing title")

    # Numeric fields
    for col in ["critic_score", "community_rating", "personal_rating"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = None

    # Date field
    if "release_date" in df.columns:
        df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce").dt.date
    else:
        df["release_date"] = None

    # fetched_at
    if "fetched_at" not in df.columns:
        df["fetched_at"] = datetime.now(timezone.utc)

    # source
    df["source"] = source_name

    # Generate stable ID
    df["id"] = df.apply(lambda row: _make_id(source_name, row["title"]), axis=1)

    logger.info(f"[{source_name}] Normalization complete: {len(df)} valid rows")
    return df[SCHEMA_COLS]

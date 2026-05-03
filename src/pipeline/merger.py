import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)

SOURCE_PRIORITY = {"rawg": 0, "metacritic": 1, "games_played": 2}


def merge(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [df for df in dfs if not df.empty]
    if not non_empty:
        logger.warning("All source DataFrames are empty — nothing to merge")
        return pd.DataFrame()

    combined = pd.concat(non_empty, ignore_index=True)
    logger.info(f"Combined {len(combined)} rows from {len(non_empty)} source(s) before dedup")

    # Sort by source priority so first-occurrence dedup keeps the highest-priority source
    combined["_priority"] = combined["source"].map(SOURCE_PRIORITY).fillna(99)
    combined = combined.sort_values("_priority").drop(columns=["_priority"])

    before = len(combined)
    combined = combined.drop_duplicates(subset=["id"], keep="first")
    dupes = before - len(combined)
    if dupes:
        logger.info(f"Removed {dupes} duplicate records")

    # Sort final output: hype score descending, then release date descending
    combined["ai_hype_score"] = pd.to_numeric(combined["ai_hype_score"], errors="coerce")
    combined = combined.sort_values(
        ["ai_hype_score", "release_date"],
        ascending=[False, False],
        na_position="last",
    ).reset_index(drop=True)

    logger.info(f"Merge complete: {len(combined)} unique records")
    return combined

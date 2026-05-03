import os
import time

from dotenv import load_dotenv

load_dotenv()

from src.utils.config_loader import load_config
from src.utils.logger import get_logger
from src.sources import rawg, metacritic_csv, games_played
from src.pipeline import normalizer, enricher, merger
from src.reports import generator

logger = get_logger(__name__)

REQUIRED_ENV_VARS = ["ANTHROPIC_API_KEY", "RAWG_API_KEY", "GOOGLE_SERVICE_ACCOUNT_JSON"]


def _validate_env() -> None:
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in the values."
        )


def run() -> None:
    start = time.time()
    logger.info("FlowForge pipeline starting")

    _validate_env()
    config = load_config()
    sources_cfg = config["sources"]
    pipeline_cfg = config["pipeline"]
    max_per_source = pipeline_cfg.get("max_records_per_source", 40)

    raw_dfs = []

    # --- RAWG ---
    if sources_cfg["rawg"].get("enabled", False):
        try:
            rawg_cfg = sources_cfg["rawg"]
            df = rawg.fetch(
                ordering=rawg_cfg.get("ordering", "-rating"),
                page_size=rawg_cfg.get("page_size", 40),
            )
            df = df.head(max_per_source)
            df = normalizer.normalize(df, "rawg")
            raw_dfs.append(df)
        except Exception as e:
            logger.error(f"RAWG source failed: {e}")

    # --- Metacritic CSV ---
    if sources_cfg["metacritic_csv"].get("enabled", False):
        try:
            csv_cfg = sources_cfg["metacritic_csv"]
            df = metacritic_csv.fetch(
                path=csv_cfg["path"],
                column_map=csv_cfg.get("column_map", {}),
            )
            df = df.head(max_per_source)
            df = normalizer.normalize(df, "metacritic")
            raw_dfs.append(df)
        except Exception as e:
            logger.error(f"Metacritic CSV source failed: {e}")

    # --- Google Sheets ---
    if sources_cfg["games_played"].get("enabled", False):
        try:
            sheets_cfg = sources_cfg["games_played"]
            df = games_played.fetch(
                spreadsheet_name=sheets_cfg["spreadsheet_name"],
                sheet_tab=sheets_cfg.get("sheet_tab", "Sheet1"),
                column_map=sheets_cfg.get("column_map", {}),
            )
            df = df.head(max_per_source)
            df = normalizer.normalize(df, "games_played")
            raw_dfs.append(df)
        except Exception as e:
            logger.error(f"Google Sheets source failed: {e}")

    if not raw_dfs:
        logger.error("No data loaded from any source — aborting")
        return

    import pandas as pd
    combined = pd.concat(raw_dfs, ignore_index=True)
    logger.info(f"Total normalized records across all sources: {len(combined)}")

    enriched = enricher.enrich(combined, config)
    merged = merger.merge([enriched])
    generator.generate(merged, config)

    elapsed = round(time.time() - start, 1)
    logger.info(f"Pipeline complete in {elapsed}s")


if __name__ == "__main__":
    run()

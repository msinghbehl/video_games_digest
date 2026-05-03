import json
import os
import time

import anthropic
import pandas as pd
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from src.utils.logger import get_logger

logger = get_logger(__name__)

AI_FIELDS = ["ai_summary", "ai_genre_tags", "ai_hype_score", "ai_play_recommendation"]


def _load_prompt_template(path: str = "config/enrichment_prompt.txt") -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _validated_str(value) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    return value.strip() or None


def _validated_score(value) -> int | None:
    try:
        score = int(value)
        return score if 1 <= score <= 10 else None
    except (TypeError, ValueError):
        return None


def _safe(value) -> object:
    """Convert pandas NaN / numpy NaN to None so json.dumps produces null, not NaN."""
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _build_prompt(template: str, batch: list[dict]) -> str:
    return template.replace("{games_json}", json.dumps(batch, ensure_ascii=False, indent=2))


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(anthropic.RateLimitError),
    before_sleep=before_sleep_log(logger, 30),  # 30 = logging.WARNING
)
def _call_claude(client: anthropic.Anthropic, prompt: str, model: str, max_tokens: int) -> str:
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _parse_response(text: str, expected_ids: set) -> list[dict]:
    if not text or not text.strip():
        logger.warning("Claude returned an empty response for this batch")
        return []
    # Strip markdown code fences if the model wrapped its output
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(cleaned)
        if not isinstance(data, list):
            raise ValueError("Response is not a JSON array")
        return data
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse enrichment response: {e}")
        logger.debug(f"Raw response was: {text[:300]}")
        return []


def enrich(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    if df.empty:
        return df

    ai_cfg = config["ai"]
    pipeline_cfg = config["pipeline"]
    batch_size = pipeline_cfg.get("enrichment_batch_size", 15)
    max_records = pipeline_cfg.get("max_enrichment_records", 100)
    model = ai_cfg.get("model", "claude-sonnet-4-6")
    max_tokens = ai_cfg.get("max_tokens", 2048)

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    template = _load_prompt_template()

    df = df.copy()
    for field in AI_FIELDS:
        df[field] = None

    # Cap records to control cost
    work_df = df.head(max_records).copy()
    logger.info(f"Enriching {len(work_df)} records in batches of {batch_size}")

    enrichment_map: dict[str, dict] = {}

    for i in range(0, len(work_df), batch_size):
        batch_df = work_df.iloc[i:i + batch_size]
        batch = [
            {
                "id": row["id"],
                "title": row["title"],
                "genre": _safe(row["genre"]),
                "critic_score": _safe(row["critic_score"]),
                "community_rating": _safe(row["community_rating"]),
                "notes": _safe(row["notes"]) or "",
            }
            for _, row in batch_df.iterrows()
        ]

        prompt = _build_prompt(template, batch)
        expected_ids = {r["id"] for r in batch}

        logger.info(f"Calling Claude for batch {i // batch_size + 1} ({len(batch)} records)")
        try:
            raw_text = _call_claude(client, prompt, model, max_tokens)
            results = _parse_response(raw_text, expected_ids)
            for result in results:
                record_id = result.get("id")
                if record_id:
                    enrichment_map[record_id] = result
            missing = expected_ids - set(enrichment_map.keys())
            if missing:
                logger.warning(f"Enrichment missing for IDs: {missing}")
        except Exception as e:
            logger.warning(f"Enrichment batch failed: {e}")

        time.sleep(0.5)

    # Merge enrichment results back
    for idx, row in df.iterrows():
        result = enrichment_map.get(row["id"])
        if result:
            df.at[idx, "ai_summary"] = _validated_str(result.get("summary"))
            df.at[idx, "ai_genre_tags"] = _validated_str(result.get("genre_tags"))
            df.at[idx, "ai_hype_score"] = _validated_score(result.get("hype_score"))
            df.at[idx, "ai_play_recommendation"] = _validated_str(result.get("play_recommendation"))

    enriched_count = df["ai_summary"].notna().sum()
    logger.info(f"Enrichment complete: {enriched_count}/{len(df)} records enriched")
    return df

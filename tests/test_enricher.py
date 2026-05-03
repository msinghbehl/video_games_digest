import json
import os

import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from src.pipeline import enricher


def _make_df() -> pd.DataFrame:
    return pd.DataFrame([
        {"id": "abc123", "title": "Elden Ring", "genre": "RPG", "critic_score": 96.0,
         "community_rating": 4.5, "notes": None, "source": "rawg"},
        {"id": "def456", "title": "Hollow Knight", "genre": "Metroidvania", "critic_score": 90.0,
         "community_rating": 4.3, "notes": None, "source": "metacritic"},
    ])


def _make_config(batch_size: int = 15) -> dict:
    return {
        "ai": {"model": "claude-sonnet-4-6", "max_tokens": 2048},
        "pipeline": {"enrichment_batch_size": batch_size, "max_enrichment_records": 100},
    }


def _fake_claude_response(records: list[dict]) -> str:
    return json.dumps([
        {
            "id": r["id"],
            "summary": f"{r['title']} is a great game.",
            "genre_tags": "Action RPG, Open World",
            "hype_score": 9,
            "play_recommendation": "Play it immediately.",
        }
        for r in records
    ])


def test_enrich_adds_ai_fields():
    df = _make_df()
    config = _make_config()

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}):
        with patch("src.pipeline.enricher._call_claude") as mock_claude:
            mock_claude.return_value = _fake_claude_response(
                [{"id": "abc123", "title": "Elden Ring"}, {"id": "def456", "title": "Hollow Knight"}]
            )
            result = enricher.enrich(df, config)

    for field in enricher.AI_FIELDS:
        assert field in result.columns

    assert result.iloc[0]["ai_summary"] == "Elden Ring is a great game."
    assert result.iloc[0]["ai_hype_score"] == 9


def test_enrich_handles_partial_response():
    df = _make_df()
    config = _make_config()

    # Claude returns only one record
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}):
        with patch("src.pipeline.enricher._call_claude") as mock_claude:
            mock_claude.return_value = json.dumps([
                {"id": "abc123", "summary": "Great.", "genre_tags": "RPG", "hype_score": 9, "play_recommendation": "Play it."}
            ])
            result = enricher.enrich(df, config)

    assert result.iloc[0]["ai_summary"] == "Great."
    assert result.iloc[1]["ai_summary"] is None


def test_enrich_handles_bad_json():
    df = _make_df()
    config = _make_config()

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}):
        with patch("src.pipeline.enricher._call_claude") as mock_claude:
            mock_claude.return_value = "not json at all"
            result = enricher.enrich(df, config)

    assert result["ai_summary"].isna().all()


def test_enrich_empty_dataframe():
    df = pd.DataFrame()
    config = _make_config()
    result = enricher.enrich(df, config)
    assert result.empty


def test_enrich_respects_max_records():
    rows = [{"id": f"id{i}", "title": f"Game {i}", "genre": "RPG",
             "critic_score": 80.0, "community_rating": 4.0, "notes": None, "source": "rawg"}
            for i in range(20)]
    df = pd.DataFrame(rows)
    config = {
        "ai": {"model": "claude-sonnet-4-6", "max_tokens": 2048},
        "pipeline": {"enrichment_batch_size": 15, "max_enrichment_records": 5},
    }

    called_with: list[list] = []

    def capture_call(client, prompt, model, max_tokens):
        data = json.loads(prompt.split("Games:\n")[1])
        called_with.extend(data)
        return json.dumps([{"id": r["id"], "summary": ".", "genre_tags": "RPG", "hype_score": 7, "play_recommendation": "."} for r in data])

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}):
        with patch("src.pipeline.enricher._call_claude", side_effect=capture_call):
            enricher.enrich(df, config)

    assert len(called_with) == 5

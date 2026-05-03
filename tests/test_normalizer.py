import pandas as pd
import pytest
from src.pipeline.normalizer import normalize, SCHEMA_COLS


def _sample_df(source: str) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "title": "Elden Ring",
            "platform": "PC",
            "genre": "RPG",
            "release_date": "2022-02-25",
            "critic_score": "96",
            "community_rating": "4.5",
            "personal_rating": None,
            "status": None,
            "notes": None,
            "url": "https://example.com",
            "source": source,
        },
        {
            "title": "  ",  # whitespace-only — should be dropped
            "platform": None,
            "genre": None,
            "release_date": None,
            "critic_score": None,
            "community_rating": None,
            "personal_rating": None,
            "status": None,
            "notes": None,
            "url": None,
            "source": source,
        },
    ])


def test_normalize_output_has_schema_columns():
    df = _sample_df("rawg")
    result = normalize(df, "rawg")
    for col in SCHEMA_COLS:
        assert col in result.columns, f"Missing column: {col}"


def test_normalize_drops_empty_title():
    df = _sample_df("rawg")
    result = normalize(df, "rawg")
    assert len(result) == 1
    assert result.iloc[0]["title"] == "Elden Ring"


def test_normalize_sets_source():
    df = _sample_df("metacritic")
    result = normalize(df, "metacritic")
    assert (result["source"] == "metacritic").all()


def test_normalize_id_is_12_chars():
    df = _sample_df("rawg")
    result = normalize(df, "rawg")
    assert result.iloc[0]["id"].isalnum()
    assert len(result.iloc[0]["id"]) == 12


def test_normalize_numeric_coercion():
    df = _sample_df("metacritic")
    result = normalize(df, "metacritic")
    assert result.iloc[0]["critic_score"] == 96.0
    assert result.iloc[0]["community_rating"] == 4.5


def test_normalize_empty_dataframe():
    result = normalize(pd.DataFrame(), "rawg")
    assert result.empty
    for col in SCHEMA_COLS:
        assert col in result.columns


def test_normalize_same_title_same_id():
    df1 = pd.DataFrame([{"title": "Elden Ring", "source": "rawg"}])
    df2 = pd.DataFrame([{"title": "  Elden Ring  ", "source": "rawg"}])
    r1 = normalize(df1, "rawg")
    r2 = normalize(df2, "rawg")
    assert r1.iloc[0]["id"] == r2.iloc[0]["id"]

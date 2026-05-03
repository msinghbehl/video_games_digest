import os
import tempfile

import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from src.sources import metacritic_csv


# ── Metacritic CSV ──────────────────────────────────────────────────────────

def _write_csv(content: str) -> str:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    tmp.write(content)
    tmp.close()
    return tmp.name


def test_metacritic_csv_basic():
    csv_content = "Title,Platform,Score,Release Date,Genre,URL\nElden Ring,PC,96,2022-02-25,RPG,https://metacritic.com/elden-ring\n"
    path = _write_csv(csv_content)
    column_map = {
        "title": "Title", "platform": "Platform", "critic_score": "Score",
        "release_date": "Release Date", "genre": "Genre", "url": "URL",
    }
    df = metacritic_csv.fetch(path, column_map)
    os.unlink(path)

    assert len(df) == 1
    assert df.iloc[0]["title"] == "Elden Ring"
    assert df.iloc[0]["critic_score"] == "96"
    assert df.iloc[0]["source"] == "metacritic"


def test_metacritic_csv_missing_column_fills_none():
    csv_content = "Title,Platform\nHollow Knight,PC\n"
    path = _write_csv(csv_content)
    column_map = {
        "title": "Title", "platform": "Platform", "critic_score": "Score",
        "release_date": "Release Date", "genre": "Genre", "url": "URL",
    }
    df = metacritic_csv.fetch(path, column_map)
    os.unlink(path)

    assert df.iloc[0]["critic_score"] is None
    assert df.iloc[0]["genre"] is None


def test_metacritic_csv_file_not_found():
    with pytest.raises(FileNotFoundError):
        metacritic_csv.fetch("nonexistent.csv", {})


# ── RAWG (mocked HTTP) ──────────────────────────────────────────────────────

def test_rawg_fetch_maps_fields():
    from src.sources import rawg

    mock_response = {
        "results": [
            {
                "name": "Elden Ring",
                "released": "2022-02-25",
                "rating": 4.5,
                "metacritic": 96,
                "slug": "elden-ring",
                "genres": [{"name": "RPG"}, {"name": "Action"}],
                "platforms": [{"platform": {"name": "PC"}}, {"platform": {"name": "PS5"}}],
            }
        ]
    }

    with patch.dict(os.environ, {"RAWG_API_KEY": "test-key"}):
        with patch("src.sources.rawg.requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None,
            )
            df = rawg.fetch()

    assert len(df) == 1
    row = df.iloc[0]
    assert row["title"] == "Elden Ring"
    assert row["community_rating"] == 4.5
    assert row["critic_score"] == 96
    assert "RPG" in row["genre"]
    assert "PC" in row["platform"]
    assert row["source"] == "rawg"


def test_rawg_missing_api_key():
    from src.sources import rawg
    env = {k: v for k, v in os.environ.items() if k != "RAWG_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(EnvironmentError):
            rawg.fetch()

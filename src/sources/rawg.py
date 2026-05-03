import os
from datetime import datetime, timezone

import pandas as pd
import requests

from src.utils.logger import get_logger

logger = get_logger(__name__)

RAWG_BASE = "https://api.rawg.io/api"


def fetch(ordering: str = "-rating", page_size: int = 40) -> pd.DataFrame:
    api_key = os.environ.get("RAWG_API_KEY")
    if not api_key:
        raise EnvironmentError("RAWG_API_KEY is not set")

    params = {
        "key": api_key,
        "ordering": ordering,
        "page_size": min(page_size, 40),
    }

    logger.info(f"Fetching RAWG games (ordering={ordering}, page_size={page_size})")
    response = requests.get(f"{RAWG_BASE}/games", params=params, timeout=15)
    response.raise_for_status()

    results = response.json().get("results", [])
    logger.info(f"RAWG returned {len(results)} games")

    rows = []
    for game in results:
        genres = ", ".join(g["name"] for g in game.get("genres", []))
        platforms = ", ".join(
            p["platform"]["name"] for p in game.get("platforms", []) or []
        )
        rows.append({
            "title": game.get("name"),
            "platform": platforms or None,
            "genre": genres or None,
            "release_date": game.get("released"),
            "critic_score": game.get("metacritic"),
            "community_rating": game.get("rating"),
            "url": f"https://rawg.io/games/{game.get('slug', '')}",
            "notes": None,
            "personal_rating": None,
            "status": None,
        })

    df = pd.DataFrame(rows)
    df["source"] = "rawg"
    df["fetched_at"] = datetime.now(timezone.utc)
    return df

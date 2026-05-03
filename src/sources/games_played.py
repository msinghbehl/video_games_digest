import json
import os
from datetime import datetime, timezone

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

from src.utils.logger import get_logger

logger = get_logger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def fetch(spreadsheet_name: str, sheet_tab: str, column_map: dict) -> pd.DataFrame:
    json_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not json_path or not os.path.exists(json_path):
        raise EnvironmentError(
            f"GOOGLE_SERVICE_ACCOUNT_JSON path is missing or file not found: {json_path}"
        )

    logger.info(f"Connecting to Google Sheets: '{spreadsheet_name}' / tab '{sheet_tab}'")
    creds = Credentials.from_service_account_file(json_path, scopes=SCOPES)
    client = gspread.authorize(creds)

    spreadsheet = client.open(spreadsheet_name)
    worksheet = spreadsheet.worksheet(sheet_tab)
    records = worksheet.get_all_records()
    logger.info(f"Google Sheets returned {len(records)} rows")

    if not records:
        return pd.DataFrame()

    raw = pd.DataFrame(records).astype(str).replace("", None)

    rename = {v: k for k, v in column_map.items() if v in raw.columns}
    df = raw.rename(columns=rename)

    schema_cols = ["title", "platform", "personal_rating", "status", "notes", "release_date"]
    for col in schema_cols:
        if col not in df.columns:
            logger.warning(f"Games Played sheet missing column '{col}' — filling with None")
            df[col] = None

    df = df[schema_cols].copy()
    df["source"] = "games_played"
    df["critic_score"] = None
    df["community_rating"] = None
    df["genre"] = None
    df["url"] = None
    df["fetched_at"] = datetime.now(timezone.utc)

    return df

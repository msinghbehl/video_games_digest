import os
from datetime import date

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.utils.logger import get_logger

logger = get_logger(__name__)

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


def _compute_stats(df: pd.DataFrame) -> dict:
    stats = {
        "total_records": len(df),
        "by_source": df["source"].value_counts().to_dict(),
        "avg_hype_score": round(df["ai_hype_score"].mean(), 2) if df["ai_hype_score"].notna().any() else None,
        "avg_hype_by_source": (
            df.groupby("source")["ai_hype_score"]
            .mean()
            .round(2)
            .to_dict()
        ),
        "top_10": df.nlargest(10, "ai_hype_score")[
            ["title", "source", "ai_hype_score", "ai_genre_tags", "ai_play_recommendation"]
        ].to_dict(orient="records"),
        "genre_distribution": _genre_distribution(df),
        "finished_games": df[df["status"] == "Finished"][
            ["title", "personal_rating", "ai_summary", "ai_play_recommendation"]
        ].to_dict(orient="records"),
        "run_date": date.today().isoformat(),
    }
    return stats


def _genre_distribution(df: pd.DataFrame) -> dict:
    counts: dict[str, int] = {}
    for tags in df["ai_genre_tags"].dropna():
        for tag in tags.split(","):
            tag = tag.strip()
            if tag:
                counts[tag] = counts.get(tag, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True)[:15])


def generate(df: pd.DataFrame, config: dict) -> None:
    if df.empty:
        logger.warning("Nothing to report — enriched DataFrame is empty")
        return

    output_cfg = config["output"]
    reports_dir = output_cfg.get("reports_dir", "output/reports")
    formats = output_cfg.get("report_formats", ["csv"])
    os.makedirs(reports_dir, exist_ok=True)

    today = date.today().isoformat()
    stats = _compute_stats(df)

    if "csv" in formats:
        csv_path = os.path.join(reports_dir, f"digest_{today}.csv")
        df.to_csv(csv_path, index=False)
        logger.info(f"CSV report written: {csv_path}")

    if "html" in formats:
        html_path = os.path.join(reports_dir, f"digest_{today}.html")
        _write_html(df, stats, html_path)
        logger.info(f"HTML report written: {html_path}")


def _write_html(df: pd.DataFrame, stats: dict, path: str) -> None:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("digest.html")
    html = template.render(stats=stats, records=df.to_dict(orient="records"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

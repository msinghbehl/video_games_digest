# FlowForge — Gaming Intelligence Pipeline

An automated data pipeline that pulls game data from three sources, enriches every record with AI-generated insights via Claude, and produces a weekly Gaming Intelligence Digest.

## What it does

- Fetches top-rated games from the **RAWG Video Games Database API**
- Reads a **Metacritic top games CSV** for critic-ranked benchmarks
- Pulls a personal **"Games Played" Google Sheet** log
- Normalizes all records into a unified schema with pandas
- Enriches each game with **Claude AI**: summary, genre tags, hype score (1–10), and play recommendation
- Generates a ranked weekly digest as **CSV + HTML report**

## Output

A dark-themed HTML digest ranking all games by AI hype score, with genre breakdowns, source attribution, and personal log highlights.

![Pipeline flow: 3 sources → normalize → Claude AI → digest report]

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| Data processing | pandas |
| AI enrichment | Claude API (Haiku) via `anthropic` SDK |
| Google Sheets | `gspread` + service account |
| Retry logic | `tenacity` |
| Config | PyYAML |
| Templating | Jinja2 |

## Project Structure

```
src/
├── sources/        # Data ingestion (RAWG, CSV, Google Sheets)
├── pipeline/       # Normalize → Enrich → Merge
├── reports/        # Report generation + HTML template
└── utils/          # Logger, config loader

config/
├── config.yaml             # All tunable parameters
└── enrichment_prompt.txt   # Claude prompt template
```

## Setup

### 1. Clone and install

```bash
git clone <your-repo-url>
cd FlowForge
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in your keys:
# ANTHROPIC_API_KEY — get from console.anthropic.com
# RAWG_API_KEY      — free at rawg.io/apidocs
# GOOGLE_SERVICE_ACCOUNT_JSON — path to your service account JSON
```

### 3. Set up Google Sheets

1. Create a Google Cloud project and enable the **Google Sheets API** and **Google Drive API**
2. Create a service account, download its JSON key, save to `config/service_account.json`
3. Create a Google Sheet named **`FlowForge - Games Played`** with columns:
   `Title | Platform | Hours Played | Your Rating | Status | Started | Finished Date | Notes`
4. Share the sheet with your service account email

### 4. Add Metacritic CSV

Download the games dataset from Kaggle:
[Metacritic Scores for Games, Movies, TV and Music](https://www.kaggle.com/datasets/patkle/metacritic-scores-for-games-movies-tv-and-music)

Drop the games CSV at `data/raw/metacritic_top_games.csv`. The column mapping in `config/config.yaml` is already configured for this dataset's schema.

### 5. Run

```bash
python3 -m src.main
```

Reports are written to `output/reports/digest_YYYY-MM-DD.csv` and `.html`.

## Configuration

All behaviour is controlled by `config/config.yaml` — no code changes needed for tuning:

```yaml
pipeline:
  enrichment_batch_size: 8       # Records per Claude API call
  max_enrichment_records: 100    # Cost control cap

sources:
  rawg:
    enabled: true
    ordering: "-rating"          # -rating | -released | -metacritic

ai:
  model: "claude-haiku-4-5-20251001"   # Swap to sonnet for higher quality
  max_tokens: 4096
```

## Scheduling (weekly digest)

Add to crontab to run every Monday at 8am:

```bash
crontab -e
# Add:
0 8 * * 1 cd /path/to/FlowForge && /path/to/venv/bin/python3 -m src.main
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for a full technical breakdown of every module, design decisions, data schema, error handling strategy, and extension points.

## Running Tests

```bash
python -m pytest tests/test_normalizer.py -v
python -m pytest tests/test_sources.py -v
python -m pytest tests/test_enricher.py -v
```

## Security

- API keys and credentials live in `.env` and `config/service_account.json` — both are gitignored
- The Google service account uses read-only scopes (`spreadsheets.readonly`, `drive.readonly`)
- Config is loaded with `yaml.safe_load` to prevent code execution via YAML

## Data Sources

| Source | Provider | Notes |
|--------|----------|-------|
| Game database + ratings | [RAWG Video Games Database](https://rawg.io/apidocs) | Free API, 500k+ titles |
| Critic scores | [Metacritic Scores Dataset — Kaggle](https://www.kaggle.com/datasets/patkle/metacritic-scores-for-games-movies-tv-and-music) | Community-maintained dataset by patkle |
| Personal log | Google Sheets (your own) | Not included in this repo |

## License

MIT

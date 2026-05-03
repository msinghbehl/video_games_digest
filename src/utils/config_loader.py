import os
import yaml


REQUIRED_KEYS = ["pipeline", "sources", "ai", "output"]


def load_config(path: str = "config/config.yaml") -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    for key in REQUIRED_KEYS:
        if key not in config:
            raise ValueError(f"Missing required config key: '{key}'")

    return config

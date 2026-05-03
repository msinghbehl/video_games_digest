# FlowForge weekly scheduler entry point.
#
# To run every Monday at 8am, add to crontab (crontab -e):
#   0 8 * * 1 cd /path/to/FlowForge && /path/to/venv/bin/python3 -m src.main
#
# Or run manually from the FlowForge directory:
#   python3 -m src.main

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.main import run

if __name__ == "__main__":
    run()

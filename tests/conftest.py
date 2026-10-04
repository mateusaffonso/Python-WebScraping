import os
import sys

# The project modules import each other as top-level packages
# (e.g. "from trabalha_brasil import ..."), so proj_scraper/ must be on the path.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "proj_scraper"))

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def read_fixture(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()

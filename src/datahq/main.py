from __future__ import annotations

import argparse

from dotenv import load_dotenv

from .cruises import sync_cruises
from .retention import prune_source
from .revolut import sync_revolut
from .square import sync_square


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="The Arch data ingestion runner")
    parser.add_argument("source", choices=["square", "revolut", "cruises", "all"])
    args = parser.parse_args()

    if args.source in {"square", "all"}:
        sync_square()
        prune_source("square")
    if args.source in {"revolut", "all"}:
        sync_revolut()
        prune_source("revolut")
    if args.source in {"cruises", "all"}:
        sync_cruises()


if __name__ == "__main__":
    main()

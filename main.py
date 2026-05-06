# RL Rank Viewer

import argparse
import logging
import sys

from log_setup import get_logger, setup_logger
from tracker import GameTracker
from overlay import WebViewApp

log = get_logger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RankViewer Overlay")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    setup_logger(logging.DEBUG if args.verbose else logging.INFO)

    log.info("RankViewer starting…")

    tracker = GameTracker()
    overlay = WebViewApp(tracker)
    tracker.on_players_update = overlay.on_players_update
    tracker.on_match_end = overlay.on_match_end

    tracker.start()
    try:
        overlay.run()
    finally:
        tracker.stop()
        log.info("RankViewer stopped")


if __name__ == "__main__":
    sys.exit(main())

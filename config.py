"""App config."""

import os

from dotenv import load_dotenv

load_dotenv()

MMR_QUEUE_BACKPRESSURE: int = 20
RL_STATS_PORT: int = 49123
RL_PACKET_SEND_RATE: int = 1

MMR_CACHE_TTL: int = 300
MMR_STALE_TTL: int = 3600
MMR_NEGATIVE_CACHE_TTL: int = 120
MMR_FETCH_INTERVAL: float = 0.5
MMR_HTTP_TIMEOUT: int = 15

# Modo oficial (API key) vs scraping
TRACKER_API_KEY: str | None = os.getenv("TRACKER_API_KEY")
USE_OFFICIAL_API: bool = TRACKER_API_KEY is not None

MMR_IMPERSONATE_TARGET: str = "chrome120"

MMR_API_BASE_URL: str = (
    "https://api.tracker.gg/api/v2/rocket-league/standard/profile/{plat}/{ident}"
)

MMR_OFFICIAL_API_URL: str = (
    "https://public-api.tracker.gg/v2/rocket-league/standard/profile/{plat}/{ident}"
)

MMR_API_HEADERS: dict[str, str] = {
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://rocketleague.tracker.network",
    "Referer": "https://rocketleague.tracker.network/",
    "Accept-Language": "en-US,en;q=0.9",
}

MMR_PLATFORM_MAP: dict[str, str] = {
    "Steam": "steam",
    "Epic": "epic",
    "PS4": "psn",
    "XboxOne": "xbl",
    "Switch": "switch",
}

MMR_PLAYLIST_IDS: dict[int, str] = {10: "1v1", 11: "2v2", 13: "3v3"}

ROCKET_LEAGUE_TIERS: dict[int, str] = {
    0: "Unranked",
    1: "Bronze I",
    2: "Bronze II",
    3: "Bronze III",
    4: "Silver I",
    5: "Silver II",
    6: "Silver III",
    7: "Gold I",
    8: "Gold II",
    9: "Gold III",
    10: "Platinum I",
    11: "Platinum II",
    12: "Platinum III",
    13: "Diamond I",
    14: "Diamond II",
    15: "Diamond III",
    16: "Champion I",
    17: "Champion II",
    18: "Champion III",
    19: "Grand Champion I",
    20: "Grand Champion II",
    21: "Grand Champion III",
    22: "Supersonic Legend",
}

OVERLAY_WIDTH: int = 300
OVERLAY_HEIGHT: int = 440
OVERLAY_REFRESH_INTERVAL: float = 2.0
OVERLAY_PLAYLIST_CYCLE: tuple[str, ...] = ("best", "1v1", "2v2", "3v3")
OVERLAY_SIZE_PRESETS: tuple[tuple[str, int, int], ...] = (
    ("Small", 300, 440),
    ("Medium", 360, 530),
    ("Tall", 280, 620),
    ("Wide", 480, 340),
)

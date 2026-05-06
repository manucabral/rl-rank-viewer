# See main.py for full credits. Uses rlstatsapi for game-state events.
"""RL stats tracker."""

import asyncio
import threading
from collections.abc import Callable

from rlstatsapi import (
    StatsClient,
    candidate_stats_api_paths,
    configure_stats_api,
    get_stats_api_status,
)

from config import MMR_QUEUE_BACKPRESSURE, RL_PACKET_SEND_RATE, RL_STATS_PORT
from fetcher import RankFetcher
from log_setup import get_logger
from rank_utils import team_name

log = get_logger(__name__)


class GameTracker:
    """Connects to RL Stats API, extracts players, enqueues MMR fetches.

    Callbacks (set externally):
        on_players_update(players: list[dict])
        on_match_end()
    """

    def __init__(self, port: int = RL_STATS_PORT):
        self.on_players_update: Callable[[list[dict]], None] | None = None
        self.on_match_end: Callable[[], None] | None = None

        self._port = port
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stop_event: asyncio.Event | None = None
        self._client: StatsClient | None = None
        self._match_active = False
        self._players: list[dict] = []
        self._players_lock = threading.Lock()
        self._rank_fetcher = RankFetcher()

    def start(self) -> None:
        self._setup_api()
        self._rank_fetcher.start()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="game-tracker"
        )
        self._thread.start()
        log.info("Game tracker started")

    def stop(self) -> None:
        pending = self._rank_fetcher.pending_count
        self._rank_fetcher.stop()
        if self._loop and self._loop.is_running():
            if self._stop_event is not None:
                self._loop.call_soon_threadsafe(self._stop_event.set)
            else:
                self._loop.call_soon_threadsafe(self._loop.stop)
        log.info("Game tracker stopped (%d pending)", pending)

    @property
    def current_players(self) -> list[dict]:
        with self._players_lock:
            return list(self._players)

    @property
    def rank_fetcher(self) -> RankFetcher:
        return self._rank_fetcher

    def _setup_api(self) -> None:
        status = get_stats_api_status()
        if status.enabled:
            log.info("Stats API already enabled (%s)", status.path)
            return
        if not status.found:
            searched = "; ".join(str(p) for p in candidate_stats_api_paths())
            log.warning(
                "TAStatsAPI.ini not found. Searched:\n  %s\n"
                "Make sure Rocket League has been run at least once.",
                searched,
            )
            return
        try:
            configure_stats_api(
                enabled=True,
                port=self._port,
                packet_send_rate=RL_PACKET_SEND_RATE,
                path=status.path,
            )
            log.info("Stats API configured (%s). Restart RL if running.", status.path)
        except (OSError, ValueError) as exc:
            log.warning("Could not configure Stats API: %s", exc)

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._listen())
        except asyncio.CancelledError:
            log.info("Game tracker loop cancelled")
        except Exception:  # pylint: disable=broad-exception-caught
            log.exception("Game tracker loop crashed")
        finally:
            self._loop.close()

    async def _listen(self) -> None:
        log.info("Connecting to RL Stats API (127.0.0.1:%d)…", self._port)
        async with StatsClient(port=self._port, overflow="drop") as client:
            self._client = client
            client.on_match_created(self._on_create)
            client.on_update_state(self._on_update)
            client.on_match_destroyed(self._on_destroy)
            client.on_connect(lambda: log.info("Stats API TCP connected"))
            client.on_disconnect(lambda: log.warning("Stats API TCP disconnected"))
            log.info("Stats API ready, waiting for match…")
            self._stop_event = asyncio.Event()
            await self._stop_event.wait()

    async def _on_create(self, msg) -> None:
        guid = msg.data.get("MatchGuid", "")
        if not guid:
            return
        self._match_active = True
        log.info("  MATCH CREATED: %s", guid)

    async def _on_destroy(self, _msg) -> None:
        if not self._match_active:
            return
        self._match_active = False
        with self._players_lock:
            self._players = []
        log.info("  MATCH ENDED")
        if self.on_match_end:
            self.on_match_end()

    async def _on_update(self, msg) -> None:
        if self._rank_fetcher.pending_count > MMR_QUEUE_BACKPRESSURE:
            log.warning(
                "Queue backed up (%d), dropping events",
                self._rank_fetcher.pending_count,
            )
            if self._client is not None:
                self._client.clear_queue()
            return

        data = msg.data
        raw_players = data.get("Players", [])
        if not isinstance(raw_players, list) or not raw_players:
            return

        self._check_active(data)
        if not self._match_active:
            return

        player_list = self._extract(raw_players)
        if not self._update(player_list):
            return

        self._log_players(player_list)
        self._queue_all(player_list)
        if self.on_players_update:
            self.on_players_update(player_list)

    @staticmethod
    def _extract(raw_players: list) -> list[dict]:
        players: list[dict] = []
        for entry in raw_players:
            if not isinstance(entry, dict):
                continue
            players.append(
                {
                    "name": entry.get("Name", "?"),
                    "id": entry.get("PrimaryId", "?"),
                    "team": entry.get("TeamNum", -1),
                }
            )
        return players

    def _check_active(self, data: dict) -> None:
        guid = data.get("MatchGuid", "")
        if guid and not self._match_active:
            self._match_active = True
            log.info("  MATCH STARTED (via UpdateState)")

    def _update(self, new_players: list[dict]) -> bool:
        with self._players_lock:
            if new_players == self._players:
                return False
            self._players = new_players
            return True

    def _log_players(self, players: list[dict]) -> None:
        log.info("Players in match (%d):", len(players))
        for p in players:
            log.info("  [%s] %s (ID: %s)", team_name(p["team"]), p["name"], p["id"])

    def _queue_all(self, players: list[dict]) -> None:
        log.info("Enqueuing %d player(s) for rank fetch…", len(players))
        for p in players:
            self._rank_fetcher.enqueue(p["id"], p["name"])

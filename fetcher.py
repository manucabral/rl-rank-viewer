"""Rank fetcher"""

import queue
import threading
import time
from datetime import datetime, timezone

from curl_cffi import requests

from config import (
    MMR_API_BASE_URL,
    MMR_API_HEADERS,
    MMR_CACHE_TTL,
    MMR_FETCH_INTERVAL,
    MMR_HTTP_TIMEOUT,
    MMR_IMPERSONATE_TARGET,
    MMR_NEGATIVE_CACHE_TTL,
    MMR_PLATFORM_MAP,
    MMR_PLAYLIST_IDS,
    MMR_STALE_TTL,
)
from log_setup import get_logger
from rank_utils import parse_division_number

log = get_logger(__name__)


def resolve_platform(primary_id: str, display_name: str) -> tuple[str, str] | None:
    """Parse PrimaryId into (platform, identifier) or None."""
    parts = primary_id.split("|")
    plat = MMR_PLATFORM_MAP.get(parts[0])
    if not plat:
        return None
    if plat == "steam" and len(parts) >= 2 and parts[1]:
        return (plat, parts[1])
    if not display_name:
        return None
    return (plat, display_name)


def parse_mmr_response(data: dict) -> dict | None:
    """Parse tracker.gg API response into playlists dict."""
    playlists: dict[str, dict] = {}
    for seg in data.get("segments") or []:
        if seg.get("type") != "playlist":
            continue
        pid = (seg.get("attributes") or {}).get("playlistId")
        if not isinstance(pid, int):
            continue
        label = MMR_PLAYLIST_IDS.get(pid)
        if not label:
            continue
        stats = seg.get("stats") or {}
        rating_val = stats.get("rating")
        rating = rating_val.get("value") if isinstance(rating_val, dict) else None
        if rating is None:
            continue
        try:
            mmr_int = int(rating)
        except (ValueError, TypeError):
            continue
        tier = ((stats.get("tier") or {}).get("metadata") or {}).get("name", "Unranked")
        division = ((stats.get("division") or {}).get("metadata") or {}).get("name", "")
        tier_val = (stats.get("tier") or {}).get("value")
        tier_id: int | None = (
            int(tier_val) if isinstance(tier_val, (int, float)) else None
        )
        playlists[label] = {
            "mmr": mmr_int,
            "tier": tier,
            "division": division,
            "tier_id": tier_id,
            "div_num": parse_division_number(division),
        }

    if not playlists:
        return None

    best_label, best = max(playlists.items(), key=lambda x: x[1]["mmr"])
    return {"playlists": playlists, "best": {**best, "playlist": best_label}}


class RankFetcher:
    """Fetches and caches player ranks from tracker.gg API in a background thread."""

    def __init__(self, ttl: int = MMR_CACHE_TTL):
        self._ttl = ttl
        self._cache: dict[str, dict] = {}
        self._cache_lock = threading.Lock()
        self._pending: queue.Queue[tuple[str, str, str]] = queue.Queue()
        self._inflight: set[str] = set()
        self._inflight_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread: threading.Thread | None = None

    def start(self) -> None:
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._worker_thread = threading.Thread(
            target=self._work, daemon=True, name="mmr-fetcher"
        )
        self._worker_thread.start()
        log.info("Rank fetcher started")

    def stop(self) -> None:
        self._stop_event.set()
        log.info("Rank fetcher stopping (%d pending)", self.pending_count)

    @property
    def pending_count(self) -> int:
        with self._inflight_lock:
            return self._pending.qsize() + len(self._inflight)

    def get_cached(self, key: str) -> dict | None:
        """Get from cache (fresh or stale), None if expired/missing."""
        with self._cache_lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            age = self._age(entry)
            fresh_ttl = MMR_NEGATIVE_CACHE_TTL if entry.get("_negative") else self._ttl
            if age < fresh_ttl:
                return entry  # no deepcopy, consumer is read-only
            if not entry.get("_negative") and age < MMR_STALE_TTL:
                return entry
            return None

    def is_fresh(self, key: str) -> bool:
        with self._cache_lock:
            entry = self._cache.get(key)
            if not entry:
                return False
            ttl = MMR_NEGATIVE_CACHE_TTL if entry.get("_negative") else self._ttl
            return self._age(entry) < ttl

    def enqueue(self, primary_id: str, display_name: str) -> None:
        """Queue player for rank fetch."""
        key = f"{primary_id}|{display_name}"
        with self._inflight_lock:
            if key in self._inflight:
                return
        if self.is_fresh(key):
            return
        handle = resolve_platform(primary_id, display_name)
        if not handle:
            return
        platform, identifier = handle
        with self._inflight_lock:
            self._inflight.add(key)
        self._pending.put((key, platform, identifier))
        log.debug("queued %s -> %s/%s", key, platform, identifier)

    def _work(self) -> None:
        last_request = 0.0
        while not self._stop_event.is_set():
            try:
                key, plat, ident = self._pending.get(timeout=MMR_FETCH_INTERVAL)
            except queue.Empty:
                continue
            since = time.monotonic() - last_request
            if since < MMR_FETCH_INTERVAL:
                self._stop_event.wait(MMR_FETCH_INTERVAL - since)
                if self._stop_event.is_set():
                    with self._inflight_lock:
                        self._inflight.discard(key)
                    break
            try:
                self._fetch(key, plat, ident)
            except Exception:  # pylint: disable=broad-exception-caught
                log.exception("rank fetch crashed for %s", key)
            finally:
                with self._inflight_lock:
                    self._inflight.discard(key)
            last_request = time.monotonic()
        log.info("Rank fetcher worker stopped")

    def _fetch(self, key: str, plat: str, ident: str) -> None:
        url = MMR_API_BASE_URL.format(plat=plat, ident=ident)
        log.info("GET %s", url)
        t0 = time.monotonic()
        try:
            r = requests.get(
                url,
                headers=MMR_API_HEADERS,
                impersonate=MMR_IMPERSONATE_TARGET,  # type: ignore[arg-type]
                timeout=MMR_HTTP_TIMEOUT,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log.warning("HTTP fetch failed for %s: %s", key, exc)
            return
        log.debug(
            "  -> HTTP %d in %.0fms", r.status_code, (time.monotonic() - t0) * 1000
        )
        if r.status_code == 404:
            self._cache_miss(key)
            return
        if r.status_code != 200:
            log.warning("HTTP %d for %s", r.status_code, key)
            return
        try:
            self._parse(key, r)
        except Exception:  # pylint: disable=broad-exception-caught
            log.exception("failed to process MMR response for %s", key)

    def _parse(self, key: str, response) -> None:
        try:
            payload = response.json()
        except ValueError as exc:
            log.warning("bad JSON for %s: %s", key, exc)
            return
        data = (payload or {}).get("data")
        if not isinstance(data, dict):
            log.warning("no .data in response for %s", key)
            return
        entry = parse_mmr_response(data)
        if not entry:
            log.warning("no playlists found for %s", key)
            self._cache_miss(key)
            return
        entry["fetched_at"] = datetime.now(timezone.utc).isoformat()
        with self._cache_lock:
            self._cache[key] = entry
        self._log_summary(key, entry)

    def _cache_miss(self, key: str) -> None:
        log.info("player not found: %s", key)
        with self._cache_lock:
            self._cache[key] = {
                "_negative": True,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

    @staticmethod
    def _age(entry: dict) -> float:
        fetched = datetime.fromisoformat(entry["fetched_at"])
        return (datetime.now(timezone.utc) - fetched).total_seconds()

    def _log_summary(self, key: str, entry: dict) -> None:
        best = entry["best"]
        parts = []
        for label in tuple(MMR_PLAYLIST_IDS.values()):
            pl = entry["playlists"].get(label)
            parts.append(f'{label}={pl["mmr"] if pl else "???"}')
        log.info(
            "%s: MMR %s (best=%d - %s)",
            key,
            " ".join(parts),
            best["mmr"],
            best["playlist"],
        )

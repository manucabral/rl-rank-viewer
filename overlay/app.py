"""Rank overlay."""

import base64
import html as html_mod
import json
import os

import webview

from config import (
    OVERLAY_HEIGHT,
    OVERLAY_PLAYLIST_CYCLE,
    OVERLAY_REFRESH_INTERVAL,
    OVERLAY_SIZE_PRESETS,
    OVERLAY_WIDTH,
)
from controller import Controller
from log_setup import get_logger
from overlay.templates import OVERLAY_HTML, PLACEHOLDER_HTML
from rank_utils import rank_image_filename, rank_tier_color
from utils import RepeatingTimer

log = get_logger(__name__)
_RANKS_DIR = os.path.join(os.path.dirname(__file__), "ranks")


def _load_icons() -> dict[int, str]:
    """Load rank icons as base64."""
    cache: dict[int, str] = {}
    for tier_id in range(23):
        path = os.path.join(_RANKS_DIR, rank_image_filename(tier_id))
        try:
            with open(path, "rb") as file:
                data = base64.b64encode(file.read()).decode("ascii")
            cache[tier_id] = f"data:image/png;base64,{data}"
        except FileNotFoundError:
            pass
    log.info("Loaded %d rank icons into cache", len(cache))
    return cache


def _load_bindings(path: str = "bindings.json") -> dict:
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


class WebViewApp:
    """Frameless overlay."""

    def __init__(self, tracker):
        self._tracker = tracker
        self._window = None
        self._hidden = False
        self._selected_playlist: str = OVERLAY_PLAYLIST_CYCLE[0]
        self._size_index: int = 0
        self._last_html: str | None = None
        self._hotkey_registered = False
        self._icon_cache = _load_icons()
        self._timer = RepeatingTimer(OVERLAY_REFRESH_INTERVAL, self._poll)

        self._actions = {
            "toggle": self._toggle,
            "playlist_next": self._next_list,
            "playlist_prev": self._prev_list,
            "size_next": self._next_size,
            "size_prev": self._prev_size,
        }

        bindings = _load_bindings()
        self._keyboard = bindings.get("keyboard", {})
        self._controller = Controller(self._actions, bindings.get("controller"))

    def on_players_update(self, players: list[dict]) -> None:
        self._push(players)

    def on_match_end(self) -> None:
        self._last_html = None
        if self._window:
            try:
                self._window.evaluate_js("showWaiting()")
            except Exception:  # pylint: disable=broad-exception-caught
                pass

    def run(self) -> None:
        self._window = webview.create_window(
            "RankViewer",
            html=OVERLAY_HTML,
            width=OVERLAY_WIDTH,
            height=OVERLAY_HEIGHT,
            frameless=False,
            resizable=True,
            on_top=True,
        )
        self._hotkeys_on()
        self._controller.start()
        self._timer.start()
        webview.start()
        self._timer.stop()
        self._controller.stop()
        self._hotkeys_off()

    def _poll(self) -> None:
        if self._window is None or self._tracker is None:
            return
        players = self._tracker.current_players
        if players:
            self._push(players)

    def _push(self, players: list[dict]) -> None:
        if self._window is None:
            return
        body = self._html(players)
        if body == self._last_html:
            return
        self._last_html = body
        try:
            self._window.evaluate_js(f"updateOverlay({json.dumps(body)})")
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    def _html(self, players: list[dict]) -> str:
        if not players:
            return PLACEHOLDER_HTML

        selected = self._selected_playlist
        fetcher = self._tracker.rank_fetcher
        mode_label = selected.upper() if selected != "best" else "Best"

        cards = [
            f'<div class="mode-badge">'
            f"{mode_label}"
            f'<span class="mode-hint"> (F8)</span>'
            f"</div>"
        ]

        for player in players:
            cards.append(self._card(player, fetcher, selected))

        return f'<div class="cards-grid">{"".join(cards)}</div>'

    def _card(self, player: dict, fetcher, selected: str) -> str:
        raw_name = player.get("name", "Unknown")
        team = player.get("team", -1)
        key = f"{player.get('id', '')}|{raw_name}"
        entry = fetcher.get_cached(key)

        tier = "Fetching…"
        division = ""
        mmr = "-"
        tier_id = None
        division_number = 0

        if entry:
            best = entry.get("best")
            if selected != "best" and entry.get("playlists"):
                best = entry["playlists"].get(selected) or best
            if best:
                tier = best.get("tier", "Unranked")
                division = best.get("division", "")
                mmr_raw = best.get("mmr")
                mmr = str(mmr_raw) if mmr_raw is not None else "-"
                tier_id = best.get("tier_id")
                division_number = best.get("div_num", 0)

        display_tier = f"{tier} \u00b7 {division}" if division else tier

        return (
            f'<div class="card card-{team % 2}">'
            f"{self._icon(tier_id)}"
            "<div class=info>"
            f"<div class=name>{html_mod.escape(raw_name)}</div>"
            f"<div class=mmr>{mmr}</div>"
            f"<div class=tier>{html_mod.escape(display_tier)}</div>"
            "</div>"
            f"{self._bars(tier_id, division_number)}"
            "</div>"
        )

    def _icon(self, tier_id: int | None) -> str:
        if isinstance(tier_id, int):
            src = self._icon_cache.get(tier_id, "")
            if src:
                return (
                    f'<img class="rank-icon" src="{html_mod.escape(src)}"'
                    ' alt="" onerror="this.style.display=\'none\'">'
                )
        return "<div class=rank-img>NO<br>IMG</div>"

    @staticmethod
    def _bars(tier_id: int | None, division_number: int) -> str:
        if division_number <= 0 or not isinstance(tier_id, int):
            return ""
        color = rank_tier_color(tier_id)
        bars = "".join(
            f'<div class="division-bar" style="background:{color}"></div>'
            for _ in range(division_number)
        )
        return f'<div class="division-bars">{bars}</div>'

    def _hotkeys_on(self) -> None:
        if not self._keyboard:
            return
        try:
            import keyboard  # pylint: disable=import-outside-toplevel

            for action, hotkey in self._keyboard.items():
                callback = self._actions.get(action)
                if callback:
                    keyboard.add_hotkey(hotkey, callback)
            self._hotkey_registered = True
            log.info("hotkeys: %s", ", ".join(self._keyboard.values()))
        except Exception:  # pylint: disable=broad-exception-caught
            log.warning("keyboard not available; hotkeys disabled")

    def _hotkeys_off(self) -> None:
        if self._hotkey_registered:
            try:
                import keyboard  # pylint: disable=import-outside-toplevel

                keyboard.unhook_all_hotkeys()
            except Exception:  # pylint: disable=broad-exception-caught
                pass

    def _toggle(self) -> None:
        if not self._window:
            return
        self._hidden = not self._hidden
        if self._hidden:
            self._window.hide()
        else:
            self._window.show()
        log.info("window %s", "hidden" if self._hidden else "shown")

    def _next_list(self) -> None:
        self._move_list(1)

    def _prev_list(self) -> None:
        self._move_list(-1)

    def _move_list(self, delta: int) -> None:
        try:
            index = OVERLAY_PLAYLIST_CYCLE.index(self._selected_playlist)
        except ValueError:
            index = 0
        index = (index + delta) % len(OVERLAY_PLAYLIST_CYCLE)
        self._selected_playlist = OVERLAY_PLAYLIST_CYCLE[index]
        log.info("playlist: %s", self._selected_playlist)
        players = self._tracker.current_players
        if players:
            self._push(players)

    def _next_size(self) -> None:
        self._move_size(1)

    def _prev_size(self) -> None:
        self._move_size(-1)

    def _move_size(self, delta: int) -> None:
        self._size_index = (self._size_index + delta) % len(OVERLAY_SIZE_PRESETS)
        label, width, height = OVERLAY_SIZE_PRESETS[self._size_index]
        if self._window:
            self._window.resize(width, height)
        log.info("window size: %s (%dx%d)", label, width, height)

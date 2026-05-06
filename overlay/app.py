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
            with open(path, "rb") as fh:
                data = base64.b64encode(fh.read()).decode("ascii")
            cache[tier_id] = f"data:image/png;base64,{data}"
        except FileNotFoundError:
            pass
    log.info("Loaded %d rank icons into cache", len(cache))
    return cache


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
            frameless=True,
            resizable=True,
            on_top=True,
        )
        self._hotkeys_on()
        self._timer.start()
        webview.start()
        self._timer.stop()
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
        div_num = 0

        if entry:
            pd = entry.get("best")
            if selected != "best" and entry.get("playlists"):
                pd = entry["playlists"].get(selected) or pd
            if pd:
                tier = pd.get("tier", "Unranked")
                division = pd.get("division", "")
                m_val = pd.get("mmr")
                mmr = str(m_val) if m_val is not None else "-"
                tier_id = pd.get("tier_id")
                div_num = pd.get("div_num", 0)

        display_tier = f"{tier} \u00b7 {division}" if division else tier
        rank_img = self._icon(tier_id)
        bars_html = self._bars(tier_id, div_num)

        return (
            f'<div class="card card-{team % 2}">'
            f"{rank_img}"
            "<div class=info>"
            f"<div class=name>{html_mod.escape(raw_name)}</div>"
            f"<div class=mmr>{mmr}</div>"
            f"<div class=tier>{html_mod.escape(display_tier)}</div>"
            "</div>"
            f"{bars_html}"
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
    def _bars(tier_id: int | None, div_num: int) -> str:
        if div_num <= 0 or not isinstance(tier_id, int):
            return ""
        color = rank_tier_color(tier_id)
        bars = "".join(
            f'<div class="division-bar" style="background:{color}"></div>'
            for _ in range(div_num)
        )
        return f'<div class="division-bars">{bars}</div>'

    def _hotkeys_on(self) -> None:
        try:
            import keyboard  # pylint: disable=import-outside-toplevel

            keyboard.add_hotkey("ctrl+shift+o", self._toggle)
            keyboard.add_hotkey("F8", self._next_list)
            keyboard.add_hotkey("F9", self._next_size)
            self._hotkey_registered = True
            log.info("hotkeys: ctrl+shift+o, F8, F9")
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
        try:
            idx = OVERLAY_PLAYLIST_CYCLE.index(self._selected_playlist)
            next_idx = (idx + 1) % len(OVERLAY_PLAYLIST_CYCLE)
        except ValueError:
            next_idx = 0
        self._selected_playlist = OVERLAY_PLAYLIST_CYCLE[next_idx]
        log.info("playlist: %s", self._selected_playlist)
        players = self._tracker.current_players
        if players:
            self._push(players)

    def _next_size(self) -> None:
        self._size_index = (self._size_index + 1) % len(OVERLAY_SIZE_PRESETS)
        _label, w, h = OVERLAY_SIZE_PRESETS[self._size_index]
        if self._window:
            self._window.resize(w, h)
        log.info("window size: %s (%dx%d)", _label, w, h)

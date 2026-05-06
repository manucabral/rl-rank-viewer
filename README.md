# rl-rank-viewer

Personal project inspired by InGameRank, released in case it helps someone.

Since Rocket League added EAC support, BakkesMod plugins like InGameRank no longer work the same way.

Keyboard only for now. Xbox / PlayStation controller keybinds are not supported yet.

## Features

- Frameless always-on-top overlay
- Playlist switching: best / 1v1 / 2v2 / 3v3
- Resizable overlay window
- No internal plugin, no injection, no game file changes

## Disclaimer

This project is not affiliated with Psyonix, Epic Games, Rocket League, BakkesMod, InGameRank, Tracker.gg, or Tracker Network.

The proper way to access Tracker.gg data is through the [Tracker.gg Developer API](https://tracker.gg/developers).

This project does not use the official API. Use it at your own risk: your IP could be blocked, and your Tracker.gg account could be restricted or banned.

## Requirements

Rocket League Stats API must have been enabled https://www.rocketleague.com/en/developer/stats-api

## Setup & Run

Install dependencies:
```bash
pip install -r requirements.txt
```

Run:
```bash
python main.py
```

Use `-v` for debug logging:

```bash
python main.py -v
```

## Hotkeys

| Key | Action |
|-----|--------|
| F8 | Cycle playlist: best / 1v1 / 2v2 / 3v3 |
| F9 | Cycle window size |
| Ctrl+Shift+O | Hide / show overlay |

## Notes
- The Stats API exporter must be enabled before starting the overlay.
- Restart Rocket League after editing TAStatsAPI.ini.
- Tracker.gg data may depend on the player platform and profile visibility.
- If the overlay does not update, check that port 49123 is enabled and not blocked by another app or firewall.

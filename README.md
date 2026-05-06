# rl-rank-viewer

Personal project inspired by InGameRank, released in case it helps someone.

Since Rocket League added EAC support, BakkesMod plugins like InGameRank no longer work the same way.

Keyboard + controller support (Xbox and PS4). Bindings configurable via `bindings.json`.

## Features

- Playlist switching: best / 1v1 / 2v2 / 3v3
- Resizable overlay window
- No internal plugin, no injection, no game file changes

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

## Data mode

You can use:

**Official API** if a `.env` file exists with a `TRACKER_API_KEY`:

```
TRACKER_API_KEY=your-key-here
```

**Scraping** falls back automatically if no `.env` or no key is set

## Bindings

Edit `bindings.json` to change keyboard shortcuts or controller buttons.

```json
{
  "keyboard": {
    "toggle": "ctrl+shift+o",
    "playlist_next": "f8",
    "size_next": "f9"
  },
  "controller": {
    "toggle": "back",
    "playlist_next": "dpad_right",
    "playlist_prev": "dpad_left",
    "size_next": "dpad_up",
    "size_prev": "dpad_down"
  }
}
```

| Name | Xbox | PS4 |
|------|------|-----|
| `a` | A | Cross (×) |
| `b` | B | Circle (○) |
| `x` | X | Square (□) |
| `y` | Y | Triangle (△) |
| `lb` | Left bumper | L1 |
| `rb` | Right bumper | R1 |
| `back` | Back/View | Share |
| `start` | Start/Menu | Options |
| `ls` | Left stick click | L3 |
| `rs` | Right stick click | R3 |
| `dpad_up` | D-pad up | D-pad up |
| `dpad_down` | D-pad down | D-pad down |
| `dpad_left` | D-pad left | D-pad left |
| `dpad_right` | D-pad right | D-pad right |

If no controller is connected, it's silently ignored.

## Notes

- The Stats API must be enabled before starting the overlay.
- Restart Rocket League after editing `TAStatsAPI.ini`.
- Tracker.gg data depends on platform and profile visibility.
- If the overlay does not update, check that port 49123 is not blocked by firewall.

## Disclaimer

This project is not affiliated with Psyonix, Epic Games, Rocket League, BakkesMod, InGameRank, Tracker.gg, or Tracker Network.

Use it at your own risk. I'm not responsible for anything that happens to your accounts.


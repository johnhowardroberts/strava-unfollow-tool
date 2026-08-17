# Strava Unfollow Helper

A small local web app for bulk-unfollowing people on Strava. Strava's UI only lets
you unfollow one person at a time with several clicks each, which is painful if
you've been on the platform for years and follow hundreds of people you no longer
know. This gives you a checklist instead: scan your following list, tick who to
remove (or select-all and un-tick who to keep), and it works through them for you.

![screenshot placeholder](#) <!-- feel free to drop a screenshot here -->

## How it works

Strava's public developer API doesn't expose following/followers/unfollow at all
(those endpoints were removed in 2018 for privacy reasons). So this tool doesn't
use the API — it drives the same requests strava.com's own website makes:

1. It reads your Strava session cookie straight out of your browser's cookie
   store (via [`browser_cookie3`](https://pypi.org/project/browser-cookie3/)) —
   no password or API token needed, and nothing is stored anywhere.
2. It fetches your `strava.com/athletes/<you>/follows?type=following` pages
   (the same HTML your browser would render) and parses out each person's name,
   location, avatar, and internal "follow id".
3. When you hit unfollow, it sends the same `DELETE` request the "Unfollow"
   button on the site sends, with a randomized 2–4 second delay between each
   one so it behaves like a human clicking through the page rather than a bot
   hammering the site.

Because this rides on an undocumented, internal endpoint rather than the public
API, it's a bit outside the letter of Strava's terms of service on automated
access. It's intended for cleaning up your own account, at a human-like pace —
not for scraping other people's data or running unattended at scale. Use it at
your own risk; this project isn't affiliated with or endorsed by Strava.

## Setting this up via an AI coding agent

If you'd rather have an agent (Claude Code, Cursor, etc.) install and run this
for you instead of doing it by hand, see [AGENT_GUIDE.md](AGENT_GUIDE.md) — it
has a ready-to-paste prompt.

## Requirements

- Python 3.9+
- A desktop browser, logged into strava.com, on the same machine you run this on
  (Chrome by default — see [Using a different browser](#using-a-different-browser)
  for others)

## Setup

```bash
git clone https://github.com/<your-username>/strava-unfollow-tool.git
cd strava-unfollow-tool
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## Usage

```bash
./venv/bin/python app.py
```

Then open [http://127.0.0.1:5757](http://127.0.0.1:5757) in your browser and:

1. Click **Scan my following list** — this reads your cookies and pulls the
   full list (paginated, so it takes a little while for large lists).
   - On macOS, the first run will prompt for Keychain access so the script can
     decrypt Chrome's cookie store — click **Always Allow**.
2. Use the filter box, **Select all**, **Select none**, or **Invert** to pick
   who to unfollow.
3. Click **Unfollow selected**, confirm the count, and let it run. It processes
   one person every 2–4 seconds, so a few hundred people will take a while —
   leave the tab open and don't let your machine go to sleep (see below).

If it stops partway through (closed laptop lid, network blip, etc.), nothing is
lost — just reopen the page, scan again, and whoever's left is whoever hasn't
been unfollowed yet.

### Keeping your machine awake

A long-running batch will get killed if your computer sleeps mid-run.

- **macOS**: run it as `caffeinate -i ./venv/bin/python app.py` to block idle
  sleep (note this does *not* stop sleep from closing the lid — keep it open
  or stay plugged in).
- **Windows**: `powercfg /change standby-timeout-ac 0` (and `-dc` for battery),
  or just change your sleep settings in Settings → System → Power for the
  duration of the run.
- **Linux**: `systemd-inhibit --what=idle ./venv/bin/python app.py`, or disable
  suspend temporarily.

## Configuration

All optional, set as environment variables before running `app.py`:

| Variable | Default | Purpose |
|---|---|---|
| `STRAVA_UNFOLLOW_BROWSER` | `chrome` | Which browser to read cookies from (see below) |
| `STRAVA_UNFOLLOW_PORT` | `5757` | Local port to serve the app on |
| `STRAVA_UNFOLLOW_MIN_DELAY` / `STRAVA_UNFOLLOW_MAX_DELAY` | `2` / `4` | Seconds between each unfollow request |
| `STRAVA_ATHLETE_ID` | auto-detected | Your numeric Strava athlete ID, if auto-detection fails |

Example:

```bash
STRAVA_UNFOLLOW_BROWSER=firefox STRAVA_UNFOLLOW_MIN_DELAY=3 STRAVA_UNFOLLOW_MAX_DELAY=6 ./venv/bin/python app.py
```

### Using a different browser

Set `STRAVA_UNFOLLOW_BROWSER` to one of: `chrome`, `chromium`, `brave`, `edge`,
`vivaldi`, `opera`, `opera_gx`, `firefox`, `librewolf`, `arc`, `safari`, or
`auto` (tries every installed browser it can find and uses whichever has a
Strava session). This is handled by `browser_cookie3`, which supports Windows,
macOS, and Linux — see [its docs](https://pypi.org/project/browser-cookie3/)
for platform-specific quirks (e.g. Chromium-based browsers need to be closed
on some Linux setups, Safari cookie access varies by macOS version).

## Troubleshooting

- **"Couldn't read cookies from ..."** — make sure you're logged into
  strava.com in that browser on this machine, and approve any OS-level
  keychain/credential-manager prompt.
- **"No Strava session cookie found"** — same as above; your session may have
  expired. Log into strava.com again and retry.
- **"Couldn't auto-detect your athlete ID"** — set `STRAVA_ATHLETE_ID` (find
  it in the URL of your own Strava profile: `strava.com/athletes/<id>`).
- **Occasional single failures in the log** (e.g. connection reset) — usually
  a transient network blip, not a block. Just rerun "Unfollow selected" after
  the batch finishes; failed entries stay checked so it only retries those.
- **A wave of failures in a row** — stop and wait a while before retrying;
  that's more likely to be Strava rate-limiting or flagging the pattern.

## Project layout

```
app.py              Flask server: scan/unfollow endpoints, background job runner
strava_client.py     Cookie/session handling, HTML scraping, the unfollow request
templates/index.html Single-page checklist UI (vanilla JS, no build step)
```

## License

MIT — see [LICENSE](LICENSE).

import json
import os
import random
import re
import time
from dataclasses import dataclass
from typing import Callable, Optional

import browser_cookie3
import requests
from bs4 import BeautifulSoup

BASE = "https://www.strava.com"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# Browsers browser_cookie3 knows how to pull cookies from. Set STRAVA_UNFOLLOW_BROWSER
# to one of these (or "auto" to try all installed browsers) if you don't use Chrome.
SUPPORTED_BROWSERS = {
    "chrome": browser_cookie3.chrome,
    "chromium": browser_cookie3.chromium,
    "brave": browser_cookie3.brave,
    "edge": browser_cookie3.edge,
    "vivaldi": browser_cookie3.vivaldi,
    "opera": browser_cookie3.opera,
    "opera_gx": browser_cookie3.opera_gx,
    "firefox": browser_cookie3.firefox,
    "librewolf": browser_cookie3.librewolf,
    "arc": browser_cookie3.arc,
    "safari": browser_cookie3.safari,
}


@dataclass
class FollowedAthlete:
    athlete_id: str
    follow_id: str
    name: str
    location: str
    avatar: Optional[str]


class StravaSessionError(RuntimeError):
    pass


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    browser = os.environ.get("STRAVA_UNFOLLOW_BROWSER", "chrome").lower()
    try:
        if browser == "auto":
            cj = browser_cookie3.load(domain_name="strava.com")
        elif browser in SUPPORTED_BROWSERS:
            cj = SUPPORTED_BROWSERS[browser](domain_name="strava.com")
        else:
            raise StravaSessionError(
                f"Unknown STRAVA_UNFOLLOW_BROWSER '{browser}'. Supported: "
                f"{', '.join(sorted(SUPPORTED_BROWSERS))}, or 'auto'."
            )
    except StravaSessionError:
        raise
    except Exception as exc:
        raise StravaSessionError(
            f"Couldn't read cookies from {browser} ({exc}). Make sure you're logged "
            "into strava.com in that browser, and approve any OS keychain/credential "
            "prompt if one appears. See the README for browser-specific notes."
        ) from exc

    session.cookies.update(cj)
    if not any("session" in c.name for c in cj):
        raise StravaSessionError(
            f"No Strava session cookie found in {browser}. Log into strava.com in that "
            "browser, then retry. If you use a different browser, set STRAVA_UNFOLLOW_BROWSER."
        )
    return session


def get_csrf_token(session: requests.Session, referer_url: str) -> str:
    resp = session.get(referer_url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    meta = soup.find("meta", attrs={"name": "csrf-token"})
    if not meta or not meta.get("content"):
        raise StravaSessionError("Couldn't find a CSRF token on the page — session may be invalid.")
    return meta["content"]


def discover_athlete_id(session: requests.Session) -> str:
    override = os.environ.get("STRAVA_ATHLETE_ID")
    if override:
        return override

    resp = session.get(f"{BASE}/dashboard")
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for a in soup.find_all("a", href=re.compile(r"^/athletes/\d+$")):
        text = a.get_text(strip=True)
        if text in ("My Profile", "Profile"):
            return re.match(r"^/athletes/(\d+)$", a["href"]).group(1)
    raise StravaSessionError(
        "Couldn't auto-detect your athlete ID. Visit your own Strava profile and note "
        "the number in the URL (strava.com/athletes/<id>), then set the STRAVA_ATHLETE_ID "
        "environment variable to that number and retry."
    )


def _parse_follow_page(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen_follow_ids = set()
    for li in soup.find_all("li"):
        athlete_link = li.find("a", href=re.compile(r"^/athletes/\d+$"))
        follow_btn = li.find("button", attrs={"data-follow": True})
        if not athlete_link or not follow_btn:
            continue
        follow_id = follow_btn["data-follow"]
        if follow_id in seen_follow_ids:
            continue
        seen_follow_ids.add(follow_id)
        athlete_id = re.match(r"^/athletes/(\d+)$", athlete_link["href"]).group(1)
        name = athlete_link.get_text(strip=True)

        location = ""
        loc_el = li.find(class_=re.compile("location", re.I))
        if loc_el:
            location = loc_el.get_text(strip=True)

        avatar = None
        avatar_div = li.find(attrs={"data-react-props": True})
        if avatar_div:
            try:
                props = json.loads(avatar_div["data-react-props"])
                avatar = props.get("src")
            except (KeyError, json.JSONDecodeError):
                pass

        results.append(FollowedAthlete(athlete_id, follow_id, name, location, avatar))
    return results


def fetch_following(
    session: requests.Session,
    athlete_id: str,
    progress_cb: Optional[Callable[[int], None]] = None,
    max_pages: int = 60,
) -> list:
    all_results = {}
    for page in range(1, max_pages + 1):
        resp = session.get(
            f"{BASE}/athletes/{athlete_id}/follows",
            params={"type": "following", "page": page},
        )
        resp.raise_for_status()
        page_results = _parse_follow_page(resp.text)
        if not page_results:
            break
        for a in page_results:
            all_results[a.follow_id] = a
        if progress_cb:
            progress_cb(len(all_results))
        time.sleep(0.8 + random.uniform(0, 0.4))
    return list(all_results.values())


def unfollow(
    session: requests.Session,
    athlete_id: str,
    follow_id: str,
    csrf_token: str,
    referer_url: str,
) -> None:
    resp = session.delete(
        f"{BASE}/athletes/{athlete_id}/follows/{follow_id}",
        params={"stm_source": "stm-source-follow-follows-index"},
        headers={
            "X-CSRF-Token": csrf_token,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": referer_url,
            "Accept": "application/json, text/javascript, */*; q=0.01",
        },
    )
    if resp.status_code not in (200, 204):
        raise StravaSessionError(f"Unfollow failed ({resp.status_code}): {resp.text[:200]}")

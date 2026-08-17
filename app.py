import os
import random
import threading
import time
import uuid
from dataclasses import asdict

from flask import Flask, jsonify, render_template, request

import strava_client as sc

app = Flask(__name__)
app.jinja_env.auto_reload = True
app.config["TEMPLATES_AUTO_RELOAD"] = True

PORT = int(os.environ.get("STRAVA_UNFOLLOW_PORT", 5757))
MIN_DELAY = float(os.environ.get("STRAVA_UNFOLLOW_MIN_DELAY", 2))
MAX_DELAY = float(os.environ.get("STRAVA_UNFOLLOW_MAX_DELAY", 4))

STATE = {
    "session": None,
    "athlete_id": None,
    "csrf_token": None,
    "referer_url": None,
    "following": [],
    "scan_status": "idle",  # idle | scanning | done | error
    "scan_error": None,
    "scan_count": 0,
}

JOBS = {}


def _ensure_session():
    if STATE["session"] is None:
        STATE["session"] = sc.build_session()
        STATE["athlete_id"] = sc.discover_athlete_id(STATE["session"])
        STATE["referer_url"] = f"{sc.BASE}/athletes/{STATE['athlete_id']}/follows?type=following"
        STATE["csrf_token"] = sc.get_csrf_token(STATE["session"], STATE["referer_url"])


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/scan", methods=["POST"])
def api_scan():
    if STATE["scan_status"] == "scanning":
        return jsonify({"status": "scanning"})

    def run():
        STATE["scan_status"] = "scanning"
        STATE["scan_error"] = None
        STATE["scan_count"] = 0
        try:
            _ensure_session()

            def progress(n):
                STATE["scan_count"] = n

            following = sc.fetch_following(STATE["session"], STATE["athlete_id"], progress_cb=progress)
            following.sort(key=lambda a: a.name.lower())
            STATE["following"] = following
            STATE["scan_status"] = "done"
        except Exception as exc:
            STATE["scan_status"] = "error"
            STATE["scan_error"] = str(exc)

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/api/scan/status")
def api_scan_status():
    return jsonify(
        {
            "status": STATE["scan_status"],
            "count": STATE["scan_count"],
            "error": STATE["scan_error"],
            "athletes": [asdict(a) for a in STATE["following"]] if STATE["scan_status"] == "done" else [],
        }
    )


@app.route("/api/unfollow", methods=["POST"])
def api_unfollow():
    follow_ids = request.json.get("follow_ids", [])
    names = request.json.get("names", {})
    by_id = {a.follow_id: a for a in STATE["following"]}
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"done": 0, "total": len(follow_ids), "results": [], "finished": False}

    def run():
        try:
            _ensure_session()
        except Exception as exc:
            JOBS[job_id]["results"] = [
                {"follow_id": fid, "name": names.get(fid, fid), "ok": False, "error": str(exc)}
                for fid in follow_ids
            ]
            JOBS[job_id]["done"] = len(follow_ids)
            JOBS[job_id]["finished"] = True
            return
        for fid in follow_ids:
            athlete = by_id.get(fid)
            name = athlete.name if athlete else names.get(fid, fid)
            try:
                sc.unfollow(STATE["session"], STATE["athlete_id"], fid, STATE["csrf_token"], STATE["referer_url"])
                JOBS[job_id]["results"].append({"follow_id": fid, "name": name, "ok": True})
            except Exception as exc:
                JOBS[job_id]["results"].append({"follow_id": fid, "name": name, "ok": False, "error": str(exc)})
            JOBS[job_id]["done"] += 1
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        JOBS[job_id]["finished"] = True

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/unfollow/status")
def api_unfollow_status():
    job_id = request.args.get("job_id")
    return jsonify(JOBS.get(job_id, {"error": "unknown job"}))


if __name__ == "__main__":
    app.run(port=PORT, debug=False)

# Agent setup guide

This file is meant to be copy-pasted directly into a coding agent (Claude Code,
Cursor, Copilot, etc.) as a prompt. If you're a human reading this in a browser:
copy everything in the code block below and paste it as your message to the
agent.

---

## Prompt to paste into your agent

```
Set up and run the "Strava Unfollow Helper" tool for me from this repo:
https://github.com/johnhowardroberts/strava-unfollow-tool

It's a local Flask web app that reads my Strava session cookie from my browser,
scrapes my "following" list, and lets me bulk-unfollow people through a
checklist UI. No API keys or passwords involved — it just needs a browser on
this machine that's already logged into strava.com.

Please:

1. Check for git and Python 3.9+. If either is missing, help me install them
   (ask me first if it needs elevated permissions or a package manager I don't
   have, like Homebrew).

2. Clone the repo into the current directory (or ask me where I'd like it),
   then create a virtualenv and install requirements.txt into it.

3. Ask me which desktop browser I have logged into strava.com on this machine
   (Chrome, Firefox, Brave, Edge, Safari, Vivaldi, Opera, etc. are all
   supported). Set the STRAVA_UNFOLLOW_BROWSER environment variable to that
   browser when running the app (it defaults to "chrome" otherwise).

4. Start the app (`python app.py` inside the venv) as a long-running background
   process, and tell me the URL to open (http://127.0.0.1:5757 by default).
   Since this can run for several minutes to hours depending on how many
   people I'm unfollowing, please also prevent this machine from sleeping for
   the duration — e.g. wrap the run with `caffeinate -i` on macOS,
   `systemd-inhibit --what=idle` on Linux, or tell me how to temporarily
   disable sleep on Windows. Let me know this only blocks *idle* sleep, not a
   closed laptop lid — I should keep it open or stay plugged in.

5. IMPORTANT — do not try to open the app in a browser you're driving
   yourself (e.g. via an automated/headless browser tool), and do not select
   who to unfollow or click "Unfollow selected" on my behalf. That decision
   and that action are mine to make in my own real, already-logged-in
   browser — please just get the server running and tell me the URL to open
   myself.

6. Watch the server output for errors while I use it and help me debug if
   something goes wrong. Common issues and what they mean are in the repo's
   README.md "Troubleshooting" section — check there first. A few worth
   knowing up front:
   - First run on macOS may prompt for Keychain access to decrypt the
     browser's cookie store — that's expected, I should click Allow.
   - If the process dies mid-run, nothing already-unfollowed is lost; I just
     reopen the page, click Scan again, and continue with whoever's left.
   - If I edit the Python files while the server's running, it needs a
     restart to pick up the change (only the HTML template hot-reloads).

7. Tell me plainly, before I start clicking through people to unfollow, that
   this tool works by replaying the same request Strava's own website makes
   (not the public API, which doesn't expose unfollow at all) — so it's a bit
   outside the letter of Strava's terms of service on automated access, even
   though it's just automating my own account at a human pace. That's my call
   to make, I just want it surfaced.

Once the server's running and I've confirmed I can load the page, you're done
— I'll take it from there.
```

---

## Notes for repo maintainers

The prompt above intentionally keeps the agent scoped to *environment setup*
(installing deps, starting the process, keeping the machine awake, debugging
crashes) and explicitly keeps it out of the *decision* (who to unfollow) and
the *execution* (clicking the button that does it). That split exists because:

- Selecting who to unfollow is a judgment call about the user's own
  relationships — not something to delegate to an agent's guesswork.
- Clicking "Unfollow selected" fires real, individually-hard-to-reverse
  requests against the user's live Strava account. Keeping a human's hands on
  that specific action, in their own authenticated browser tab, is the same
  boundary this project's own development process followed (see the commit
  history / project discussion) — an agent automating its own browser to
  click through the checklist would be a meaningfully different, riskier
  thing than an agent running `pip install` and `python app.py`.

If you fork this and change that boundary intentionally, please keep it
explicit in whatever guide you ship, rather than silent.

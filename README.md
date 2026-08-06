# brightspace-weekly-planner

A local Python app that checks your Fanshawe Brightspace courses, finds what's
due this week, and generates a Markdown report, JSON data file, and an HTML
dashboard.

## What It Does

- Opens Brightspace in a headed Chromium browser (visible on your Windows desktop
  via WSLg)
- Lets you manually log in and complete MFA
- Reuses your saved browser profile so you only do MFA once (until session expires)
- Scans your active courses for items due this week
- Generates `weekly_due_report.md`, `weekly_due_report.json`, `dashboard.html`,
  and `run_log.txt` inside the `output/` folder

## Why Persistent Playwright Profile

Brightspace uses multi-factor authentication (MFA). There is no way to automate
that safely. Instead, this app uses a dedicated Playwright persistent browser
profile:

- First run: a headed Chromium window opens, you log in and complete MFA manually.
- Future runs: the saved profile reuses your authenticated session.
- When the session expires: the app pauses and asks you to log in again.

Your session cookies stay **local only**. They are never committed to git,
printed to logs, or uploaded anywhere.

## Paths

| Purpose | Windows Path | WSL Path |
|---------|-------------|----------|
| Project root | `C:\Bin\SideProjs\brightspace-weekly-planner` | `/mnt/c/Bin/SideProjs/brightspace-weekly-planner` |
| Browser profile | (WSL path) | `/mnt/c/Bin/SideProjs/brightspace-weekly-planner/.local_browser_profile` |
| Reports | (WSL path) | `/mnt/c/Bin/SideProjs/brightspace-weekly-planner/output` |
| Site map | (WSL path) | `/mnt/c/Bin/SideProjs/brightspace-weekly-planner/output/brightspace_site_map.json` |

## Prerequisites

- Python 3.11+
- Playwright Chromium (`playwright install chromium`)
- For the `.bat` launchers only: WSL with a distro installed, plus WSLg for the
  headed browser. The launchers are thin wrappers that call
  `wsl.exe -- bash run_planner.sh`, so on a machine with no WSL distro they fail
  immediately. The Python package itself has no WSL dependency and runs fine on
  native Windows, Linux and macOS — see below.

## Install

Under WSL or Linux:

```bash
cd /mnt/c/Bin/SideProjs/brightspace-weekly-planner
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

On native Windows, skip the `.bat` files and drive the module directly:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
$env:PYTHONPATH = "$PWD\src"
python -m brightspace_planner.main sample-report
```

Every command in "How to Run" below works the same way once `PYTHONPATH`
includes `src`.

## Configuration

Copy `.env.example` to `.env` and customise:

```bash
cp .env.example .env
```

Key settings:

- `BRIGHTSPACE_URL` — your Brightspace homepage URL
- `OUTPUT_FOLDER` — where reports are saved
- `PLAYWRIGHT_PROFILE_DIR` — persistent browser profile directory
- `HEADLESS` — keep `false` so you can see and interact with the browser
- `WEEK_START_DATE` / `WEEK_END_DATE` — optional ISO dates; defaults to
  Monday–Sunday of the current week

If set, `BRIGHTSPACE_USERNAME` and `BRIGHTSPACE_PASSWORD` are only used as hints;
the app still requires you to manually complete MFA in the browser.

## How to Run

### 1. Test the GUI

Opens headed Chromium through WSLg and navigates to Brightspace to confirm the
browser appears on your Windows desktop.

```bash
python -m brightspace_planner.main gui-test
```

### 2. First-Time Login / MFA Setup

Opens headed Chromium, navigates to Brightspace, and waits for you to log in and
complete MFA. The persistent profile is saved for future runs.

```bash
python -m brightspace_planner.main auth
```

Leave the browser window open until you see the Brightspace homepage after fully
logging in. The app will detect when you have reached the home page.

### 3. Sample Report (No Brightspace needed)

Generates reports from fake/sample data so you can verify the report/dashboard
pipeline works before logging into Brightspace.

```bash
python -m brightspace_planner.main sample-report
```

### 4. Weekly Scan

Uses the persistent browser profile to check due work for the configured week.

```bash
python -m brightspace_planner.main scan
```

### 5. Regenerate Dashboard

Regenerates `dashboard.html` from the most recent `weekly_due_report.json`.

```bash
python -m brightspace_planner.main dashboard
```

## Hermes / Site Map Discovery

Before the app can scan efficiently, Hermes performs an initial read-only
exploration of your Brightspace:

1. Opens Brightspace using the persistent profile.
2. Logs in (you complete MFA if needed).
3. Explores the homepage, active courses, assignments, discussions, quizzes,
   content modules, calendar, and announcements.
4. Saves a local site map to `output/brightspace_site_map.json`.

The app reads this map during `scan` to know which pages to visit instead of
hard-coding Brightspace selectors.

**The real site map contains your course names and links. It is NOT committed to
git.** The repo includes only a fake/example schema.

To refresh the log in later (if MFA is required again):

```bash
python -m brightspace_planner.main auth
```

When the session expires the scan will pause and tell you to run `auth` again.

## Where Reports Are Saved

All output lives in:

```
/mnt/c/Bin/SideProjs/brightspace-weekly-planner/output/
```

- `weekly_due_report.md` — human-readable Markdown summary
- `weekly_due_report.json` — structured JSON data
- `dashboard.html` — open in any browser (single file, no server needed)
- `run_log.txt` — append-only log of scan runs
- `brightspace_site_map.json` — local site map (not committed)

## How to Open the Dashboard

From Windows Explorer:

```
C:\Bin\SideProjs\brightspace-weekly-planner\output\dashboard.html
```

Or from WSL:

```bash
explorer.exe "$(wslpath -w /mnt/c/Bin/SideProjs/brightspace-weekly-planner/output/dashboard.html)"
```

## What Files Are Ignored by Git

The following are **never** committed:

- `.env` and real config files
- `secrets/` directory
- `output/` directory
- `.local_browser_profile/` directory
- Playwright traces and screenshots
- Cookies, tokens, storage state files
- Downloaded Brightspace files/attachments
- Any file containing password, token, cookie, session, or authorization data

## What to Do If Brightspace Asks for MFA Again

Sessions expire. When that happens:

1. Run `python -m brightspace_planner.main auth`
2. Complete MFA in the opened browser window
3. Run `python -m brightspace_planner.main scan` again

"""
Pull the Firestore `events` and `feedback` collections (site + Telegram bot) and
report on them.

Two stages, deliberately separable so the report can be rebuilt without re-reading
Firestore:
  1. fetch  — dumps every event to data/usage/events_<YYYY-MM-DD>.json (artifact of record)
  2. report — aggregates that dump into data/usage/usage_summary.json + report.html

Events are written by web/lib/log.ts (source: home/watch/findname) and
bot/src/log.ts (source: bot). Both are pseudonymous: the site's sessionId is a
per-tab UUID, the bot's is a truncated sha256 of the Telegram user id — so bot
"sessions" are stable people and site "sessions" are visits. Do not add them up.

Usage:
  uv run --group firebase python scripts/non_essential/report_usage.py           # fetch + report
  uv run python scripts/non_essential/report_usage.py --from-dump <path>         # report only
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
USAGE_DIR = ROOT / "data" / "usage"
SA_KEY = ROOT / "internal" / "firebase-sa-kargin-archive.json"
PROJECT = "kargin-archive"

(ROOT / "logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(ROOT / "logs" / "report_usage.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("report_usage")


def fetch_events() -> list[dict]:
    """Stream the whole events collection. Fails loudly — no partial reports."""
    from google.cloud import firestore

    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        if not SA_KEY.exists():
            raise RuntimeError(
                f"no credentials: set GOOGLE_APPLICATION_CREDENTIALS or place the key at {SA_KEY}"
            )
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(SA_KEY)

    db = firestore.Client(project=PROJECT)
    out: list[dict] = []
    for snap in db.collection("events").stream():
        d = snap.to_dict() or {}
        ts = d.get("ts")
        out.append(
            {
                "id": snap.id,
                "ts": ts.isoformat() if hasattr(ts, "isoformat") else None,
                "type": d.get("type"),
                "source": d.get("source"),
                "sessionId": d.get("sessionId"),
                "query": d.get("query"),
                "mode": d.get("mode"),
                "filters": d.get("filters"),
                "resultCount": d.get("resultCount"),
                "sketchId": d.get("sketchId"),
                "ua": d.get("ua"),
            }
        )
    out.sort(key=lambda e: e["ts"] or "")
    log.info(f"fetched {len(out)} events from {PROJECT}/events")
    return out


def fetch_feedback() -> list[dict]:
    """Visitor reports. Clients can only create these, so reading needs the admin SDK."""
    from google.cloud import firestore

    db = firestore.Client(project=PROJECT)
    out: list[dict] = []
    for snap in db.collection("feedback").stream():
        d = snap.to_dict() or {}
        ts = d.get("ts")
        out.append(
            {
                "id": snap.id,
                "ts": ts.isoformat() if hasattr(ts, "isoformat") else None,
                "kind": d.get("kind"),
                "message": d.get("message"),
                "query": d.get("query"),
                "sketchId": d.get("sketchId"),
                "contact": d.get("contact"),
                "source": d.get("source"),
            }
        )
    out.sort(key=lambda e: e["ts"] or "")
    log.info(f"fetched {len(out)} feedback reports")
    return out


def device_of(ua: str | None) -> str:
    if not ua:
        return "unknown"
    if ua == "telegram-bot":
        return "bot"
    u = ua.lower()
    if "ipad" in u or "tablet" in u:
        return "tablet"
    if "mobi" in u or "iphone" in u or "android" in u:
        return "mobile"
    return "desktop"


def summarise(events: list[dict], sketch_titles: dict[str, str]) -> dict:
    site = [e for e in events if e.get("source") != "bot"]
    bot = [e for e in events if e.get("source") == "bot"]

    def searches(rows: list[dict]) -> list[dict]:
        return [e for e in rows if e.get("type") == "search" and (e.get("query") or "").strip()]

    def query_table(rows: list[dict]) -> list[dict]:
        """Distinct queries with how often they ran and what they returned."""
        agg: dict[str, dict] = {}
        for e in searches(rows):
            q = e["query"].strip()
            a = agg.setdefault(q, {"query": q, "count": 0, "resultCount": e.get("resultCount")})
            a["count"] += 1
            if e.get("resultCount") is not None:
                a["resultCount"] = e["resultCount"]
        return sorted(agg.values(), key=lambda a: (-a["count"], a["query"]))

    days = Counter(e["ts"][:10] for e in events if e.get("ts"))
    opened = Counter(e["sketchId"] for e in events if e.get("type") == "open" and e.get("sketchId"))

    def sessions(rows: list[dict]) -> int:
        return len({e["sessionId"] for e in rows if e.get("sessionId")})

    site_q, bot_q = query_table(site), query_table(bot)
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "totals": {
            "events": len(events),
            "site": len(site),
            "bot": len(bot),
            "siteVisits": sessions(site),
            "botPeople": sessions(bot),
            "firstEvent": events[0]["ts"] if events else None,
            "lastEvent": events[-1]["ts"] if events else None,
            "activeDays": len(days),
        },
        "byType": dict(Counter(e.get("type") or "?" for e in events).most_common()),
        "bySource": dict(Counter(e.get("source") or "?" for e in events).most_common()),
        "byDevice": dict(Counter(device_of(e.get("ua")) for e in events).most_common()),
        "byDay": dict(sorted(days.items())),
        "siteQueries": site_q,
        "botQueries": bot_q,
        "zeroResultQueries": [q for q in site_q + bot_q if q["resultCount"] == 0],
        "filtersUsed": dict(
            Counter(e["filters"] for e in events if e.get("type") == "filter" and e.get("filters")).most_common()
        ),
        "topOpened": [
            {"sketchId": sid, "count": n, "title": sketch_titles.get(sid, sid)}
            for sid, n in opened.most_common(20)
        ],
    }


def load_titles() -> dict[str, str]:
    p = ROOT / "web" / "public" / "data" / "sketches.json"
    if not p.exists():
        log.warning(f"{p} missing — opened sketches will show ids only")
        return {}
    return {s["id"]: s.get("title", s["id"]) for s in json.loads(p.read_text(encoding="utf-8"))}


# ---------------------------------------------------------------- report

def bar_rows(data: dict[str, int], colour: str) -> str:
    """Horizontal CSS bars with the value labelled on the bar itself."""
    if not data:
        return '<p class="empty">— դատարկ —</p>'
    top = max(data.values()) or 1
    out = []
    for label, n in data.items():
        out.append(
            f'<div class="bar-row"><span class="bar-label">{html.escape(str(label))}</span>'
            f'<span class="bar-track"><span class="bar" style="width:{n / top * 100:.1f}%;'
            f'background:{colour}">{n}</span></span></div>'
        )
    return "".join(out)


def query_rows(rows: list[dict]) -> str:
    if not rows:
        return '<tr><td colspan="3" class="empty">no searches recorded</td></tr>'
    out = []
    for r in rows:
        rc = r["resultCount"]
        cls = "zero" if rc == 0 else ""
        shown = "—" if rc is None else f"{rc}"
        out.append(
            f'<tr class="{cls}"><td>{html.escape(r["query"])}</td>'
            f"<td class=num>{r['count']}</td><td class=num>{shown}</td></tr>"
        )
    return "".join(out)


def build_html(s: dict) -> str:
    t = s["totals"]
    span = "—"
    if t["firstEvent"] and t["lastEvent"]:
        span = f"{t['firstEvent'][:16].replace('T', ' ')} → {t['lastEvent'][:16].replace('T', ' ')} UTC"
    opened = "".join(
        f'<tr><td>{html.escape(r["title"])}</td><td class=num>{r["count"]}</td></tr>'
        for r in s["topOpened"]
    ) or '<tr><td colspan="2" class="empty">no sketch opens recorded</td></tr>'
    filters = "".join(
        f"<tr><td><code>{html.escape(k)}</code></td><td class=num>{v}</td></tr>"
        for k, v in s["filtersUsed"].items()
    ) or '<tr><td colspan="2" class="empty">no filter use recorded</td></tr>'

    return f"""<!doctype html><html lang=hy><meta charset=utf-8>
<title>Kargin — usage</title>
<style>
  :root{{--red:#D90012;--blue:#0033A0;--orange:#F2A800;--ink:#1A1410;--paper:#FBF3E2;--muted:#8A7C64}}
  *{{box-sizing:border-box}}
  body{{margin:0;padding:32px;background:var(--paper);color:var(--ink);
       font:15px/1.5 system-ui,'Segoe UI',sans-serif;max-width:1000px}}
  h1{{margin:0 0 4px;font-size:30px}}
  h2{{margin:34px 0 10px;font-size:18px;border-bottom:2px solid var(--ink);padding-bottom:5px}}
  .sub{{color:var(--muted);margin:0 0 22px}}
  .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:12px}}
  .card{{border:2px solid var(--ink);border-radius:10px;background:#fff;padding:12px 14px;
        box-shadow:4px 4px 0 var(--ink)}}
  .card .n{{font-size:27px;font-weight:800;line-height:1.1}}
  .card .l{{font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-top:3px}}
  table{{border-collapse:collapse;width:100%;table-layout:fixed;background:#fff;
        border:2px solid var(--ink);border-radius:8px;overflow:hidden}}
  th,td{{padding:7px 10px;border-bottom:1px solid #0002;text-align:left;
        overflow:hidden;text-overflow:ellipsis}}
  th{{background:#0000000d;font-size:11px;letter-spacing:.09em;text-transform:uppercase}}
  td.num,th.num{{text-align:right;font-variant-numeric:tabular-nums}}
  tr.zero td{{background:#D900120f}}
  tr.zero td:first-child::after{{content:" (0 արդյունք)";color:var(--red);font-size:11px}}
  .bar-row{{display:flex;align-items:center;gap:9px;margin:4px 0}}
  .bar-label{{width:132px;flex:none;font-size:12px;font-weight:600;text-align:right;
             overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
  .bar-track{{flex:1;background:#0000000a;border-radius:3px}}
  .bar{{display:block;padding:2px 7px;border-radius:3px;color:#fff;font-size:11px;
       font-weight:700;text-align:right;min-width:26px}}
  .empty{{color:var(--muted);font-style:italic}}
  .note{{background:#fff;border-left:4px solid var(--orange);padding:10px 14px;margin:14px 0;
        font-size:13px;color:#000a}}
  .cols{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}
  @media(max-width:720px){{.cols{{grid-template-columns:1fr}}body{{padding:18px}}}}
</style>
<h1>Կարգին — usage</h1>
<p class=sub>{span} · {t['activeDays']} active day(s) · generated {s['generatedAt'][:16].replace('T', ' ')} UTC</p>

<div class=cards>
  <div class=card><div class=n style="color:var(--red)">{t['events']}</div><div class=l>events</div></div>
  <div class=card><div class=n style="color:var(--blue)">{t['site']}</div><div class=l>from site</div></div>
  <div class=card><div class=n style="color:var(--orange)">{t['bot']}</div><div class=l>from bot</div></div>
  <div class=card><div class=n>{t['siteVisits']}</div><div class=l>site visits</div></div>
  <div class=card><div class=n>{t['botPeople']}</div><div class=l>bot users</div></div>
</div>
<div class=note><b>Counting caveat.</b> A site "visit" is one browser tab (sessionStorage UUID, new on
every tab and after a browser restart). A bot "user" is a hashed Telegram id, stable forever. The two
are not the same unit and must not be summed.</div>

<h2>Events per day</h2>
{bar_rows(s['byDay'], 'var(--blue)')}

<div class=cols>
  <div><h2>By type</h2>{bar_rows(s['byType'], 'var(--red)')}</div>
  <div><h2>By surface</h2>{bar_rows(s['bySource'], 'var(--orange)')}</div>
</div>

<h2>By device</h2>
{bar_rows(s['byDevice'], 'var(--blue)')}

<div class=cols>
  <div>
    <h2>Site searches ({len(s['siteQueries'])} distinct)</h2>
    <table><colgroup><col style="width:56%"><col style="width:22%"><col style="width:22%"></colgroup>
    <tr><th>query</th><th class=num>times</th><th class=num>results</th></tr>
    {query_rows(s['siteQueries'])}</table>
  </div>
  <div>
    <h2>Bot searches ({len(s['botQueries'])} distinct)</h2>
    <table><colgroup><col style="width:56%"><col style="width:22%"><col style="width:22%"></colgroup>
    <tr><th>query</th><th class=num>times</th><th class=num>results</th></tr>
    {query_rows(s['botQueries'])}</table>
  </div>
</div>

<h2>Most opened sketches</h2>
<table><colgroup><col style="width:80%"><col style="width:20%"></colgroup>
<tr><th>sketch</th><th class=num>opens</th></tr>{opened}</table>

<h2>Filters used</h2>
<table><colgroup><col style="width:80%"><col style="width:20%"></colgroup>
<tr><th>filter</th><th class=num>times</th></tr>{filters}</table>
</html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from-dump", type=Path, help="skip Firestore, aggregate this events dump")
    ap.add_argument("--open", action="store_true", help="open the report when done")
    args = ap.parse_args()

    USAGE_DIR.mkdir(parents=True, exist_ok=True)
    reports: list[dict] = []
    if args.from_dump:
        events = json.loads(args.from_dump.read_text(encoding="utf-8"))
        log.info(f"loaded {len(events)} events from {args.from_dump}")
    else:
        events = fetch_events()
        dump = USAGE_DIR / f"events_{datetime.now(timezone.utc):%Y-%m-%d}.json"
        dump.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info(f"raw dump -> {dump}")

        reports = fetch_feedback()
        (USAGE_DIR / "feedback.json").write_text(
            json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # Printed in full, not counted: these are sentences a person wrote for us,
        # and there will never be so many that reading them is a burden.
        for r in reports:
            when = (r["ts"] or "")[:16].replace("T", " ")
            where = r.get("sketchId") or r.get("query") or "—"
            log.info(f"REPORT [{r.get('kind')}] {when} ({r.get('source')}, {where}): {r.get('message')}")
            if r.get("contact"):
                log.info(f"        reply to: {r['contact']}")

    summary = summarise(events, load_titles())
    (USAGE_DIR / "usage_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = USAGE_DIR / "report.html"
    report.write_text(build_html(summary), encoding="utf-8")
    log.info(f"summary -> {USAGE_DIR / 'usage_summary.json'}   report -> {report}")

    t = summary["totals"]
    log.info(
        f"{t['events']} events ({t['site']} site / {t['bot']} bot), "
        f"{t['siteVisits']} site visits, {t['botPeople']} bot users, {t['activeDays']} active days"
    )
    log.info(f"types: {summary['byType']}   devices: {summary['byDevice']}")
    if args.open and sys.platform == "win32":
        os.startfile(report)  # noqa: S606


if __name__ == "__main__":
    main()

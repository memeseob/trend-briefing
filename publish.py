"""Publish a trend report to the public site (GitHub Pages) and optionally ping ntfy.

Usage: python -X utf8 publish.py <report.json> [--notify "message"]
<report.json> is {"kind","date","title","createdAt","markdown"} (same as the old db doc).
Writes reports/<id>.md, reports/<id>.thumbs.json (TikTok only; YouTube loads straight from ytimg),
rebuilds reports/index.json, commits and pushes. --notify sends one ntfy push that opens the report.
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

SITE = "https://memeseob.github.io/trend-briefing/"
TOPIC = "trend-6d1gu8jt"
ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
META = ("kind", "date", "title", "createdAt")


def report_id(rep: dict) -> str:
    """Return the report's id, e.g. daily-2026-10-30."""
    return f"{rep.get('kind', 'daily')}-{rep['date']}"


def build_index(metas: list[dict]) -> list[dict]:
    """Sort report metadata newest first (weekly before daily on the same date)."""
    return sorted(metas, key=lambda m: (m["date"], m.get("kind") == "weekly"), reverse=True)


def tiktok_thumbs(markdown: str) -> dict[str, str]:
    """Download TikTok thumbnails as data URIs; their CDN links expire, YouTube's don't."""
    sys.path.insert(0, str(ROOT.parent))
    import thumbs  # shared with the old db flow

    out: dict[str, str] = {}
    for key, url in thumbs.links(markdown):
        if key.startswith("tt:"):
            try:
                out[key] = thumbs.data_uri(thumbs.fetch(key, url, False))
            except Exception as e:  # a missing photo is fine, the card shows a placeholder
                print("skip", key, e)
    return out


def write_report(rep: dict) -> str:
    """Write the report's files and rebuild index.json; return its id."""
    rid = report_id(rep)
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / f"{rid}.md").write_text(rep["markdown"], encoding="utf-8")
    (REPORTS / f"{rid}.meta.json").write_text(
        json.dumps({"id": rid, **{k: rep.get(k) for k in META}}, ensure_ascii=False), encoding="utf-8")
    imgs = tiktok_thumbs(rep["markdown"])
    if imgs:
        (REPORTS / f"{rid}.thumbs.json").write_text(json.dumps(imgs), encoding="utf-8")
    metas = [json.loads(p.read_text(encoding="utf-8")) for p in REPORTS.glob("*.meta.json")]
    (REPORTS / "index.json").write_text(json.dumps(build_index(metas), ensure_ascii=False), encoding="utf-8")
    return rid


def push(rid: str) -> None:
    """Commit and push the site repo."""
    git = ["git", "-C", str(ROOT)]
    subprocess.run([*git, "add", "-A"], check=True)
    if subprocess.run([*git, "diff", "--cached", "--quiet"]).returncode:
        subprocess.run([*git, "commit", "-q", "-m", f"report {rid}"], check=True)
    subprocess.run([*git, "push", "-q"], check=True)


def notify(message: str, rid: str, title: str) -> None:
    """Send one ntfy push; tapping it opens the report."""
    link = f"{SITE}#{rid}"
    body = {"topic": TOPIC, "title": title, "message": f"{message}\n{link}",
            "click": link, "tags": ["bar_chart"]}
    req = urllib.request.Request("https://ntfy.sh/", data=json.dumps(body).encode("utf-8"), method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        print("ntfy", r.status)


def main(argv: list[str]) -> None:
    """Publish the report file in argv[0]; notify if --notify is given."""
    rep = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    rid = write_report(rep)
    push(rid)
    print("published", SITE + "#" + rid)
    if "--notify" in argv:
        title = "주간 트렌드 보고" if rep.get("kind") == "weekly" else "아침 트렌드 브리핑"
        notify(argv[argv.index("--notify") + 1], rid, title)


if __name__ == "__main__":
    main(sys.argv[1:])

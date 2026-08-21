#!/usr/bin/env python3
"""
check_references.py

Validate that every reference link in the Fulcrum RVx paper resolves.

- Parses the "Reference links (quick index)" block of the manuscript, so the
  checker always reflects the current bibliography with no hand-maintained list.
- Checks each URL with a real browser User-Agent, follows redirects, and falls
  back from HEAD to a ranged GET for servers that reject HEAD (many publishers do).
- Runs once by default, or repeatedly with --interval for an unattended watch.
- Writes a machine-readable JSON report and a human-readable console summary.
- Exits non-zero when any link is broken, so it can gate a build or a CI step.

Dependency-free: standard library only (matches the paper's reference code).

Examples
--------
    python check_references.py
    python check_references.py --interval 3600            # re-check hourly
    python check_references.py --interval 21600 --quiet   # every 6h, terse
    python check_references.py --timeout 20 --workers 12
    python check_references.py --json report.json
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import datetime as dt
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
# Manuscript lives in the parent folder (this script was moved into code/).
PARENT = os.path.dirname(HERE)
DEFAULT_MD = os.path.join(PARENT, "Fulcrum-RVx-Research-Paper-Hardened.md")

# A realistic UA; some publisher CDNs (Cambridge, IEEE) refuse the urllib default.
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Match a numbered quick-index line and pull the reference number plus every URL on it.
REF_LINE = re.compile(r"^\s*(\d+)\.\s+(.*)$")
# Capture greedily to the next whitespace; parentheses are trimmed intelligently
# afterwards so DOIs that legitimately contain them (e.g. 10.1016/S0166-4115(08)62386-9)
# are preserved while a trailing ")" from "(preprint https://...)" is removed.
URL_RE = re.compile(r"https?://\S+")


def clean_url(u: str) -> str:
    """Trim trailing sentence punctuation and only *unbalanced* closing parens."""
    u = u.rstrip(".,;")
    while u.endswith(")") and u.count(")") > u.count("("):
        u = u[:-1].rstrip(".,;")
    return u


def parse_references(md_path: str) -> list[dict]:
    """Return [{'num': int, 'urls': [str, ...], 'text': str}] from the quick index."""
    with open(md_path, encoding="utf-8") as fh:
        lines = fh.readlines()

    in_index = False
    refs: list[dict] = []
    for line in lines:
        if line.startswith("### Reference links (quick index)"):
            in_index = True
            continue
        if in_index and line.startswith("### Full citations"):
            break
        if not in_index:
            continue
        m = REF_LINE.match(line)
        if not m:
            continue
        urls = [clean_url(u) for u in URL_RE.findall(line)]
        if urls:
            refs.append({"num": int(m.group(1)), "urls": urls, "text": m.group(2).strip()})
    return refs


def _request(url: str, method: str, timeout: float, ctx: ssl.SSLContext):
    headers = {
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        # Ask for only the first byte so a GET fallback stays cheap.
        "Range": "bytes=0-0",
    }
    req = urllib.request.Request(url, method=method, headers=headers)
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def check_url(url: str, timeout: float, retries: int = 2) -> dict:
    """Check a URL with retries for transient failures (timeouts, DNS blips)."""
    res = _check_url_once(url, timeout)
    attempt = 1
    # Only retry genuine transient failures, not real HTTP errors.
    while attempt <= retries and (not res["ok"]) and res["status"] is None:
        time.sleep(1.5 * attempt)  # linear backoff
        res = _check_url_once(url, timeout * (1 + attempt))  # widen timeout each try
        attempt += 1
    if attempt > 1 and res["ok"]:
        res["note"] = (res["note"] + f" (recovered on retry {attempt - 1})").strip()
    return res


def _check_url_once(url: str, timeout: float) -> dict:
    """Check one URL. OK when the final status is < 400 (redirects followed)."""
    ctx = ssl.create_default_context()
    # Some sites present incomplete chains; retry once without verification and flag it.
    for verify in (True, False):
        if not verify:
            ctx = ssl._create_unverified_context()
        for method in ("HEAD", "GET"):
            try:
                resp = _request(url, method, timeout, ctx)
                code = getattr(resp, "status", resp.getcode())
                final = resp.geturl()
                resp.close()
                return {
                    "url": url,
                    "ok": code < 400,
                    "status": code,
                    "final_url": final if final != url else "",
                    "note": "" if verify else "tls-unverified",
                }
            except urllib.error.HTTPError as e:
                # 405/403 on HEAD is common; let the GET attempt run before giving up.
                if method == "HEAD" and e.code in (403, 405, 406, 501):
                    continue
                # 403 from a bot wall is not proof the page is dead; mark separately.
                soft = e.code in (403, 429)
                return {
                    "url": url,
                    "ok": soft,  # treat bot-walls as "reachable, gated"
                    "status": e.code,
                    "final_url": "",
                    "note": "bot-gated (manual check)" if soft else "http-error",
                }
            except (urllib.error.URLError, ssl.SSLError, TimeoutError, OSError) as e:
                last = getattr(e, "reason", e)
                if verify:
                    break  # retry the whole thing with verification off
                return {"url": url, "ok": False, "status": None,
                        "final_url": "", "note": f"unreachable: {last}"}
    return {"url": url, "ok": False, "status": None, "final_url": "", "note": "unreachable"}


def run_once(md_path: str, timeout: float, workers: int, quiet: bool, retries: int = 2) -> dict:
    refs = parse_references(md_path)
    jobs: list[tuple[int, str]] = [(r["num"], u) for r in refs for u in r["urls"]]

    results: dict[str, dict] = {}
    with futures.ThreadPoolExecutor(max_workers=workers) as pool:
        fut = {pool.submit(check_url, url, timeout, retries): (num, url) for num, url in jobs}
        for f in futures.as_completed(fut):
            num, url = fut[f]
            res = f.result()
            res["ref"] = num
            results[url] = res

    ordered = sorted(results.values(), key=lambda r: (r["ref"], r["url"]))
    broken = [r for r in ordered if not r["ok"]]
    gated = [r for r in ordered if r["ok"] and "gated" in r["note"]]

    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{stamp}] checked {len(ordered)} link(s) across {len(refs)} references")
    if not quiet:
        for r in ordered:
            mark = "OK " if r["ok"] else "XX "
            code = r["status"] if r["status"] is not None else "---"
            extra = f"  ({r['note']})" if r["note"] else ""
            print(f"  {mark}[{r['ref']:>2}] {code} {r['url']}{extra}")

    print(f"summary: {len(ordered) - len(broken)} ok, {len(broken)} broken, "
          f"{len(gated)} bot-gated (verify by hand)")
    if broken:
        print("BROKEN:")
        for r in broken:
            print(f"  [{r['ref']}] {r['url']}  -> {r['status']} {r['note']}")

    return {
        "timestamp": stamp,
        "references": len(refs),
        "links": len(ordered),
        "ok": len(ordered) - len(broken),
        "broken": broken,
        "gated": [g["url"] for g in gated],
        "results": ordered,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate reference links in the RVx paper.")
    ap.add_argument("--md", default=DEFAULT_MD, help="path to the manuscript markdown")
    ap.add_argument("--interval", type=int, default=0,
                    help="seconds between re-checks; 0 = run once (default)")
    ap.add_argument("--timeout", type=float, default=15.0, help="per-request timeout (s)")
    ap.add_argument("--workers", type=int, default=8, help="concurrent checks")
    ap.add_argument("--retries", type=int, default=2,
                    help="retries for transient failures (timeouts/DNS)")
    ap.add_argument("--json", default=os.path.join(HERE, "reference_check_report.json"),
                    help="path for the JSON report (latest run)")
    ap.add_argument("--quiet", action="store_true", help="print only the summary")
    args = ap.parse_args()

    if not os.path.exists(args.md):
        print(f"manuscript not found: {args.md}", file=sys.stderr)
        return 2

    def one() -> int:
        report = run_once(args.md, args.timeout, args.workers, args.quiet, args.retries)
        try:
            with open(args.json, "w", encoding="utf-8") as fh:
                json.dump(report, fh, indent=2)
            print(f"report written: {args.json}")
        except OSError as e:
            print(f"could not write report: {e}", file=sys.stderr)
        return 1 if report["broken"] else 0

    if args.interval <= 0:
        return one()

    print(f"interval mode: re-checking every {args.interval}s. Ctrl+C to stop.")
    try:
        while True:
            one()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nstopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())

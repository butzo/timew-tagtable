#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 butzo
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version. See the LICENSE file for details.
"""Timewarrior report: one row per day, one column per tag, decimal hours.

Settings (timewarrior.cfg or rc.<key>=<value> on the command line):
  tagtable.tags       comma-separated columns in order; tags joined by + are summed
                      into one column, e.g. work,uni+thesis; the tag * matches
                      every interval (required)
  tagtable.delimiter  column delimiter; literal string or tab/\\t/space (default: tab)
  tagtable.copy       yes/no; copy value rows to the clipboard via wl-copy (default: no)

Examples:
  timew report tagtable :month
  timew report tagtable :month rc.tagtable.tags=work,uni+thesis rc.tagtable.delimiter=';'
  timew report tagtable :month rc.tagtable.tags="work,uni,*"
  timew report tagtable 2026-09-01 - 2026-10-01 rc.tagtable.copy=yes
"""
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, time, timedelta, timezone

UNTAGGED = "untagged"
WILDCARD = "*"
TAG_JOIN = "+"
TIMEW_FMT = "%Y%m%dT%H%M%SZ"
NAMED_DELIMITERS = {"": "\t", "tab": "\t", "\\t": "\t", "space": " "}
TRUE = {"yes", "y", "on", "true", "1"}


def parse_utc(s):
    """Timewarrior UTC timestamp -> aware datetime in local time."""
    return datetime.strptime(s, TIMEW_FMT).replace(tzinfo=timezone.utc).astimezone()


def next_midnight(dt):
    """Next local midnight after dt (DST-safe: naive local -> aware)."""
    return datetime.combine(dt.date() + timedelta(days=1), time.min).astimezone()


def fail(msg):
    print(f"tagtable: {msg}")
    sys.exit(1)


def main():
    header, _, body = sys.stdin.read().partition("\n\n")
    config = dict(l.split(": ", 1) for l in header.splitlines() if ": " in l)
    intervals = json.loads(body.strip() or "[]")

    cols = []  # (header label, tags summed into this column)
    for raw in config.get("tagtable.tags", "").split(","):
        tags = [t.strip().strip('"') for t in raw.split(TAG_JOIN)]
        tags = [t for t in tags if t]
        if tags:
            cols.append((TAG_JOIN.join(tags), tags))
    if not cols:
        fail("no tags given; set tagtable.tags in timewarrior.cfg or pass rc.tagtable.tags=a,b")
    raw_delim = config.get("tagtable.delimiter", "")
    delim = NAMED_DELIMITERS.get(raw_delim.lower(), raw_delim)
    copy = config.get("tagtable.copy", "no").strip().lower() in TRUE

    now = datetime.now().astimezone()
    rep_start = parse_utc(config["temp.report.start"]) if config.get("temp.report.start") else None
    rep_end = parse_utc(config["temp.report.end"]) if config.get("temp.report.end") else None

    seconds = defaultdict(float)  # (date, column index) -> seconds
    seen_days = set()
    seen_tags = set()
    for iv in intervals:
        start = parse_utc(iv["start"])
        end = parse_utc(iv["end"]) if "end" in iv else now
        if rep_start:
            start = max(start, rep_start)
        if rep_end:
            end = min(end, rep_end)
        if end <= start:
            continue
        iv_tags = set(iv.get("tags") or [UNTAGGED])
        seen_tags |= iv_tags
        # Once per matching column, however many of its tags the interval has
        hits = [i for i, (_, tags) in enumerate(cols)
                if WILDCARD in tags or not iv_tags.isdisjoint(tags)]
        cur = start
        while cur < end:  # split at local midnight
            seg_end = min(end, next_midnight(cur))
            seen_days.add(cur.date())
            for i in hits:
                seconds[(cur.date(), i)] += (seg_end - cur).total_seconds()
            cur = seg_end

    seen_days = sorted(seen_days)
    first_day = rep_start.date() if rep_start else (seen_days[0] if seen_days else None)
    if first_day is None:
        fail("no range and no data")
    last_day = (rep_end - timedelta(microseconds=1)).date() if rep_end else max(seen_days + [first_day])

    rows = []
    day = first_day
    while day <= last_day:
        cells = [f"{seconds[(day, i)] / 3600:.2f}" if seconds.get((day, i)) else ""
                 for i in range(len(cols))]
        rows.append(delim.join(cells))
        day += timedelta(days=1)

    # Per tag, not per column, so a typo inside a group is still reported;
    # the wildcard has data as soon as anything at all was tracked
    used = seen_tags | ({WILDCARD} if seen_tags else set())
    unused = [t for t in dict.fromkeys(t for _, tags in cols for t in tags) if t not in used]
    values = "\n".join(rows)

    print(f"{first_day} - {last_day} ({len(rows)} days)")
    if unused:
        print(f"no data: {', '.join(unused)}")
    print(delim.join(label for label, _ in cols))
    if copy:
        try:
            # Detach wl-copy's output: it keeps running to serve the clipboard,
            # and an inherited stdout would block timew until it exits.
            subprocess.run(["wl-copy"], input=values, text=True, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"copied {len(rows)} rows to clipboard")
        except (OSError, subprocess.CalledProcessError) as e:
            print(f"copy failed: {e}")
    print()
    print(values)


if __name__ == "__main__":
    main()

"""The reader privacy scan (ship-b3933d): nothing that identifies a person may appear in a page or a reader data file.

The patterns are the ones Papyrus's own reader privacy scan uses (procedures/newsroom/tests/reader_privacy.py in
Papyrus 5.22.0), which is a test helper and not exported. Person ids are random UUIDs, the same shape as a public
`readerId`, so the scan allows exactly the reader ids that a reader data file publishes on purpose and fails on every
other UUID, on any `ss1_` or `ssdev_` site subject, on any email address and on any person id spelling.

Run against the live site:  python3 tests/reader_privacy.py https://shipped.anth.us
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Iterable, Mapping

SITE_SUBJECT = re.compile(r"ss(?:1|dev)_[A-Za-z0-9_-]{8,}")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]*[A-Za-z][A-Za-z0-9-]*\.)+[A-Za-z]{2,}")
UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
PERSON_ID = re.compile(r"person[-_ ]?id|\bperson[-_][A-Za-z0-9-]{6,}|\bprs_[A-Za-z0-9]+", re.IGNORECASE)

LIVE_PAGES = ("/", "/new/", "/rising/", "/vapor/", "/submit/", "/sign-in/", "/policies/", "/roundup/")
LIVE_DATA = ("items", "board", "readers", "submissions")


def identity_leaks(text: str, allowed_reader_ids: Iterable[str] = ()) -> list[str]:
    allowed = {reader_id.lower() for reader_id in allowed_reader_ids}
    leaks = [match.group(0) for pattern in (SITE_SUBJECT, EMAIL, PERSON_ID) for match in pattern.finditer(text)]
    leaks += [match.group(0) for match in UUID.finditer(text) if match.group(0).lower() not in allowed]
    return leaks


def scan_files(files: Mapping[str, bytes | str], allowed_reader_ids: Iterable[str] = ()) -> dict[str, list[str]]:
    """The leaks per file name; empty when the output is clean."""
    allowed = list(allowed_reader_ids)
    found: dict[str, list[str]] = {}
    for name, body in files.items():
        text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else body
        leaks = identity_leaks(text, allowed)
        if leaks:
            found[name] = leaks
    return found


def reader_ids_in(data_files: Mapping[str, str]) -> set[str]:
    """The public reader ids a set of reader data files publishes (every `readerId` value)."""
    found: set[str] = set()

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "readerId" and isinstance(item, str):
                    found.add(item)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for body in data_files.values():
        walk(json.loads(body))
    return found


def _fetch(url: str) -> str | None:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "shipped-privacy-scan"}), timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def scan_live(origin: str, item_paths: Iterable[str] = ()) -> int:
    pages = {path: _fetch(origin + path) for path in (*LIVE_PAGES, *item_paths)}
    data = {f"/_data/reader/{name}.json": _fetch(f"{origin}/_data/reader/{name}.json") for name in LIVE_DATA}
    published = {name: body for name, body in data.items() if body is not None}
    for name, body in {**pages, **data}.items():
        print(f"{name}: {'missing' if body is None else f'{len(body)} bytes'}")
    allowed = reader_ids_in(published)
    leaks = scan_files({name: body for name, body in pages.items() if body is not None}) | scan_files(published, allowed)
    for name, found in leaks.items():
        print(f"LEAK {name}: {found}")
    print("clean" if not leaks else "FAILED")
    return 1 if leaks else 0


if __name__ == "__main__":
    sys.exit(scan_live(sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "https://shipped.anth.us", sys.argv[2:]))

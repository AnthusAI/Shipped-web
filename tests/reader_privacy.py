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

ANALYTICS_IDENTITY_FIELDS = re.compile(r"user_id|userId|user_properties|client_id|\bcid\b", re.IGNORECASE)
GTAG_CALL = re.compile(r"gtag\s*\((?:[^()]|\([^()]*\))*\)|papyrusAnalytics\.track\s*\((?:[^()]|\([^()]*\))*\)")
IDENTITY_QUERY_NAME = re.compile(r"[?&](?:token|t|ss|sitesubject|subject|email|handle|user|user_id|person|person_id|personid)=", re.IGNORECASE)

SPONSORSHIP_SCRIPT_PATH = "/assets/shipped-sponsorship.js"
SPONSORSHIP_EVENT_NAMES = {"view_promotion", "select_promotion"}
SPONSORSHIP_EVENT_FIELDS = {
    "promotion_id", "promotion_name", "creative_name", "creative_slot", "page_type", "sponsor_topic", "match_kind", "sponsor_action",
}
SPONSORSHIP_ATTRIBUTE_NAMES = {"unit", "id", "name", "slot", "page-type", "topic", "match", "action"}
SPONSORSHIP_ATTRIBUTE = re.compile(r'data-sponsor-([a-z-]+)="([^"]*)"')
SPONSORSHIP_SNAKE_CASE_WORD = re.compile(r"\b[a-z]+(?:_[a-z]+)+\b")
SPONSORSHIP_IDENTITY_SOURCES = re.compile(r"document\.cookie|localStorage|sessionStorage|papyrusReader|readerId|reader_id|\bhandle\b|\bemail\b", re.IGNORECASE)

LIVE_PAGES = ("/", "/new/", "/rising/", "/submit/", "/sign-in/", "/policies/", "/roundup/")
LIVE_DATA = ("items", "board", "readers", "submissions")


def identity_leaks(text: str, allowed_reader_ids: Iterable[str] = ()) -> list[str]:
    allowed = {reader_id.lower() for reader_id in allowed_reader_ids}
    leaks = [match.group(0) for pattern in (SITE_SUBJECT, EMAIL, PERSON_ID) for match in pattern.finditer(text)]
    leaks += [match.group(0) for match in UUID.finditer(text) if match.group(0).lower() not in allowed]
    return leaks


ENGINE_ANALYTICS_SCRIPT = re.compile(r"<script>(?:(?!</script>).)*IDENTITY_NAME=(?:(?!</script>).)*</script>", re.DOTALL)


def without_engine_analytics_scripts(page: str) -> str:
    """The page without Papyrus's two fixed analytics scripts (address redaction and the event allowlist).

    Their patterns list the identity words they remove (`person_id`, `user_id`, `ss1_`...), which is not identity in the page.
    Everything the site itself configures, the gtag config, set and event calls, stays in and is scanned.
    """
    return ENGINE_ANALYTICS_SCRIPT.sub("", page)


def analytics_leaks(page: str) -> list[str]:
    """Identity in the Google Analytics configuration and event calls of a page.

    The gtag config, set and event calls in the page carry no `user_id`, `user_properties` or client id, and no identity in
    any argument (subject, email, person id, UUID, identity query parameter). Pages from Papyrus 5.29.0 also redact the
    address GA records, so the calls the page makes before any event are the same on every page.
    """
    leaks: list[str] = []
    for call in GTAG_CALL.findall(without_engine_analytics_scripts(page)):
        if "'js'" in call or call.strip().startswith("gtag(){"):
            continue
        for match in ANALYTICS_IDENTITY_FIELDS.finditer(call):
            leaks.append(f"analytics field {match.group(0)}")
        for pattern in (SITE_SUBJECT, EMAIL, PERSON_ID, UUID, IDENTITY_QUERY_NAME):
            leaks += [f"analytics value {match.group(0)}" for match in pattern.finditer(call)]
    return leaks


def sponsorship_attribute_leaks(page: str) -> list[str]:
    """Identity in the data attributes the sponsorship units carry, which the sponsorship script sends to Google Analytics.

    A unit carries only the attributes in `SPONSORSHIP_ATTRIBUTE_NAMES` (what the unit is and where it sits), and none holds
    a subject, an email, a person id, a UUID or an identity query parameter.
    """
    leaks: list[str] = []
    for name, value in SPONSORSHIP_ATTRIBUTE.findall(page):
        if name not in SPONSORSHIP_ATTRIBUTE_NAMES:
            leaks.append(f"sponsorship attribute data-sponsor-{name}")
        for pattern in (SITE_SUBJECT, EMAIL, PERSON_ID, UUID, IDENTITY_QUERY_NAME):
            leaks += [f"sponsorship value {match.group(0)}" for match in pattern.finditer(value)]
    return leaks


def sponsorship_script_leaks(script: str) -> list[str]:
    """Identity in the sponsorship script: view_promotion and select_promotion carry only the allowed fields and read no reader state."""
    leaks = [f"sponsorship script field {word}" for word in sorted(set(SPONSORSHIP_SNAKE_CASE_WORD.findall(script)) - SPONSORSHIP_EVENT_FIELDS - SPONSORSHIP_EVENT_NAMES)]
    leaks += [f"sponsorship script identity {match.group(0)}" for match in ANALYTICS_IDENTITY_FIELDS.finditer(script)]
    leaks += [f"sponsorship script reads {match.group(0)}" for match in SPONSORSHIP_IDENTITY_SOURCES.finditer(script)]
    leaks += analytics_leaks(script)
    return leaks


def scan_files(files: Mapping[str, bytes | str], allowed_reader_ids: Iterable[str] = ()) -> dict[str, list[str]]:
    """The leaks per file name; empty when the output is clean."""
    allowed = list(allowed_reader_ids)
    found: dict[str, list[str]] = {}
    for name, body in files.items():
        text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else body
        is_page = name.endswith("/") or name.endswith(".html")
        is_sponsorship_script = name.endswith(SPONSORSHIP_SCRIPT_PATH.lstrip("/"))
        leaks = identity_leaks(without_engine_analytics_scripts(text) if is_page else text, allowed) + (analytics_leaks(text) if is_page else [])
        leaks += sponsorship_attribute_leaks(text) if is_page else []
        leaks += sponsorship_script_leaks(text) if is_sponsorship_script else []
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
    pages[SPONSORSHIP_SCRIPT_PATH] = _fetch(origin + SPONSORSHIP_SCRIPT_PATH)
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

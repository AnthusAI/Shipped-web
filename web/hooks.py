"""Shipped named hooks for the standard Papyrus front end (projection.json names this module).

Editors set the verdict, the four editor scores, the evidence and the entities in an item's front matter.
The dimensions, the hype gap formula and the verdicts are data in scoring.json; this code only iterates them.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from functools import lru_cache
from html import escape
from pathlib import Path
from urllib.parse import urlparse

LOGGER = logging.getLogger("shipped.hooks")

SCORING_PATH = Path(__file__).with_name("scoring.json")

DEPENDS_ON = {"*": [], "item": []}

MINIMUM_SCORE = 1.0
MAXIMUM_SCORE = 5.0
METER_SEGMENTS = 5
LOW_SCORE_BELOW = 2.5
BOARD_ROW_LIMIT = 30
DEFAULT_VERDICT = "pending"
MINUS_SIGN = "−"

EVIDENCE_CHECKS = {
    "checked": ("Checked", "check check-checked",
                '<circle cx="8" cy="8" r="5.8"/><path d="M5.4 8.1l1.8 1.8 3.4-3.7"/>', ""),
    "partly": ("Partly", "check",
               '<circle cx="8" cy="8" r="5.8"/><path d="M8 2.2a5.8 5.8 0 0 1 0 11.6z" fill="currentColor"/>', ""),
    "unchecked": ("Not checked", "check check-unchecked",
                  '<circle cx="8" cy="8" r="5.8"/>', ' stroke-dasharray="2 2"'),
}

STAMP_ICONS = {
    "shipped": '<path d="M2.5 2.5h11v11h-11z"/><path d="M5 8.2l2 2 4-4.4"/>',
    "verified": '<circle cx="8" cy="8" r="5.8"/><path d="M5.4 8.1l1.8 1.8 3.4-3.7"/>',
    "pending": '<circle cx="8" cy="8" r="5.8"/><path d="M8 4.8V8l2.2 1.4"/>',
    "vapor": '<circle cx="8" cy="8" r="5"/><path d="M3 13L13 3"/>',
}
FALLBACK_STAMP_ICON = '<circle cx="8" cy="8" r="5.8"/>'

SAFE_URL_SCHEMES = ("http", "https")


@lru_cache(maxsize=1)
def _scoring():
    return json.loads(SCORING_PATH.read_text(encoding="utf-8"))


def page_inputs(site):
    return _scoring()


def _item_key(summary):
    return summary.output_path or summary.slug


def _warn(summary, message):
    LOGGER.warning("item %s: %s", _item_key(summary), message)


def _text(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def _read_scores(summary, front):
    raw = front.get("scores")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        _warn(summary, "scores is not a mapping; left out")
        return {}
    known = {dimension["key"] for dimension in _scoring()["dimensions"]}
    scores = {}
    for key, value in raw.items():
        if key not in known:
            _warn(summary, f"score for unknown dimension {key!r} left out")
        elif isinstance(value, bool) or not isinstance(value, (int, float)) or not MINIMUM_SCORE <= value <= MAXIMUM_SCORE:
            _warn(summary, f"score {key}={value!r} is not a number from 1 to 5; left out")
        else:
            scores[key] = float(value)
    return scores


def _read_evidence(summary, front):
    raw = front.get("evidence")
    if raw is None:
        return []
    if not isinstance(raw, list):
        _warn(summary, "evidence is not a list; left out")
        return []
    evidence = []
    for position, entry in enumerate(raw):
        if not isinstance(entry, dict):
            _warn(summary, f"evidence {position} is not a mapping; left out")
            continue
        url = _text(entry.get("url"))
        kind = _text(entry.get("kind"))
        check = entry.get("check")
        if not url or urlparse(url).scheme not in SAFE_URL_SCHEMES or not urlparse(url).netloc:
            _warn(summary, f"evidence {position} has no http or https url; left out")
        elif check not in EVIDENCE_CHECKS:
            _warn(summary, f"evidence {position} has check {check!r}; left out")
        elif not kind:
            _warn(summary, f"evidence {position} has no kind; left out")
        else:
            evidence.append({"kind": kind, "url": url, "check": check})
    return evidence


def _read_entities(summary, front):
    raw = front.get("entities")
    if raw is None:
        return []
    if not isinstance(raw, list):
        _warn(summary, "entities is not a list; left out")
        return []
    entities = []
    for position, entry in enumerate(raw):
        kind = _text(entry.get("kind")) if isinstance(entry, dict) else None
        name = _text(entry.get("name")) if isinstance(entry, dict) else None
        if kind and name:
            entities.append({"kind": kind, "name": name})
        else:
            _warn(summary, f"entity {position} needs a kind and a name; left out")
    return entities


def _read_verdict(summary, front):
    raw = front.get("verdict")
    if raw is None:
        return DEFAULT_VERDICT
    if raw in _scoring()["verdicts"]:
        return raw
    _warn(summary, f"unknown verdict {raw!r}; shown as {DEFAULT_VERDICT}")
    return DEFAULT_VERDICT


def _date_text(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return _text(value)


def _read_item(summary):
    front = summary.front_matter or {}
    return {
        "verdict": _read_verdict(summary, front),
        "by": _text(front.get("verdictBy")),
        "at": _date_text(front.get("verdictAt")),
        "scores": _read_scores(summary, front),
        "evidence": _read_evidence(summary, front),
        "entities": _read_entities(summary, front),
        "maker": _text(front.get("maker")),
    }


def _hype_gap(scores):
    rule = _scoring()["hypeGap"]
    keys = rule["plus"] + rule["minus"]
    if not keys or any(key not in scores for key in keys):
        return None
    plus = sum(scores[key] for key in rule["plus"]) / len(rule["plus"])
    minus = sum(scores[key] for key in rule["minus"]) / len(rule["minus"])
    return plus - minus


def _hype_gap_html(gap, large=False):
    if gap is None:
        return ""
    rounded = round(gap, 1)
    size = " hype-gap-xl" if large else ""
    if rounded > 0:
        return f'<span class="hype-gap hype-gap-over{size}">&#9650; +{rounded:.1f} over</span>'
    if rounded < 0:
        return f'<span class="hype-gap hype-gap-under{size}">&#9660; {MINUS_SIGN}{abs(rounded):.1f} under</span>'
    return f'<span class="hype-gap{size}">&#9644; 0.0 level</span>'


def _stamp_html(verdict, extra_class=""):
    icon = STAMP_ICONS.get(verdict, FALLBACK_STAMP_ICON)
    return (
        f'<span class="status-stamp status-stamp-{escape(verdict)}{extra_class}">'
        f'<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">{icon}</svg>'
        f'<span class="status-stamp-label">{escape(verdict.capitalize())}</span></span>'
    )


def _score_dimension_html(label, score):
    if score is None:
        return (
            f'<div class="score-dimension is-low"><span class="score-dimension-name">{escape(label)}</span>'
            f'<span class="score-dimension-value" aria-label="{escape(label)} not scored">&mdash;</span></div>'
        )
    filled = round(score)
    segments = "".join(
        f'<span class="meter-segment{" is-on" if index < filled else ""}"></span>' for index in range(METER_SEGMENTS)
    )
    low = " is-low" if score < LOW_SCORE_BELOW else ""
    return (
        f'<div class="score-dimension{low}"><span class="score-dimension-name">{escape(label)}</span>'
        f'<span class="score-dimension-value">{score:.1f}</span>'
        f'<span class="score-meter" role="img" aria-label="{escape(label)} {score:.1f} out of 5, editor score">{segments}</span></div>'
    )


def _dimensions_html(scores):
    return "".join(_score_dimension_html(dimension["label"], scores.get(dimension["key"])) for dimension in _scoring()["dimensions"])


def _evidence_row_html(entry):
    label, css_class, icon, extra = EVIDENCE_CHECKS[entry["check"]]
    url = escape(entry["url"], quote=True)
    parsed = urlparse(entry["url"])
    shown = escape(parsed.netloc + parsed.path.rstrip("/"))
    return (
        f'<div class="evidence-row"><span class="evidence-type">{escape(entry["kind"])}</span>'
        f'<div class="evidence-body"><a class="evidence-link" href="{url}" rel="nofollow noopener">{shown}</a></div>'
        f'<span class="{css_class}"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"{extra} aria-hidden="true">{icon}</svg>{label}</span></div>'
    )


def _entity_chips_html(entities):
    return "".join(
        f'<span class="entity-chip"><i>{escape(entity["kind"])}</i>{escape(entity["name"])}</span>' for entity in entities
    )


def _checked_note(item):
    parts = []
    if item["by"]:
        parts.append(f'Checked by {escape(item["by"])}')
    if item["at"]:
        parts.append(escape(item["at"]))
    return ", ".join(parts)


def item_decorator(html, summary):
    item = _read_item(summary)
    gap = _hype_gap(item["scores"])
    note = _checked_note(item)
    note_html = f'<div class="item-stamp-note">{note}</div>' if note else ""
    maker_html = f'<span class="kicker">{escape(item["maker"])}</span>' if item["maker"] else ""
    chips = _entity_chips_html(item["entities"])
    chips_html = f'<div class="desk-entities">{chips}</div>' if chips else ""
    scores_html = ""
    if item["scores"]:
        gap_html = f'<div class="hype-row"><span class="hype-label">Hype gap</span>{_hype_gap_html(gap, True)}</div>' if gap is not None else ""
        scores_html = (
            f'<div class="desk-scores"><p class="kicker">Editor score</p>'
            f'<div class="desk-score-grid">{_dimensions_html(item["scores"])}</div>{gap_html}</div>'
        )
    evidence_html = ""
    if item["evidence"]:
        rows = "".join(_evidence_row_html(entry) for entry in item["evidence"])
        evidence_html = (
            '<section class="desk-evidence" aria-labelledby="desk-evidence-h"><div class="section-heading">'
            '<h2 id="desk-evidence-h">Primary evidence</h2></div>' + rows + "</section>"
        )
    strip = (
        '<header class="item-header desk-strip"><div class="item-header-main">'
        f'<div class="item-header-meta"><span class="kicker kicker-ink">Desk verdict</span>{maker_html}</div>'
        f"{scores_html}{chips_html}</div>"
        f'<div class="item-stamp-block">{_stamp_html(item["verdict"], " status-stamp-xl")}{note_html}</div></header>'
    )
    return strip + html + evidence_html


def _date_label(summary):
    published = _text(summary.published_at)
    if not published:
        return ""
    try:
        return datetime.fromisoformat(published.replace("Z", "+00:00")).strftime("%-d %b")
    except ValueError:
        return published[:10]


def _source_domain(item):
    for entry in item["evidence"]:
        return urlparse(entry["url"]).netloc
    return ""


def _board_row_html(position, summary, entry, section_label):
    item = _read_item(summary)
    gap_html = _hype_gap_html(_hype_gap(item["scores"]))
    meta = [f"<b>{escape(_source_domain(item))}</b>"] if _source_domain(item) else []
    meta.append(f"<span>&sect; {escape(section_label)}</span>")
    date_label = _date_label(summary)
    if date_label:
        meta.append(f"<span>{escape(date_label)}</span>")
    chips = _entity_chips_html(item["entities"])
    return (
        '<li class="board-row">'
        f'<span class="board-rank">{position}</span>'
        f'<div class="board-main"><a class="board-title" href="{escape(entry.url, quote=True)}">{escape(entry.title)}</a>'
        f'<div class="board-meta">{"".join(meta)}</div>'
        + (f'<div class="board-entities">{chips}</div>' if chips else "")
        + (f'<div class="board-gap"><span class="kicker">Hype gap</span> {gap_html}</div>' if gap_html else "")
        + "</div>"
        f'<div class="board-status">{_stamp_html(item["verdict"])}</div>'
        f'<div class="board-dimensions">{_dimensions_html(item["scores"])}</div>'
        "</li>"
    )


def _desk_board(page):
    section_labels = {section.name: section.label for section in page.settings.sections}
    entries_by_id = {entry.item_id: entry for entry in page.entries if entry.url}
    rows = [
        (summary, entries_by_id[summary.item_id])
        for summary in page.summaries
        if summary.section in section_labels and summary.item_id in entries_by_id
    ]
    if not rows:
        return ""
    rows.sort(key=lambda pair: (_text(pair[0].published_at) or "", pair[0].slug), reverse=True)
    body = "".join(
        _board_row_html(position, summary, entry, section_labels[summary.section])
        for position, (summary, entry) in enumerate(rows[:BOARD_ROW_LIMIT], start=1)
    )
    head_dimensions = "".join(f'<span>{escape(dimension["label"])}</span>' for dimension in _scoring()["dimensions"])
    return (
        '<section class="board desk-board" aria-labelledby="desk-board-h">'
        '<div class="board-heading"><h2 id="desk-board-h">From the desk</h2></div>'
        '<p class="board-note desk-board-note">Ratings open with reader sign-in</p>'
        f'<div class="board-head kicker" aria-hidden="true"><span>Rank</span><span>Item</span><span>Status</span>'
        f'<span class="board-head-dims">{head_dimensions}</span></div>'
        f'<ol class="board-list">{body}</ol></section>'
    )


def block(name, attributes, page):
    if name == "desk-board":
        return _desk_board(page)
    raise ValueError(f"unknown block {name!r}")

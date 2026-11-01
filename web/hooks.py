"""Shipped named hooks for the standard Papyrus front end (projection.json names this module).

Editors set the verdict, the four editor scores, the evidence and the entities in an item's front matter.
The dimensions and the verdicts are data in scoring.json; this code only iterates them.
"""

from __future__ import annotations

import json
import logging
import math
import re
from datetime import date, datetime
from functools import lru_cache
from html import escape, unescape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunsplit

LOGGER = logging.getLogger("shipped.hooks")

SCORING_PATH = Path(__file__).with_name("scoring.json")
NEWSLETTER_LISTS_PATH = Path(__file__).with_name("newsletter-lists.json")

ROUNDUP_ARCHIVE_PATH = "/roundup/"
ROUNDUP_SECTION = "roundup"
WIKI_ITEM_TYPE = "wiki_page"
READER_SCRIPT_PATH = "/_plugins/papyrus-reader@1.js"
READER_STYLESHEET_PATH = "/_plugins/papyrus-reader@1.css"
PROPOSALS_SCRIPT_PATH = "/assets/shipped-proposals.js"
PAGE_ITEM_TYPE = "page"
VERSION_SUFFIX = re.compile(r"-v\d+$")
SIGN_IN_LINK = re.compile(r'<a href="/sign-in/"[^>]*>Sign in</a>')
NEWSLETTER_SCRIPT_PATH = "/_plugins/papyrus-newsletter@1.js"
NEWSLETTER_CONSENT = "Email me the lists I ticked. I can unsubscribe in one click."
NEWSLETTER_HEADING = "Get The Weekly by email"
NEWSLETTER_DEK = "Tick the lists you want: The Weekly, and a short alert when something is added to a section. Nothing is sent until you confirm your address from the email we send you."
NEWSLETTER_FEED_NOTE = 'Prefer a feed? <a href="/feed.xml">RSS</a> carries the latest items.'

DEPENDS_ON = {
    "*": [],
    "item": ["*"],
    "listing:shipped": ["shipped", "stories"],
    "listing:open-weights": ["open-weights", "stories"],
    "listing:decisions": ["decisions", "stories"],
}

MINIMUM_SCORE = 1.0
MAXIMUM_SCORE = 5.0
METER_SEGMENTS = 5
LOW_SCORE_BELOW = 2.5
BOARD_ROW_LIMIT = 30
DEFAULT_VERDICT = "announced"
RETIRED_VERDICTS = {"shipped": "available", "pending": "announced", "vapor": "announced"}

EVIDENCE_CHECKS = {
    "checked": ("Checked", "check check-checked",
                '<circle cx="8" cy="8" r="5.8"/><path d="M5.4 8.1l1.8 1.8 3.4-3.7"/>', ""),
    "partly": ("Partly", "check",
               '<circle cx="8" cy="8" r="5.8"/><path d="M8 2.2a5.8 5.8 0 0 1 0 11.6z" fill="currentColor"/>', ""),
    "unchecked": ("Not checked", "check check-unchecked",
                  '<circle cx="8" cy="8" r="5.8"/>', ' stroke-dasharray="2 2"'),
}

STAMP_ICONS = {
    "available": '<path d="M2.5 2.5h11v11h-11z"/><path d="M5 8.2l2 2 4-4.4"/>',
    "verified": '<circle cx="8" cy="8" r="5.8"/><path d="M5.4 8.1l1.8 1.8 3.4-3.7"/>',
    "announced": '<circle cx="8" cy="8" r="1.6"/><path d="M4.8 11.2a4.5 4.5 0 0 1 0-6.4"/><path d="M11.2 4.8a4.5 4.5 0 0 1 0 6.4"/>',
}
STAMP_STROKE_WIDTHS = {"announced": "1.5"}
DEFAULT_STAMP_STROKE_WIDTH = "1.6"
FALLBACK_STAMP_ICON = '<circle cx="8" cy="8" r="5.8"/>'

SAFE_URL_SCHEMES = ("http", "https")

AGENT_SCORING = "agent"
DEFAULT_SCORES_LABEL = "Editor score"
DEFAULT_AGENT_SCORES_LABEL = "Editor's first pass (AI-assisted)"
AGENT_SCORING_NOTICE = "Scored by an AI research pass from the linked sources; a human editor will re-score it."
SCORING_POLICY_PATH = "/policies/#scores"
RANKING_POLICY_PATH = "/policies/#ranking"
BOARD_HELP_TEXT = (
    "Newest first. Each signal is Available, Verified or Announced. "
    "Upvotes and ratings from readers are counted apart, on each signal."
)
READER_KEY_TEXT = (
    "Upvotes count the readers who want this seen. Ratings are 1 to 5 scores on the four dimensions, counted apart from upvotes. "
    "Readers and editors are shown separately, and a reader mean from fewer than 5 ratings is too few to print."
)
NOT_YET_RATED_TEXT = "Not yet rated"
AI_STAMP_NOTE = "Stamped by AI, first pass"
AWAITING_EDITOR_TEXT = "awaiting an editor check"
EVIDENCE_NOTE_FOR_SOURCE = "Source of this signal"
SOURCE_EVIDENCE_KIND = "Release"
UNDERRATED_MARK_TEXT = "Works better than it\u2019s talked about."
WARNINGS_ALREADY_LOGGED = set()
STAMP_NOTE_VERBS = {"available": "Confirmed by", "verified": "Verified by"}
STAMP_NOTE_UNNAMED_VERBS = {"available": "Confirmed on", "verified": "Verified on"}
FOOTER_LINKS = (
    ("How the map works", "/map/"),
    ("How voting works", "/policies/#steering"),
    ("Policies", "/policies/"),
    ("All issues", "/roundup/"),
    ("RSS", "/feed.xml"),
    ("Privacy", "/policies/#privacy"),
    ("Cookie settings", "#cookie-settings"),
)
FOOTER_LINE = "Published by Anthus AI Solutions."


@lru_cache(maxsize=1)
def _scoring():
    return json.loads(SCORING_PATH.read_text(encoding="utf-8"))


def page_inputs(site):
    return _scoring()


def _subject(summary):
    """The reader subject of a published item: its lineage id, which is the item id without a `-v<n>` version suffix."""
    return VERSION_SUFFIX.sub("", summary.item_id)


def _island(name, props=None, tag="div", css_class="", fallback=""):
    """A mount point for a reader island; the reader script (loaded by head_extra) finds it by data-island."""
    class_html = f' class="{escape(css_class, quote=True)}"' if css_class else ""
    return (
        f'<{tag}{class_html} data-island="{escape(name, quote=True)}" '
        f'data-props="{escape(json.dumps(props or {}, separators=(",", ":")), quote=True)}">{fallback}</{tag}>'
    )


def _freshness_html():
    return _island("Freshness", tag="span", css_class="reader-freshness")


def _board_note_html():
    return (
        f'<p class="board-note desk-board-note">{_freshness_html()} '
        f'<span class="board-help">{escape(BOARD_HELP_TEXT)} <a href="{RANKING_POLICY_PATH}">How ranking works &rarr;</a></span></p>'
    )


def _board_reader_html(summary):
    subject = _subject(summary)
    return (
        '<div class="board-reader">'
        f'{_island("Vote", {"subject": subject}, tag="span")}{_island("UsedIt", {"subject": subject}, tag="span")}</div>'
    )


def _signal_actions_html(summary):
    subject = _subject(summary)
    return f'<div class="signal-actions">{_island("Vote", {"subject": subject})}{_island("UsedIt", {"subject": subject})}</div>'


def _item_comments_html(summary):
    return (
        '<section class="item-comments" aria-labelledby="item-comments-h">'
        '<div class="section-heading"><h2 id="item-comments-h">Comments</h2></div>'
        f'{_island("Comments", {"subject": _subject(summary)})}</section>'
    )


def _item_key(summary):
    return summary.output_path or summary.slug


def _warn(summary, message):
    warning = (_item_key(summary), message)
    if warning not in WARNINGS_ALREADY_LOGGED:
        WARNINGS_ALREADY_LOGGED.add(warning)
        LOGGER.warning("item %s: %s", warning[0], message)


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
    retired_keys = []
    for key, value in raw.items():
        if key not in known:
            retired_keys.append(key)
        elif isinstance(value, bool) or not isinstance(value, (int, float)) or not MINIMUM_SCORE <= value <= MAXIMUM_SCORE:
            _warn(summary, f"score {key}={value!r} is not a number from 1 to 5; left out")
        else:
            scores[key] = float(value)
    if retired_keys:
        _warn(summary, f"scores carry retired dimensions {sorted(retired_keys)!r}; left out")
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


def _read_relations(summary, front):
    raw = front.get("relations")
    if raw is None:
        return []
    if not isinstance(raw, list):
        _warn(summary, "relations is not a list; left out")
        return []
    relations = []
    for position, entry in enumerate(raw):
        fields = [_text(entry.get(field)) for field in ("subject", "relation", "object")] if isinstance(entry, dict) else []
        if len(fields) == 3 and all(fields):
            relations.append(dict(zip(("subject", "relation", "object"), fields)))
        else:
            _warn(summary, f"relation {position} needs a subject, a relation and an object; left out")
    return relations


def _read_verdict(summary, front):
    raw = front.get("verdict")
    if raw is None:
        return DEFAULT_VERDICT
    raw = RETIRED_VERDICTS.get(raw, raw)
    if raw in _scoring()["verdicts"]:
        return raw
    _warn(summary, f"unknown verdict {raw!r}; shown as {DEFAULT_VERDICT}")
    return DEFAULT_VERDICT


def _date_text(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return _text(value)


def _read_score_notes(summary, front):
    raw = front.get("scoreNotes")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        _warn(summary, "scoreNotes is not a mapping; left out")
        return {}
    known = {dimension["key"] for dimension in _scoring()["dimensions"]}
    return {key: _text(value) for key, value in raw.items() if key in known and _text(value)}


def _read_source_url(summary, front):
    url = _text(front.get("sourceUrl"))
    if not url:
        return None
    if urlparse(url).scheme not in SAFE_URL_SCHEMES or not urlparse(url).netloc:
        _warn(summary, "sourceUrl is not an http or https url; left out")
        return None
    return url


def _read_tags(front):
    raw = front.get("tags")
    return [tag.strip() for tag in raw if isinstance(tag, str) and tag.strip()] if isinstance(raw, list) else []


def _read_scoring(front):
    raw = front.get("scoring")
    if not isinstance(raw, dict):
        return {"by": None, "label": None, "at": None}
    return {"by": _text(raw.get("by")), "label": _text(raw.get("label")), "at": _date_text(raw.get("at"))}


def _is_agent_scored(item):
    return bool(item["scores"]) and item["scoring"]["by"] == AGENT_SCORING


def _read_item(summary):
    front = summary.front_matter or {}
    return {
        "source_url": _read_source_url(summary, front),
        "released_on": _date_text(front.get("releasedOn")),
        "score_notes": _read_score_notes(summary, front),
        "tags": _read_tags(front),
        "verdict": _read_verdict(summary, front),
        "by": _text(front.get("verdictBy")),
        "at": _date_text(front.get("verdictAt")),
        "scores": _read_scores(summary, front),
        "evidence": _read_evidence(summary, front),
        "entities": _read_entities(summary, front),
        "maker": _text(front.get("maker")),
        "maker_handle": _text(front.get("makerHandle")),
        "scoring": _read_scoring(front),
        "relations": _read_relations(summary, front),
    }


def _maker_key(item):
    return item["maker"] or item["maker_handle"]


def _maker_html(item):
    handle_html = f'<span class="maker-handle">{escape(item["maker_handle"])}</span>' if item["maker_handle"] else ""
    if item["maker"] and handle_html:
        return f'{escape(item["maker"])} ({handle_html})'
    if item["maker"]:
        return escape(item["maker"])
    return handle_html


def _stamp_html(verdict, extra_class=""):
    icon = STAMP_ICONS.get(verdict, FALLBACK_STAMP_ICON)
    stroke_width = STAMP_STROKE_WIDTHS.get(verdict, DEFAULT_STAMP_STROKE_WIDTH)
    return (
        f'<span class="status-stamp status-stamp-{escape(verdict)}{extra_class}">'
        f'<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="{stroke_width}" aria-hidden="true">{icon}</svg>'
        f'<span class="status-stamp-label">{escape(verdict.capitalize())}</span></span>'
    )


def _score_dimension_html(label, score, note=None):
    note_html = f'<span class="score-note">{escape(note)}</span>' if note else ""
    if score is None:
        return (
            f'<div class="score-dimension is-low"><span class="score-dimension-name">{escape(label)}</span>'
            f'<span class="score-dimension-value score-dimension-unrated">{NOT_YET_RATED_TEXT}</span>{note_html}</div>'
        )
    filled = round(score)
    segments = "".join(
        f'<span class="meter-segment{" is-on" if index < filled else ""}"></span>' for index in range(METER_SEGMENTS)
    )
    low = " is-low" if score < LOW_SCORE_BELOW else ""
    return (
        f'<div class="score-dimension{low}"><span class="score-dimension-name">{escape(label)}</span>'
        f'<span class="score-dimension-value">{score:.1f}</span>'
        f'<span class="score-meter" role="img" aria-label="{escape(label)} {score:.1f} out of 5, editor score">{segments}</span>{note_html}</div>'
    )


def _full_date_label(iso_date):
    try:
        return datetime.fromisoformat(str(iso_date).replace("Z", "+00:00")).strftime("%-d %b %Y")
    except (TypeError, ValueError):
        return iso_date or ""


def _timestamp_text(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return _text(value)


def _topic_of(item):
    topics = _scoring().get("topics", {})
    return topics.get(item["tags"][0]) if item["tags"] else None


def _strip_links_html(item):
    parts = []
    if item["source_url"]:
        domain = urlparse(item["source_url"]).netloc
        parts.append(
            f'<a class="source-link" href="{escape(item["source_url"], quote=True)}" rel="noopener">'
            f'Source: {escape(domain)} &rarr;</a>'
        )
    if item["released_on"]:
        parts.append(f'<span class="released-on">Released {escape(_full_date_label(item["released_on"]))}</span>')
    topic = _topic_of(item)
    if topic:
        parts.append(
            f'<a class="topic-link" href="{escape(topic["path"], quote=True)}">Beat: {escape(topic["label"])} &rarr;</a>'
        )
    return f'<div class="desk-strip-links">{"".join(parts)}</div>' if parts else ""


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


def _entity_chip_html(entity, site):
    resolved = site.knowledge.entity_for(entity["kind"], entity["name"]) if site is not None else None
    inner = f'<i>{escape(entity["kind"])}</i>{escape(entity["name"])}'
    if resolved and resolved.get("href"):
        return f'<a class="entity-chip" href="{escape(resolved["href"], quote=True)}">{inner}</a>'
    return f'<span class="entity-chip">{inner}</span>'


def _entity_chips_html(entities, site=None):
    return "".join(_entity_chip_html(entity, site) for entity in entities)


def _checked_note(item):
    """Who stamped the verdict and when, from verdictBy and verdictAt; empty when the item has neither or the verdict is not a stamp."""
    verdict = item["verdict"]
    if verdict not in STAMP_NOTE_VERBS:
        return ""
    when = escape(_full_date_label(item["at"])) if item["at"] else ""
    if item["by"]:
        return f'{STAMP_NOTE_VERBS[verdict]} {escape(item["by"])}' + (f", {when}" if when else "")
    return f"{STAMP_NOTE_UNNAMED_VERBS[verdict]} {when}" if when else ""


def _stamp_provenance(item):
    human_note = _checked_note(item)
    if human_note:
        return human_note
    if item["scoring"]["by"] == AGENT_SCORING:
        when = f' on {escape(_full_date_label(item["scoring"]["at"]))}' if item["scoring"]["at"] else ""
        return f"{AI_STAMP_NOTE}{when} &middot; {AWAITING_EDITOR_TEXT}"
    return ""


def _signal_meta_html(item):
    maker_html = f'<span class="kicker maker-display">{_maker_html(item)}</span>' if _maker_key(item) else ""
    return f'<div class="signal-meta"><span class="cintillo">Signal</span>{maker_html}{_strip_links_html(item)}</div>'


def _signal_status_html(item, summary):
    meaning = escape(_scoring().get("verdictMeanings", {}).get(item["verdict"], ""))
    provenance = _stamp_provenance(item)
    provenance_html = f'<span class="signal-status-provenance">{provenance}</span>' if provenance else ""
    return (
        '<div class="signal-status">'
        f'<div class="signal-status-line">{_stamp_html(item["verdict"], " status-stamp-lg")}'
        f'<span class="signal-status-meaning">{meaning}</span>{provenance_html}</div>'
        f'{_signal_actions_html(summary)}</div>'
    )


def _section_heading_html(number, heading_id, heading, note_html=""):
    return (
        f'<div class="section-heading"><span class="cintillo">{number}</span>'
        f'<h2 id="{heading_id}">{escape(heading)}</h2>{note_html}</div>'
    )


def _evidence_section_html(item):
    rows = "".join(_evidence_row_html(entry) for entry in item["evidence"])
    if not rows and item["source_url"]:
        parsed = urlparse(item["source_url"])
        rows = (
            f'<div class="evidence-row"><span class="evidence-type">{SOURCE_EVIDENCE_KIND}</span>'
            f'<div class="evidence-body"><a class="evidence-link" href="{escape(item["source_url"], quote=True)}" rel="nofollow noopener">'
            f'{escape(parsed.netloc + parsed.path.rstrip("/"))}</a></div>'
            f'<span class="check">{EVIDENCE_NOTE_FOR_SOURCE}</span></div>'
        )
    if not rows:
        return ""
    return (
        '<section class="signal-section desk-evidence" aria-labelledby="desk-evidence-h">'
        f'{_section_heading_html("02", "desk-evidence-h", "Primary evidence")}{rows}</section>'
    )


def _relation_row_html(relation):
    return (
        f'<div class="signal-relation"><b>{escape(relation["subject"])}</b>'
        f'<span class="signal-relation-name"><svg viewBox="0 0 100 10" width="100" height="10" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true">'
        f'<path d="M0 5h90"/><path d="M86 0.5l8 4.5-8 4.5"/></svg>{escape(relation["relation"])}</span>'
        f'<b>{escape(relation["object"])}</b></div>'
    )


def _map_section_html(item, site):
    chips = _entity_chips_html(item["entities"], site)
    relations = "".join(_relation_row_html(relation) for relation in item["relations"])
    if not chips and not relations:
        return ""
    chips_html = f'<div class="desk-entities">{chips}</div>' if chips else ""
    return (
        '<section class="signal-section" aria-labelledby="signal-map-h">'
        f'{_section_heading_html("03", "signal-map-h", "On the map")}{chips_html}{relations}</section>'
    )


def _editor_cell_html(dimension, item):
    score = item["scores"].get(dimension["key"])
    note = item["score_notes"].get(dimension["key"])
    tag_html = f'<span class="signal-editor-tag">AI first pass</span>' if score is not None and _is_agent_scored(item) else ""
    return (
        f'<div class="signal-editor"><span class="signal-cell-label">Editors</span>'
        f'{_score_dimension_html(dimension["label"], score, note)}{tag_html}</div>'
    )


def _dimension_row_html(dimension, item, summary):
    island = _island("Rating", {"subject": _subject(summary), "dimensions": [dimension["key"]]}, css_class="signal-rating-island")
    return (
        f'<div class="signal-dimension" data-dimension="{escape(dimension["key"], quote=True)}">'
        f'<div class="signal-dimension-name"><b>{escape(dimension["label"])}</b><span>{escape(dimension["question"])}</span></div>'
        f'<span class="signal-cell-label signal-cell-label-readers">Readers</span>{island}'
        f'{_editor_cell_html(dimension, item)}'
        '<span class="signal-cell-label signal-cell-label-yours">Your rating</span></div>'
    )


def _scores_label_html(item):
    if not item["scores"]:
        return ""
    agent_scored = _is_agent_scored(item)
    label = (item["scoring"]["label"] or DEFAULT_AGENT_SCORES_LABEL) if agent_scored else DEFAULT_SCORES_LABEL
    provenance_html = (
        f'<p class="scoring-provenance">{escape(AGENT_SCORING_NOTICE)} <a href="{SCORING_POLICY_PATH}">How we score &rarr;</a></p>'
        if agent_scored else ""
    )
    return f'<div class="signal-scores-label"><p class="kicker">{escape(label)}</p>{provenance_html}</div>'


def _ratings_section_html(item, summary):
    rows = "".join(_dimension_row_html(dimension, item, summary) for dimension in _scoring()["dimensions"])
    note = '<span class="kicker section-heading-note">1&ndash;5 &middot; readers and editors counted separately &middot; under 5 ratings shows &ldquo;too few&rdquo;</span>'
    return (
        '<section class="signal-section signal-ratings" aria-labelledby="signal-ratings-h">'
        f'{_section_heading_html("04", "signal-ratings-h", "Ratings", note)}'
        f'<p class="reader-key">{escape(READER_KEY_TEXT)} <a href="{RANKING_POLICY_PATH}">How ranking works &rarr;</a></p>'
        f'{_scores_label_html(item)}'
        '<div class="signal-dimension-head kicker" aria-hidden="true"><span>Dimension</span><span>Readers</span><span>Editors</span><span>Your rating</span></div>'
        f'{rows}</section>'
    )


SIGNAL_STANDING_MEMO = "shipped-signal-standing"
UNDERRATED_ICON = (
    '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">'
    '<path d="M2 13.5h12"/><path d="M4 11l4-4 2 2 3.5-3.5"/><path d="M10 5.5h3.5V9"/></svg>'
)
NEARBY_SAME_BEAT_PREFIX = "Same beat: "
NEARBY_SHARES_PREFIX = "Shares "


def _underrated_rule():
    return _scoring()["underrated"]


def _nearby_rule():
    return _scoring()["nearby"]


def _signal_url(summary):
    path = Path(summary.output_path)
    stem = path.parent if path.stem == "index" else path.with_suffix("")
    return f"/{stem.as_posix().strip('/')}/"


def _signal_title(summary):
    front = summary.front_matter or {}
    return _text(front.get("title")) or _text(summary.page_title) or _text(summary.title) or summary.slug.replace("-", " ").title()


def _signal_record(summary, site):
    item = _read_item(summary)
    entities = {}
    for entity in item["entities"]:
        resolved = site.knowledge.entity_for(entity["kind"], entity["name"])
        if resolved:
            entities.setdefault(resolved["key"], (entity["kind"], entity["name"]))
    topic = _topic_of(item)
    return {
        "item_id": summary.item_id,
        "title": _signal_title(summary),
        "url": _signal_url(summary),
        "useful": item["scores"].get("useful"),
        "ready": item["scores"].get("ready"),
        "agent_scored": _is_agent_scored(item),
        "scoring_label": item["scoring"]["label"],
        "entities": entities,
        "beat_key": item["tags"][0] if topic else None,
        "beat_label": topic["label"] if topic else None,
        "sort_date": _sort_date(summary),
    }


def _signal_records(site):
    return [
        _signal_record(summary, site)
        for summary in site.items
        if summary.type not in (WIKI_ITEM_TYPE, PAGE_ITEM_TYPE) and summary.section and summary.section not in LANDING_EXCLUDED_SECTIONS
    ]


def _mention_counts(records):
    holders = {}
    for record in records:
        for key in record["entities"]:
            holders.setdefault(key, set()).add(record["item_id"])
    counts = {}
    for record in records:
        sharing = set()
        for key in record["entities"]:
            sharing |= holders[key]
        sharing.discard(record["item_id"])
        counts[record["item_id"]] = len(sharing)
    return counts


def _quiet_mention_limit(qualifying_counts, rule):
    if not qualifying_counts:
        return None
    ordered = sorted(qualifying_counts)
    position = max(1, math.ceil(round(len(ordered) * rule["quietestShare"], 6)))
    return min(ordered[position - 1], rule["mentionCeiling"])


def _underrated_signals(records, counts, rule):
    qualifying = [
        record for record in records
        if (record["useful"] or 0) >= rule["minimumUseful"] and (record["ready"] or 0) >= rule["minimumReady"]
    ]
    limit = _quiet_mention_limit([counts[record["item_id"]] for record in qualifying], rule)
    quiet = [record for record in qualifying if counts[record["item_id"]] <= limit] if limit is not None else []
    return sorted(quiet, key=lambda record: (counts[record["item_id"]], -(record["useful"] + record["ready"]), record["title"].lower()))


def _signal_standing(site):
    def build():
        records = _signal_records(site)
        counts = _mention_counts(records)
        return {
            "records": {record["item_id"]: record for record in records},
            "ordered": records,
            "counts": counts,
            "underrated": _underrated_signals(records, counts, _underrated_rule()),
        }

    return site.memo(SIGNAL_STANDING_MEMO, build)


def _mentions_text(count):
    return f"{count} mention" if count == 1 else f"{count} mentions"


def _underrated_figures_text(record, mentions):
    return f"Useful {record['useful']:.1f} · Ready {record['ready']:.1f} · {_mentions_text(mentions)}"


def _record_scores_label(record):
    if record["agent_scored"]:
        return record["scoring_label"] or DEFAULT_AGENT_SCORES_LABEL
    return DEFAULT_SCORES_LABEL


def _underrated_mark_html(record, standing):
    if record is None or record["item_id"] not in {candidate["item_id"] for candidate in standing["underrated"]}:
        return ""
    figures = f'{_record_scores_label(record)} · {_underrated_figures_text(record, standing["counts"][record["item_id"]])}'
    return (
        f'<div class="signal-underrated"><span class="underrated-mark">{UNDERRATED_ICON}Underrated</span>'
        f'<span>{escape(UNDERRATED_MARK_TEXT)}</span><span class="signal-underrated-figures">{escape(figures)}</span></div>'
    )


def _nearby_why_text(shared_labels, same_beat_label):
    if shared_labels:
        named = [f"{kind} {name}" for kind, name in shared_labels[: _nearby_rule()["namedEntityLimit"]]]
        more = len(shared_labels) - len(named)
        if more > 0:
            named.append(f"{more} more")
        joined = named[0] if len(named) == 1 else ", ".join(named[:-1]) + " and " + named[-1]
        return NEARBY_SHARES_PREFIX + joined
    return NEARBY_SAME_BEAT_PREFIX + same_beat_label


def _nearby_signals(record, records, limit):
    candidates = []
    for other in records:
        if other["item_id"] == record["item_id"]:
            continue
        shared = [label for key, label in record["entities"].items() if key in other["entities"]]
        same_beat = bool(record["beat_key"]) and record["beat_key"] == other["beat_key"]
        if shared or same_beat:
            candidates.append({"record": other, "shared": shared, "same_beat": same_beat})
    candidates.sort(key=lambda candidate: candidate["record"]["title"].lower())
    candidates.sort(key=lambda candidate: candidate["record"]["sort_date"], reverse=True)
    candidates.sort(key=lambda candidate: (len(candidate["shared"]), candidate["same_beat"]), reverse=True)
    return [
        {"record": candidate["record"], "why": _nearby_why_text(candidate["shared"], record["beat_label"])}
        for candidate in candidates[:limit]
    ]


def _nearby_html(record, standing):
    if record is None:
        return ""
    nearby = _nearby_signals(record, standing["ordered"], _nearby_rule()["limit"])
    if not nearby:
        return ""
    rows = "".join(
        f'<li><a href="{escape(entry["record"]["url"], quote=True)}">{escape(entry["record"]["title"])}</a>'
        f'<span class="signal-nearby-why">{escape(entry["why"])}</span></li>'
        for entry in nearby
    )
    return (
        '<section class="signal-rail-block signal-nearby" aria-labelledby="signal-nearby-h">'
        f'<h2 id="signal-nearby-h">Nearby on the map</h2><ol class="signal-nearby-list">{rows}</ol></section>'
    )


def _front_underrated_html(page):
    if page.site is None:
        return ""
    standing = _signal_standing(page.site)
    shown = standing["underrated"][: _underrated_rule()["homeLimit"]]
    if not shown:
        return ""
    rows = "".join(
        f'<li><a href="{escape(record["url"], quote=True)}">{escape(record["title"])}</a>'
        f'<span class="front-underrated-figures">{escape(_underrated_figures_text(record, standing["counts"][record["item_id"]]))}</span></li>'
        for record in shown
    )
    labels = " / ".join(sorted({_record_scores_label(record) for record in shown}))
    return (
        '<section class="front-underrated" aria-labelledby="front-underrated-h">'
        f'<div class="front-side-heading"><h2 id="front-underrated-h">Underrated</h2><span class="front-underrated-mark">{UNDERRATED_ICON}Underrated</span></div>'
        f'<p class="front-side-note">{escape(UNDERRATED_MARK_TEXT)} Rated high on Useful and Ready, with few mentions. '
        f'<span class="kicker">{escape(labels)}</span></p>'
        f'<ol class="front-underrated-list">{rows}</ol></section>'
    )


def _article_with_status(html, item, summary):
    status = _signal_status_html(item, summary)
    summary_heading = _section_heading_html("01", "signal-summary-h", "Summary")
    header_end = html.find("</header>")
    if header_end < 0:
        return status + summary_heading + html
    insert_at = header_end + len("</header>")
    return html[:insert_at] + status + summary_heading + html[insert_at:]


def item_decorator(html, summary, site=None):
    if summary.type in (WIKI_ITEM_TYPE, PAGE_ITEM_TYPE):
        return html
    if _is_story(summary):
        return _story_page_html(html, summary, site)
    item = _read_item(summary)
    standing = _signal_standing(site) if site is not None else None
    record = standing["records"].get(summary.item_id) if standing else None
    main = (
        _article_with_status(html, item, summary)
        + _evidence_section_html(item)
        + _map_section_html(item, site)
        + _ratings_section_html(item, summary)
        + _underrated_mark_html(record, standing)
    )
    rail = (
        _stories_citing_signal_html(summary, site)
        + _nearby_html(record, standing)
    )
    return (
        f'{_signal_meta_html(item)}<div class="signal-layout"><div class="signal-main">{main}</div>'
        f'<aside class="signal-rail" aria-label="Related">{rail}</aside></div>{_item_comments_html(summary)}'
    )


def _date_label(summary):
    published = _text(_read_item(summary)["released_on"]) or _text(summary.published_at)
    if not published:
        return ""
    try:
        return datetime.fromisoformat(published.replace("Z", "+00:00")).strftime("%-d %b")
    except ValueError:
        return published[:10]


def _board_row_html(position, summary, entry, section_label, site=None):
    item = _read_item(summary)
    date_label = _date_label(summary)
    return (
        '<li class="board-row">'
        f'<div class="board-status">{_stamp_html(item["verdict"])}</div>'
        f'<div class="board-main"><a class="board-title" href="{escape(entry.url, quote=True)}">{escape(entry.title)}</a>'
        f'{_board_reader_html(summary)}</div>'
        f'<span class="board-section">&sect; {escape(section_label)}</span>'
        f'<span class="board-date">{escape(date_label)}</span>'
        "</li>"
    )


def _sort_date(summary):
    return _read_item(summary)["released_on"] or _text(summary.published_at) or ""


def _board_pairs(page, keep):
    section_labels = {section.name: section.label for section in page.settings.sections}
    entries_by_id = {entry.item_id: entry for entry in page.entries if entry.url}
    pairs = [
        (summary, entries_by_id[summary.item_id], section_labels[summary.section])
        for summary in page.summaries
        if summary.section in section_labels and summary.section != ROUNDUP_SECTION and summary.type != WIKI_ITEM_TYPE and not _is_story(summary) and summary.item_id in entries_by_id and keep(summary)
    ]
    pairs.sort(key=lambda triple: (_sort_date(triple[0]), triple[0].slug), reverse=True)
    return pairs


def _board_list_html(pairs, site=None):
    body = "".join(
        _board_row_html(position, summary, entry, label, site) for position, (summary, entry, label) in enumerate(pairs, start=1)
    )
    return f'<ol class="board-list">{body}</ol>'


def _more_links_html(page):
    links = "".join(
        f'<a href="/{escape(section.name, quote=True)}/">{escape(section.label)}</a>' for section in page.settings.sections
    )
    return f'<p class="board-more"><span class="kicker">More</span>{links}</p>'


def _desk_board(page, attributes):
    pairs = _board_pairs(page, lambda summary: True)
    if not pairs:
        return ""
    limit = int(attributes.get("limit", BOARD_ROW_LIMIT))
    heading = attributes.get("heading", "Latest")
    tag = "h1" if attributes.get("level") == "1" else "h2"
    more_html = _more_links_html(page) if attributes.get("more") == "true" else ""
    return (
        '<section class="board desk-board" aria-labelledby="desk-board-h">'
        f'<div class="board-heading"><{tag} id="desk-board-h">{escape(heading)}</{tag}></div>'
        f"{_board_note_html()}"
        f"{_board_list_html(pairs[:limit], page.site)}{more_html}</section>"
    )


def _mean(values):
    return sum(values) / len(values) if values else None


def _profile_row_html(label, mean):
    segments = "".join(
        f'<span class="meter-segment{" is-on" if index < round(mean) else ""}"></span>' for index in range(METER_SEGMENTS)
    )
    return (
        f'<div class="profile-row"><span class="profile-name">{escape(label)}</span>'
        f'<span class="profile-value">{mean:.1f}</span>'
        f'<span class="score-meter score-meter-large" role="img" aria-label="{escape(label)} {mean:.1f} out of 5, mean editor score">{segments}</span></div>'
    )


def _topic_profile_html(items):
    scored = [item for item in items if item["scores"]]
    if not scored:
        return ""
    rows = "".join(
        _profile_row_html(dimension["label"], _mean(values))
        for dimension in _scoring()["dimensions"]
        for values in [[item["scores"][dimension["key"]] for item in scored if dimension["key"] in item["scores"]]]
        if values
    )
    scores_label = "Editor scores (AI-assisted first pass)" if any(_is_agent_scored(item) for item in scored) else "Editor scores"
    return (
        '<section aria-labelledby="profile-h" class="topic-profile"><div class="section-heading">'
        '<span class="cintillo">Scores</span><h2 id="profile-h">How the beat scores</h2></div>'
        f'<p class="graph-note">{scores_label}, mean of {len(scored)} items</p>{rows}</section>'
    )


def _topic_makers_html(items):
    counts = {}
    labels = {}
    for item in items:
        key = _maker_key(item)
        if key:
            counts[key] = counts.get(key, 0) + 1
            labels.setdefault(key, f'<span class="maker-handle">{escape(key)}</span>' if not item["maker"] else escape(key))
    if not counts:
        return ""
    ordered = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0].lower()))
    rows = "".join(
        f'<li><span>{labels[name]}</span><span class="topic-maker-count">{count}</span></li>' for name, count in ordered
    )
    return (
        '<section aria-labelledby="makers-h" class="topic-makers"><div class="section-heading">'
        '<span class="cintillo">Makers</span><h2 id="makers-h">Who made them</h2></div>'
        f'<ul class="topic-maker-list">{rows}</ul></section>'
    )


def _topic_board(page, attributes):
    tag = attributes.get("tag")
    if not tag:
        raise ValueError("topic-board needs a tag attribute")
    pairs = _board_pairs(page, lambda summary: _read_item(summary)["tags"][:1] == [tag])
    items = [_read_item(summary) for summary, _entry, _label in pairs]
    makers = {_maker_key(item) for item in items if _maker_key(item)}
    stats = [
        ("Items", len(items)),
        ("Makers", len(makers)),
        ("Available", sum(1 for item in items if item["verdict"] == "available")),
        ("Announced", sum(1 for item in items if item["verdict"] == "announced")),
    ]
    stats_html = "".join(f"<div><dt>{label}</dt><dd>{value}</dd></div>" for label, value in stats)
    ranked_html = (
        '<section aria-labelledby="items-h" class="topic-block board desk-board"><div class="section-heading">'
        '<span class="cintillo">Newest first</span><h2 id="items-h">Items in this beat</h2></div>'
        f'{_board_note_html()}{_board_list_html(pairs, page.site)}</section>'
        if pairs else ""
    )
    return (
        f'<dl class="topic-stats topic-stats-row">{stats_html}</dl>'
        f'<div class="topic-two">{_topic_profile_html(items)}{_topic_makers_html(items)}</div>{ranked_html}'
    )


WIKI_SECTION = "wiki"
LANDING_EXCLUDED_SECTIONS = {ROUNDUP_SECTION, WIKI_SECTION, "stories"}
CONCEPT_SIGNAL_LIMIT = 10
CONCEPT_NEIGHBOUR_LIMIT = 6
LANDING_CONCEPT_LIMIT = 6
LANDING_CLUSTER_LIMIT = 8
GRAPH_JSON_PATH = "/_data/knowledge/index.json"
CLUSTER_STATE_WORDS = {"growing": "&#9650; growing", "cooling": "&#9660; cooling", "new": "&#9679; new"}
MAKER_KIND = "maker"


def _knowledge_source(page):
    return getattr(getattr(page.site, "knowledge", None), "_source", None)


def _knowledge_index(page):
    source = _knowledge_source(page)
    return (source.index() if source else None) or {}


def _knowledge_clusters(page):
    source = _knowledge_source(page)
    return ((source.clusters() if source else None) or {}).get("clusters") or []


def _latest_attribution_text(accepted_list):
    dated = [entry for entry in accepted_list if isinstance(entry, dict) and entry.get("actor") in ("ai", "human") and entry.get("on")]
    if not dated:
        return ""
    latest = max(dated, key=lambda entry: str(entry["on"]))
    day = escape(_full_date_label(str(latest["on"])[:10]))
    if latest["actor"] == "human":
        return f'Approved by {escape(str(latest.get("name") or "an editor"))} on {day}'
    return f"Edited by AI on {day}"


def _beat_clusters(page, key):
    return [cluster for cluster in _knowledge_clusters(page) if key in (cluster.get("beats") or [])]


def _beat_pairs(page, tag):
    return _board_pairs(page, lambda summary: _read_item(summary)["tags"][:1] == [tag])


def _signal_row_html(summary, entry, show_beat):
    item = _read_item(summary)
    topic = _topic_of(item) if show_beat else None
    beat_html = f'<span class="signal-beat">{escape(topic["label"])}</span>' if topic else ""
    return (
        f'<li class="signal-row">{_stamp_html(item["verdict"])}'
        f'<a class="signal-title" href="{escape(entry.url, quote=True)}">{escape(entry.title)}</a>'
        f'{beat_html}<span class="signal-date">{escape(_date_label(summary))}</span></li>'
    )


def _signal_list_html(pairs, show_beat):
    return '<ol class="signal-list">' + "".join(_signal_row_html(summary, entry, show_beat) for summary, entry, _label in pairs) + "</ol>"


def _entity_counts(items, site):
    counts = {}
    for item in items:
        for entity in item["entities"]:
            if entity["kind"] == MAKER_KIND:
                continue
            resolved = site.knowledge.entity_for(entity["kind"], entity["name"]) if site is not None else None
            key = (entity["kind"], entity["name"])
            record = counts.setdefault(key, {"name": entity["name"], "kind": entity["kind"], "href": resolved["href"] if resolved else None, "count": 0})
            record["count"] += 1
    return sorted(counts.values(), key=lambda record: (-record["count"], record["name"].lower()))


def _weighted_rows_html(rows):
    heaviest = max((weight for _name, _href, _kind, weight in rows), default=1)
    html = ""
    for name, href, kind, weight in rows:
        label = f'{escape(name)} <span class="kicker">{escape(kind)}</span>' if kind else escape(name)
        label_html = f'<a href="{escape(href, quote=True)}">{label}</a>' if href else label
        percent = round(weight / heaviest * 100)
        html += (
            f'<li class="concept-node"><span class="concept-node-name">{label_html}</span>'
            f'<span class="concept-node-weight">{weight}</span>'
            f'<span class="concept-weight" aria-hidden="true"><span style="width:{percent}%"></span></span></li>'
        )
    return f'<ul class="concept-node-list">{html}</ul>'


def _concept_stats(page, attributes):
    key = attributes["key"]
    beat = next((row for row in _knowledge_index(page).get("beats") or [] if row.get("key") == key), None)
    stats = []
    if beat and beat.get("series8"):
        series = [max(0, int(value)) for value in beat["series8"]]
        stats += [("Signals, 8 wks", sum(series)), ("This week", series[-1])]
    items = [_read_item(summary) for summary, _entry, _label in _beat_pairs(page, attributes["tag"])]
    stats.append(("Makers", len({_maker_key(item) for item in items if _maker_key(item)})))
    if _knowledge_clusters(page):
        stats.append(("Clusters", len(_beat_clusters(page, key))))
    body = "".join(f"<div><dt>{escape(label)}</dt><dd>{value}</dd></div>" for label, value in stats)
    return f'<dl class="concept-stats">{body}</dl>'


def _concept_provenance(page, attributes):
    text = _latest_attribution_text([cluster.get("acceptedBy") for cluster in _beat_clusters(page, attributes["key"])])
    return f'<p class="concept-provenance"><span aria-hidden="true">&#9998;</span> {text}</p>' if text else ""


def _concept_actions(page, attributes):
    form_id = page.settings.wiki.suggest_form
    suggest = (
        f'<details class="concept-suggest"><summary class="concept-button">Suggest an edit</summary>{page.form(form_id)}</details>'
        if form_id else ""
    )
    graph = f'<a class="concept-button concept-button-quiet" href="{GRAPH_JSON_PATH}">Graph JSON</a>'
    return f'<div class="concept-actions">{suggest}{graph}</div>'


def _concept_lineage(page, attributes):
    pairs = _beat_pairs(page, attributes["tag"])
    if not pairs:
        return ""
    summary, entry, _label = pairs[-1]
    when = _read_item(summary)["released_on"] or _text(summary.published_at)
    when_html = f" on {escape(_full_date_label(str(when)[:10]))}" if when else ""
    return (
        f'<p class="concept-lineage">Followed as a beat. First seen in <a href="{escape(entry.url, quote=True)}">{escape(entry.title)}</a>{when_html}.</p>'
        '<p class="concept-note">Extracted from signals</p>'
    )


def _concept_neighbourhood(page, attributes):
    items = [_read_item(summary) for summary, _entry, _label in _beat_pairs(page, attributes["tag"])]
    maker_counts = {}
    for item in items:
        if _maker_key(item):
            maker_counts[_maker_key(item)] = maker_counts.get(_maker_key(item), 0) + 1
    ordered = sorted(maker_counts.items(), key=lambda pair: (-pair[1], pair[0].lower()))
    name = escape(attributes.get("label", "This concept"))
    columns = ""
    if ordered:
        rows = [(maker, None, "", count) for maker, count in ordered[:CONCEPT_NEIGHBOUR_LIMIT]]
        rest = len(ordered) - len(rows)
        rest_html = f'<p class="concept-note">{rest} more makers, fewer signals each</p>' if rest > 0 else ""
        columns += f'<div><div class="concept-column-head">{name} &rarr; made by</div>{_weighted_rows_html(rows)}{rest_html}</div>'
    mentioned = _entity_counts(items, page.site)[:CONCEPT_NEIGHBOUR_LIMIT]
    if mentioned:
        rows = [(record["name"], record["href"], record["kind"], record["count"]) for record in mentioned]
        columns += f'<div><div class="concept-column-head">{name} &rarr; mentioned in signals</div>{_weighted_rows_html(rows)}</div>'
    return f'<div class="concept-columns">{columns}</div>' if columns else ""


def _concept_signals(page, attributes):
    pairs = _beat_pairs(page, attributes["tag"])
    return _signal_list_html(pairs[: int(attributes.get("limit", CONCEPT_SIGNAL_LIMIT))], show_beat=False) if pairs else ""


CONCEPT_BLOCKS = {
    "concept-stats": _concept_stats,
    "concept-provenance": _concept_provenance,
    "concept-actions": _concept_actions,
    "concept-lineage": _concept_lineage,
    "concept-neighbourhood": _concept_neighbourhood,
    "concept-signals": _concept_signals,
}


def _landing_tabs_html(page, current):
    links = "".join(
        f'<a href="/{escape(section.base, quote=True)}/"{" aria-current=" + chr(34) + "page" + chr(34) if section.name == current else ""}>{escape(section.label)}</a>'
        for section in page.settings.sections
        if section.name not in LANDING_EXCLUDED_SECTIONS and section.listing_page
    )
    return f'<nav aria-label="Sections" class="section-tabs">{links}</nav>'


def _landing_clusters_html(page):
    clusters = [cluster for cluster in _knowledge_clusters(page) if cluster.get("name")][:LANDING_CLUSTER_LIMIT]
    if not clusters:
        return ""
    rows = "".join(
        f'<li class="landing-cluster"><span class="landing-cluster-name">{escape(str(cluster["name"]))}</span>'
        f'<span class="landing-cluster-meta">{int(cluster.get("itemCount") or 0)}'
        + (f' &middot; {CLUSTER_STATE_WORDS[cluster["state"]]}' if cluster.get("state") in CLUSTER_STATE_WORDS else "")
        + "</span></li>"
        for cluster in clusters
    )
    edited = _latest_attribution_text([cluster.get("acceptedBy") for cluster in clusters])
    return (
        '<section class="landing-rail" aria-labelledby="landing-clusters-h"><h2 id="landing-clusters-h">Clusters across Shipped</h2>'
        f'<p class="concept-note">{edited.upper() + " &middot; " if edited else ""}CLUSTERS ARE NOT SPLIT BY SECTION YET</p>'
        f'<ul class="landing-list">{rows}</ul></section>'
    )


def _landing_concepts_html(items, site):
    counted = [record for record in _entity_counts(items, site) if record["href"]][:LANDING_CONCEPT_LIMIT]
    if not counted:
        return ""
    rows = "".join(
        f'<li><a class="landing-concept" href="{escape(record["href"], quote=True)}"><span class="landing-concept-name">{escape(record["name"])} '
        f'<span class="kicker">{escape(record["kind"])}</span></span><span class="landing-cluster-meta">{record["count"]} in section</span></a></li>'
        for record in counted
    )
    return (
        '<section class="landing-rail" aria-labelledby="landing-concepts-h"><h2 id="landing-concepts-h">Concepts bubbling up</h2>'
        f'<ul class="landing-list">{rows}</ul></section>'
    )


def _landing_lead_html(label):
    return (
        '<article class="landing-lead is-placeholder" aria-labelledby="landing-lead-h"><span class="placeholder-tag">Placeholder</span>'
        f'<div class="landing-lead-kicker"><span class="cintillo">Lead story</span><span class="kicker">&sect; {escape(label)}</span></div>'
        '<h2 id="landing-lead-h">The lead story for this section will appear here</h2>'
        '<p>AI-written stories are not switched on yet. When they are, readers vote on which one leads and an editor approves it.</p>'
        '<p class="concept-note">Drafted by AI &middot; Approved by [editor] &middot; [date]</p></article>'
    )


def main(page):
    listing = page.listing
    if page.kind != "listing" or listing is None or not listing.section or listing.page != 1 or listing.section in LANDING_EXCLUDED_SECTIONS:
        return None
    section = next((candidate for candidate in page.settings.sections if candidate.name == listing.section), None)
    if section is None:
        return None
    pairs = _board_pairs(page, lambda summary: summary.section == listing.section)
    shown = pairs[: max(len(listing.featured) + len(listing.entries), 1)]
    items = [_read_item(summary) for summary, _entry, _label in pairs]
    intro = f'<div class="landing-intro">{page.fragment}</div>' if page.fragment else f'<p class="landing-description">{escape(section.description)}</p>'
    older_html = (
        f'<p class="landing-older"><a href="{escape(listing.url_for_page(2), quote=True)}">Older signals</a></p>' if listing.pages > 1 else ""
    )
    signals_html = (
        '<section class="landing-signals" aria-labelledby="landing-signals-h"><div class="section-heading"><span class="cintillo">New</span>'
        f'<h2 id="landing-signals-h">Latest signals in {escape(section.label)}</h2><span class="section-heading-note">NEWEST FIRST</span></div>'
        f'{_signal_list_html(shown, show_beat=True)}{older_html}</section>'
        if shown else ""
    )
    return (
        '<div class="shipped-page section-landing">'
        f'{_landing_tabs_html(page, listing.section)}'
        f'<header class="landing-head"><span class="cintillo">Section</span><h1>{escape(section.label)}</h1>{intro}</header>'
        f'<div class="landing-layout">{_landing_lead_for_section(page, listing.section, section.label)}'
        f'<aside class="landing-rails">{_landing_clusters_html(page)}{_landing_concepts_html(items, page.site)}</aside></div>'
        f'{signals_html}</div>'
    )


def footer(page):
    links = "".join(f'<li><a href="{escape(href, quote=True)}">{escape(label)}</a></li>' for label, href in _footer_links())
    return (
        '<div class="shipped-footer">'
        '<a class="shipped-footer-wordmark" href="/"><span class="brand-word">Shipped</span></a>'
        f'<nav aria-label="Footer"><ul class="shipped-footer-links">{links}</ul></nav>'
        f'<p class="markus-footer-text">{_footer_text_html()}</p></div>'
    )


MAP_VIEW_PATH = Path(__file__).with_name("map-view.json")
MAP_BLOCK_NAMES = ("map-header", "periodic-table", "map-graph", "map-river")
MAP_MODEL_KEY = "model"
MAP_SYMBOL_PATTERN = re.compile(r"^[A-Z][a-z]$")
MAP_UNSTATED_LICENCE_WORDS = ("", "not stated", "unstated", "none", "unknown")
MAP_LICENCE_PHRASES = {
    "open": "open licence",
    "restricted": "non-commercial or research licence",
    "custom": "custom licence",
    "unstated": "licence not stated",
}
MAP_CENTRE_LIMIT = 5
MAP_CENTRE_SCAN_LIMIT = 12
MAP_NEIGHBOURS_PER_RELATION = 10
MAP_NEW_ENTITY_LIMIT = 8
MAP_PATTERN_COUNT = 6
MAP_PATTERN_ID_PREFIX = "map-pattern-"
MAP_CLUSTER_STATE_WORDS = {"new": "New", "growing": "Growing", "cooling": "Cooling"}
MAP_CLUSTER_STATE_MARKS = {"new": "●", "growing": "▲", "cooling": "▼"}
MAP_RIVER_WEEKS = 26
MAP_RIVER_STREAM_LABELS = ("Sample stream A", "Sample stream B", "Sample stream C", "Sample stream D")
MAP_RIVER_BASES = (6, 4, 3, 2)
MAP_RIVER_SWINGS = (3, 4, 2, 3)
MAP_RIVER_PHASES = (0, 5, 11, 17)
MAP_RIVER_MARKS = ((9, "born"), (15, "split"), (21, "merged"))
MAP_RIVER_COLUMN_WIDTH = 40
MAP_RIVER_MARK_SIZE = 24
MAP_RIVER_HEIGHT = 240
MAP_RIVER_MARK_BAND = 28
MAP_RIVER_UNIT_HEIGHT = 8
MAP_WHY_TABLE_NOTE = (
    "Most AI periodic tables map concepts (prompts, RAG, agents), and the product ones turn into logo walls because a tile’s "
    "position says little. This one places real signals on two measurable axes, task group and parameter size, so an empty "
    "cell is a plain fact about what we track. Mendeleev ordered elements by weight and by behaviour; the MIT CSAIL I-Con table "
    "and the DevOps tools table showed that empty cells and community-picked products make a table worth reading."
)
MAP_TILE_LEGEND = (
    ("open", "Thick solid border", "open licence stated (Apache-2.0, MIT)"),
    ("restricted", "Dashed border", "non-commercial or research-only licence"),
    ("custom", "Double border", "custom licence terms (named on the signal page)"),
    ("unstated", "Thin border", "licence not stated"),
)
MAP_STATUS_LEGEND = (
    ("available", "Available"),
    ("verified", "Verified"),
    ("announced", "Announced"),
)
MAP_PATTERN_SHAPES = (
    '<rect class="map-pattern-ink" width="6" height="6"/>',
    '<rect class="map-pattern-brand" width="6" height="6"/>',
    '<rect class="map-pattern-ground" width="6" height="6"/><path class="map-pattern-line" d="M-1 7L7 -1M-1 1L1 -1M5 7L7 5"/>',
    '<rect class="map-pattern-ground" width="6" height="6"/><circle class="map-pattern-ink" cx="3" cy="3" r="1.2"/>',
    '<rect class="map-pattern-ground" width="6" height="6"/><path class="map-pattern-line" d="M0 1.5H6"/>',
    '<rect class="map-pattern-ground" width="6" height="6"/><path class="map-pattern-line" d="M0 1.5H6M1.5 0V6"/>',
)
MAP_RIVER_MARK_SHAPES = {
    "born": ('<circle cx="8" cy="8" r="5" fill="currentColor"/>', "Cluster born"),
    "split": ('<path d="M8 2v6M8 8l-4.5 5.5M8 8l4.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8"/>', "Cluster split"),
    "merged": ('<path d="M3.5 2.5L8 8l4.5-5.5M8 8v6" fill="none" stroke="currentColor" stroke-width="1.8"/>', "Clusters merged"),
}


@lru_cache(maxsize=1)
def _map_view():
    return json.loads(MAP_VIEW_PATH.read_text(encoding="utf-8"))


def _map_positive_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        return None
    return float(value)


def _map_size_text(billions):
    if billions < 0.1:
        return f"{billions * 1000:g}M"
    return f"{billions:g}B"


def _map_range_text(low, high):
    if high < 0.1:
        return f"{low * 1000:g}–{high * 1000:g}M"
    return f"{low:g}–{high:g}B"


def _map_read_range(raw):
    if isinstance(raw, (list, tuple)):
        numbers = [_map_positive_number(value) for value in raw]
    elif isinstance(raw, str):
        numbers = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", raw)]
    else:
        return None
    if len(numbers) != 2 or None in numbers or not numbers[0] < numbers[1]:
        return None
    return (numbers[0], numbers[1])


def _map_licence_style(licence):
    text = (licence or "").strip().lower()
    if text in MAP_UNSTATED_LICENCE_WORDS:
        return "unstated"
    table = _map_view()["table"]
    if any(marker in text for marker in table["restrictedLicenceMarkers"]):
        return "restricted"
    if any(text.startswith(marker) for marker in table["openLicenceMarkers"]):
        return "open"
    return "custom"


def _map_read_model(summary, entry, group_keys):
    front = summary.front_matter or {}
    raw = front.get(MAP_MODEL_KEY)
    if not isinstance(raw, dict):
        return None
    group = _text(raw.get("taskGroup"))
    if group not in group_keys:
        _warn(summary, f"model.taskGroup {group!r} is not one of the task groups; left out of the table")
        return None
    return {
        "slug": summary.slug,
        "url": entry.url,
        "name": _text(raw.get("name")) or entry.title,
        "group": group,
        "hosted": raw.get("hosted") is True,
        "total": _map_positive_number(raw.get("parametersTotal")),
        "active": _map_positive_number(raw.get("parametersActive")),
        "range": _map_read_range(raw.get("parameterRange")),
        "licence": _text(raw.get("licence")),
        "declared_symbol": _text(raw.get("symbol")),
        "built_on": _text(raw.get("builtOn")),
        "verdict": _read_verdict(summary, front),
        "date_label": _date_label(summary),
        "sort_date": _sort_date(summary),
        "summary": summary,
    }


def _map_derive_symbol(name, taken):
    letters = re.sub(r"[^A-Za-z]", "", name or "").lower() or "x"
    first = letters[0].upper()
    for second in letters[1:] + "abcdefghijklmnopqrstuvwxyz":
        if first + second not in taken:
            return first + second
    return next(
        upper + lower
        for upper in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for lower in "abcdefghijklmnopqrstuvwxyz"
        if upper + lower not in taken
    )


def _map_assign_symbols(models):
    taken = set()
    ordered = sorted(models, key=lambda model: model["slug"])
    for model in ordered:
        declared = model["declared_symbol"]
        if declared and MAP_SYMBOL_PATTERN.match(declared) and declared not in taken:
            model["symbol"] = declared
            taken.add(declared)
        else:
            model["symbol"] = None
    for model in ordered:
        if model["symbol"] is None:
            if model["declared_symbol"]:
                _warn(model["summary"], f"model.symbol {model['declared_symbol']!r} is not a unique two-letter symbol; one was derived")
            model["symbol"] = _map_derive_symbol(model["name"], taken)
            taken.add(model["symbol"])


def _map_resolve_built_on(models):
    by_label = {}
    for model in models:
        for label in (model["name"], model["symbol"], model["slug"]):
            by_label.setdefault(label.lower(), model)
    for model in models:
        wanted = model["built_on"]
        found = by_label.get(wanted.lower()) if wanted else None
        model["built_on_model"] = found if found is not model else None


def _map_size_for_band(model):
    if model["total"] is not None:
        return model["total"]
    return model["range"][1] if model["range"] else None


def _map_band_key(model):
    table = _map_view()["table"]
    size = _map_size_for_band(model)
    if size is None:
        return table["unstatedBand"]["key"]
    chosen = table["bands"][0]["key"]
    for band in table["bands"]:
        if size >= band["from"]:
            chosen = band["key"]
    return chosen


def _map_mass_text(model):
    if model["range"]:
        return _map_range_text(*model["range"])
    if model["total"] is None:
        return "hosted" if model["hosted"] else "—"
    if model["active"] is not None:
        return f"{_map_size_text(model['total'])} / {_map_size_text(model['active'])} active"
    return _map_size_text(model["total"])


def _map_built_on_text(model):
    if not model["built_on"]:
        return ""
    found = model["built_on_model"]
    return f"on {found['symbol']}" if found else f"on {model['built_on']}"


def _map_status_mark_html(verdict):
    icon = STAMP_ICONS.get(verdict, FALLBACK_STAMP_ICON)
    return (
        f'<svg class="map-tile-status" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">{icon}</svg>'
    )


def _map_licence_phrase(licence, licence_style):
    if licence_style == "custom":
        return f"custom licence: {licence}"
    if licence:
        return f"{licence} licence"
    return MAP_LICENCE_PHRASES[licence_style]


def _map_tile_label(model, group_label):
    licence_style = _map_licence_style(model["licence"])
    parts = [
        model["name"], f"symbol {model['symbol']}", group_label, _map_mass_text(model),
        _map_licence_phrase(model["licence"], licence_style),
        model["verdict"].capitalize(),
    ]
    if model["built_on"]:
        parts.append(f"built on {model['built_on_model']['name'] if model['built_on_model'] else model['built_on']}")
    if model["date_label"]:
        parts.append(f"released {model['date_label']}")
    return ", ".join(parts)


def _map_tile_html(model, group_labels, group_shorts):
    style = _map_licence_style(model["licence"])
    foot = group_shorts[model["group"]] if model["hosted"] else _map_built_on_text(model)
    return (
        f'<a class="map-tile map-licence-{style}" href="{escape(model["url"], quote=True)}" '
        f'aria-label="{escape(_map_tile_label(model, group_labels[model["group"]]), quote=True)}">'
        f'<span class="map-tile-top"><span class="map-tile-date">{escape(model["date_label"])}</span>{_map_status_mark_html(model["verdict"])}</span>'
        f'<span class="map-tile-symbol">{escape(model["symbol"])}</span>'
        f'<span class="map-tile-name">{escape(model["name"])}</span>'
        f'<span class="map-tile-mass">{escape(_map_mass_text(model))}</span>'
        f'<span class="map-tile-foot">{escape(foot)}</span></a>'
    )


def _map_cell_html(models, group_labels, group_shorts):
    table = _map_view()["table"]
    if not models:
        return f'<span class="map-gap">{escape(table["emptyCell"])}</span>'
    ordered = sorted(models, key=lambda model: (model["sort_date"], model["name"]), reverse=True)
    limit = table["crowdedCellLimit"]
    tiles = [_map_tile_html(model, group_labels, group_shorts) for model in ordered]
    shown, hidden = tiles[:limit], tiles[limit:]
    more_html = (
        f'<details class="map-more"><summary class="map-more-summary"><span class="map-more-closed">+{len(hidden)} more</span>'
        f'<span class="map-more-open">Show fewer</span></summary><div class="map-more-tiles">{"".join(hidden)}</div></details>'
        if hidden else ""
    )
    return f'<div class="map-cell-tiles">{"".join(shown)}{more_html}</div>'


def _map_model_count_text(count):
    return f"{count} model" + ("" if count == 1 else "s")


def _map_row_head_html(kicker, label, note):
    return (
        f'<th scope="row" class="map-row-head"><span class="kicker">{escape(kicker)}</span>'
        f'<b>{escape(label)}</b><span class="map-row-note">{escape(note)}</span></th>'
    )


def _map_legend_html():
    border_rows = "".join(
        f'<li><span class="map-legend-tile map-licence-{style}" aria-hidden="true"></span><span><b>{escape(label)}</b> · {escape(text)}</span></li>'
        for style, label, text in MAP_TILE_LEGEND
    )
    status_rows = "".join(
        f'<li><svg class="map-legend-status" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">{STAMP_ICONS[key]}</svg>'
        f'<span><b>{label}</b></span></li>'
        for key, label in MAP_STATUS_LEGEND
    )
    return (
        '<section class="map-legend" aria-labelledby="map-legend-h"><h2 id="map-legend-h">How to read a tile</h2>'
        f'<ul class="map-legend-list">{border_rows}</ul>'
        f'<ul class="map-legend-status-list">{status_rows}</ul>'
        '<ul class="map-legend-rules">'
        '<li><b>Symbol</b> · two letters, unique across the table, and stable once assigned.</li>'
        '<li><b>Size</b> · Rows: total parameters. Mixture-of-experts shows total / active.</li>'
        '<li><b>On X</b> · built on another model in the table.</li>'
        '<li><b>Top of a tile</b> · date shipped, and the status mark.</li>'
        '</ul></section>'
    )


def _map_knowledge_source(page):
    lookup = getattr(page.site, "knowledge", None) if page.site is not None else None
    return getattr(lookup, "_source", None)


def _map_knowledge_index(page):
    source = _map_knowledge_source(page)
    return source.index() if source is not None else None


def _map_edited_on(page, models=()):
    index = _map_knowledge_index(page)
    stamp = (index or {}).get("asOf") or max((model["sort_date"] for model in models), default="")
    return _full_date_label(stamp[:10]) if stamp else ""


def _knowledge_week_html(page, attributes):
    stamp = (_knowledge_index(page).get("asOf") or "")[:10]
    week = f"Week of {_full_date_label(stamp)} · " if stamp else ""
    return f'<p class="front-side-kicker kicker">{escape(week)}Edited by AI</p>'


def _beats_nav_html(page, attributes):
    beats = [beat for beat in _knowledge_index(page).get("beats") or [] if beat.get("href") and beat.get("name")]
    return "".join(f'<a href="{escape(beat["href"], quote=True)}">{escape(beat["name"])}</a>' for beat in beats)


def _map_why_html(edited_on):
    stamp = f'<p class="map-edited kicker">Edited by AI on {escape(edited_on)}</p>' if edited_on else ""
    return (
        '<section class="map-why" aria-labelledby="map-why-h"><h2 id="map-why-h">Why a periodic table</h2>'
        f'<p>{escape(MAP_WHY_TABLE_NOTE)}</p>{stamp}</section>'
    )


def _map_groups_definition_html():
    rows = "".join(
        f'<div><dt>{escape(group["label"])}</dt><dd>{escape(group["definition"])}</dd></div>' for group in _map_view()["table"]["groups"]
    )
    return f'<dl class="map-group-definitions">{rows}</dl>'


def _map_table_models(page, group_keys):
    entries_by_id = {entry.item_id: entry for entry in page.entries if entry.url}
    models = [
        model
        for summary in page.summaries
        if summary.type not in (WIKI_ITEM_TYPE, PAGE_ITEM_TYPE) and summary.section != ROUNDUP_SECTION and not _is_story(summary) and summary.item_id in entries_by_id
        for model in [_map_read_model(summary, entries_by_id[summary.item_id], group_keys)]
        if model
    ]
    _map_assign_symbols(models)
    _map_resolve_built_on(models)
    return models


def _periodic_table(page, attributes):
    table = _map_view()["table"]
    groups = table["groups"]
    group_keys = {group["key"] for group in groups}
    models = _map_table_models(page, group_keys)
    edited_on = _map_edited_on(page, models)
    if not models:
        return (
            f'<p class="map-empty">{escape(table["emptyTable"])}</p>{_map_groups_definition_html()}'
            f'{_map_legend_html()}{_map_why_html(edited_on)}'
        )
    group_labels = {group["key"]: group["label"] for group in groups}
    group_shorts = {group["key"]: group["short"] for group in groups}
    on_table = [model for model in models if not model["hosted"]]
    hosted = [model for model in models if model["hosted"]]
    bands = table["bands"] + [table["unstatedBand"]]
    head_cells = "".join(
        f'<th scope="col" class="map-group-head"><span class="kicker">Group {position}</span><b>{escape(group["label"])}</b>'
        f'<span class="map-group-definition">{escape(group["definition"])}</span>'
        f'<span class="map-group-count">{_map_model_count_text(sum(1 for model in on_table if model["group"] == group["key"]))}</span></th>'
        for position, group in enumerate(groups, start=1)
    )
    body_rows = []
    for position, band in enumerate(bands, start=1):
        cells = "".join(
            '<td class="map-cell">'
            + _map_cell_html([m for m in on_table if m["group"] == group["key"] and _map_band_key(m) == band["key"]], group_labels, group_shorts)
            + "</td>"
            for group in groups
        )
        body_rows.append(f"<tr>{_map_row_head_html(f'Period {position}', band['label'], band['note'])}{cells}</tr>")
    hosted_row = table["hostedRow"]
    hosted_html = (
        '<tbody class="map-hosted"><tr>'
        f'{_map_row_head_html(hosted_row["kicker"], hosted_row["label"], hosted_row["note"])}'
        f'<td class="map-cell" colspan="{len(groups)}">{_map_cell_html(hosted, group_labels, group_shorts)}</td></tr></tbody>'
    )
    return (
        '<div class="map-table-scroll" tabindex="0" role="region" aria-labelledby="map-table-h">'
        '<table class="map-table"><caption id="map-table-h" class="map-sr-only">Models we track: columns are task groups, rows are total parameter bands.</caption>'
        f'<thead><tr><td class="map-corner"></td>{head_cells}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>{hosted_html}</table></div>'
        f'{_map_legend_html()}{_map_why_html(edited_on)}'
    )


def _map_header(page, attributes):
    index = _map_knowledge_index(page) or {}
    source = _map_knowledge_source(page)
    clusters = (source.clusters() if source is not None else None) or {}
    named_clusters = sum(1 for cluster in clusters.get("clusters") or [] if cluster.get("name"))
    signals = len(_board_pairs(page, lambda summary: True))
    stats = [("Signals", signals)]
    if index.get("entityCount") is not None:
        stats.append(("Entities", index["entityCount"]))
    if clusters:
        stats.append(("Clusters", named_clusters))
    rows = "".join(f"<div><dt>{escape(label)}</dt><dd>{value}</dd></div>" for label, value in stats)
    return f'<dl class="map-stats">{rows}</dl>'


def _map_relation_key(relation):
    return re.sub(r"[^a-z]", "", str(relation or "").lower())


def _map_relation_style(relation):
    view = _map_view()
    style = dict(view["defaultRelation"])
    style["label"] = str(relation or "related").replace("_", " ").replace("-", " ")
    style.update(view["relations"].get(_map_relation_key(relation), {}))
    return style


def _map_line_glyph_html(style):
    line_end = 34 if style["arrow"] else 42
    dash = f' stroke-dasharray="{style["dash"]}"' if style["dash"] else ""
    arrow = '<path d="M34 0.5L43 5L34 9.5z" fill="currentColor"/>' if style["arrow"] else ""
    return (
        '<svg class="map-line-glyph" viewBox="0 0 44 10" width="44" height="10" aria-hidden="true">'
        f'<line x1="3" y1="5" x2="{line_end}" y2="5" stroke="currentColor" stroke-width="{style["width"]}"{dash} stroke-linecap="round"/>{arrow}</svg>'
    )


def _map_neighbour_columns_html(neighbours, kinds, links):
    groups = {}
    for neighbour in neighbours:
        groups.setdefault(_map_relation_key(neighbour.get("relation")), []).append(neighbour)
    peak = max(int(neighbour.get("weight") or 0) for neighbour in neighbours) or 1
    ordered = sorted(groups.values(), key=lambda members: -sum(int(member.get("weight") or 0) for member in members))
    columns = []
    for members in ordered:
        style = _map_relation_style(members[0].get("relation"))
        members = sorted(members, key=lambda member: (-int(member.get("weight") or 0), str(member.get("name") or "")))
        entries = []
        for member in members[:MAP_NEIGHBOURS_PER_RELATION]:
            weight = int(member.get("weight") or 0)
            kind = escape(kinds.get(str(member.get("kind")), str(member.get("kind") or "")))
            href = links.get(str(member.get("key")))
            label = f"<i>{kind}</i>{escape(str(member.get('name') or ''))}"
            chip = f'<a class="map-chip" href="{escape(href, quote=True)}">{label}</a>' if href else f'<span class="map-chip">{label}</span>'
            entries.append(
                f'<li>{chip}<span class="map-weight" aria-hidden="true"><span style="width:{round(100 * weight / peak)}%"></span></span>'
                f'<span class="map-weight-number" title="Signals that link both">{weight}</span></li>'
            )
        extra = len(members) - MAP_NEIGHBOURS_PER_RELATION
        extra_html = f'<p class="map-neighbour-more">+{extra} more in the wiki</p>' if extra > 0 else ""
        columns.append(
            f'<div class="map-neighbour-column"><h4>{_map_line_glyph_html(style)}<span>{escape(style["label"])}</span></h4>'
            f'<ul>{"".join(entries)}</ul>{extra_html}</div>'
        )
    return f'<div class="map-neighbours">{"".join(columns)}</div>'


def _map_centres(source, index):
    by_key = {str(entity.get("key")): entity for entity in index.get("entities") or []}
    ranked = [key for key in index.get("trending") or [] if key in by_key]
    ranked += [key for key, _ in sorted(by_key.items(), key=lambda pair: -int(pair[1].get("itemCount") or 0)) if key not in ranked]
    centres = []
    for key in ranked[:MAP_CENTRE_SCAN_LIMIT]:
        entity = source.entity(key)
        if entity and entity.get("neighbours"):
            centres.append(entity)
        if len(centres) == MAP_CENTRE_LIMIT:
            break
    return centres


def _map_new_entities_html(index):
    entities = [entity for entity in index.get("entities") or [] if entity.get("isNew")]
    entities.sort(key=lambda entity: (-int(entity.get("itemCount") or 0), str(entity.get("name") or "")))
    kinds = {str(kind.get("key")): str(kind.get("label") or kind.get("key")) for kind in index.get("kinds") or []}
    if not entities:
        body = '<p class="map-empty">Nothing is new on the map this week.</p>'
    else:
        rows = "".join(
            '<li><svg viewBox="0 0 16 16" width="16" height="16" role="img" aria-label="New"><circle cx="8" cy="8" r="5" fill="currentColor"/></svg>'
            + (f'<a href="{escape(entity["href"], quote=True)}">{escape(str(entity.get("name")))}</a>' if entity.get("href") else f'<span>{escape(str(entity.get("name")))}</span>')
            + f'<span class="kicker">{escape(kinds.get(str(entity.get("kind")), str(entity.get("kind") or "")))}</span></li>'
            for entity in entities[:MAP_NEW_ENTITY_LIMIT]
        )
        body = f'<p class="map-new-count kicker">{len(entities)} new of {index.get("entityCount", len(index.get("entities") or []))} on the map</p><ul>{rows}</ul>'
    return (
        '<aside class="map-new" aria-labelledby="map-new-h"><h2 id="map-new-h">New on the map this week</h2>'
        f'{body}<a class="map-new-link" href="/wiki/">All of them in the wiki</a></aside>'
    )


def _map_graph(page, attributes):
    source = _map_knowledge_source(page)
    index = source.index() if source is not None else None
    if not index:
        return '<p class="map-empty">The concept graph appears once the first knowledge snapshot is published.</p>'
    kinds = {str(kind.get("key")): str(kind.get("label") or kind.get("key")) for kind in index.get("kinds") or []}
    links = {str(entity.get("key")): entity["href"] for entity in index.get("entities") or [] if entity.get("href")}
    centres = _map_centres(source, index)
    if not centres:
        return f'<div class="map-graph-layout"><p class="map-empty">No concept has recorded connections yet.</p>{_map_new_entities_html(index)}</div>'
    inputs, labels, panels = [], [], []
    present_relations = {}
    for position, entity in enumerate(centres):
        identifier = f"map-centre-{position}"
        checked = " checked" if position == 0 else ""
        inputs.append(f'<input class="map-centre-input" type="radio" name="map-centre" id="{identifier}"{checked}>')
        labels.append(f'<label for="{identifier}">{escape(str(entity.get("name")))}</label>')
        for neighbour in entity["neighbours"]:
            present_relations[_map_relation_key(neighbour.get("relation"))] = _map_relation_style(neighbour.get("relation"))
        count = int(entity.get("itemCount") or 0)
        page_link = (
            f'<a class="map-open-concept" href="{escape(entity["href"], quote=True)}">Open concept page</a>' if entity.get("href") else ""
        )
        panels.append(
            f'<article class="map-centre-panel" data-centre="{identifier}">'
            f'<div class="map-centre-card"><span class="kicker">{escape(kinds.get(str(entity.get("kind")), str(entity.get("kind") or "")))} · selected</span>'
            f'<h3>{escape(str(entity.get("name")))}</h3><p class="map-centre-count">{count} signal{"" if count == 1 else "s"}</p>{page_link}</div>'
            f'{_map_neighbour_columns_html(entity["neighbours"], kinds, links)}</article>'
        )
    lines_legend = "".join(
        f'<li>{_map_line_glyph_html(style)}<span>{escape(style["label"])}</span></li>' for style in present_relations.values()
    )
    return (
        '<div class="map-graph-layout"><div class="map-graph-main">'
        '<div class="map-centre-picker"><span class="kicker">Centre on</span>'
        f'{"".join(inputs)}<div class="map-centre-labels" role="group" aria-label="Centre the graph on">{"".join(labels)}</div>'
        f'<div class="map-centre-panels">{"".join(panels)}</div></div>'
        f'<div class="map-lines"><span class="kicker">Lines</span><ul>{lines_legend}</ul>'
        '<p class="map-lines-note">Weight is the number of signals that link both ends.</p></div></div>'
        f'{_map_new_entities_html(index)}</div>'
    )


def _map_pattern_defs_html():
    patterns = "".join(
        f'<pattern id="{MAP_PATTERN_ID_PREFIX}{position}" width="6" height="6" patternUnits="userSpaceOnUse">{shape}</pattern>'
        for position, shape in enumerate(MAP_PATTERN_SHAPES)
    )
    return f'<svg class="map-pattern-defs" width="0" height="0" aria-hidden="true" focusable="false"><defs>{patterns}</defs></svg>'


def _map_now_html(clusters):
    named = [cluster for cluster in clusters.get("clusters") or [] if cluster.get("name")]
    if not named:
        return '<p class="map-empty">No clusters have been named yet.</p>'
    named.sort(key=lambda cluster: -int(cluster.get("itemCount") or 0))
    peak = max(int(cluster.get("itemCount") or 0) for cluster in named) or 1
    rows = []
    for position, cluster in enumerate(named):
        count = int(cluster.get("itemCount") or 0)
        state = str(cluster.get("state") or "")
        state_html = (
            f'<span class="map-cluster-state">{MAP_CLUSTER_STATE_MARKS[state]} {MAP_CLUSTER_STATE_WORDS[state]}</span>' if state in MAP_CLUSTER_STATE_WORDS else ""
        )
        name = escape(str(cluster["name"]))
        link = cluster.get("href")
        title = f'<a href="{escape(link, quote=True)}">{name}</a>' if link and str(link).startswith("/") else name
        width = max(4, round(240 * count / peak))
        rows.append(
            f'<li><span class="map-cluster-name">{title}</span>'
            f'<svg class="map-cluster-bar" viewBox="0 0 240 14" width="240" height="14" role="img" aria-label="{count} signals">'
            f'<rect x="0.75" y="0.75" width="{width - 1.5}" height="12.5" fill="url(#{MAP_PATTERN_ID_PREFIX}{position % MAP_PATTERN_COUNT})" stroke="currentColor" stroke-width="1.5"/></svg>'
            f'<span class="map-cluster-count">{count} signals</span>{state_html}</li>'
        )
    return f'<ul class="map-cluster-list">{"".join(rows)}</ul>'


def _map_sample_river_html():
    values = [
        [
            max(1, round(MAP_RIVER_BASES[stream] + MAP_RIVER_SWINGS[stream] * math.sin((week + MAP_RIVER_PHASES[stream]) / 4)))
            for week in range(MAP_RIVER_WEEKS)
        ]
        for stream in range(len(MAP_RIVER_STREAM_LABELS))
    ]
    width = MAP_RIVER_COLUMN_WIDTH * MAP_RIVER_WEEKS
    total_height = MAP_RIVER_HEIGHT + MAP_RIVER_MARK_BAND
    columns = []
    for week in range(MAP_RIVER_WEEKS):
        floor = total_height
        for stream in range(len(MAP_RIVER_STREAM_LABELS)):
            height = values[stream][week] * MAP_RIVER_UNIT_HEIGHT
            floor -= height
            columns.append(
                f'<rect x="{week * MAP_RIVER_COLUMN_WIDTH + 1}" y="{floor}" width="{MAP_RIVER_COLUMN_WIDTH - 2}" height="{height - 1}" '
                f'fill="url(#{MAP_PATTERN_ID_PREFIX}{stream % MAP_PATTERN_COUNT})" stroke="currentColor" stroke-width="1"/>'
            )
    marks = "".join(
        f'<svg x="{(week - 1) * MAP_RIVER_COLUMN_WIDTH + (MAP_RIVER_COLUMN_WIDTH - MAP_RIVER_MARK_SIZE) // 2}" y="2" width="{MAP_RIVER_MARK_SIZE}" height="{MAP_RIVER_MARK_SIZE}" viewBox="0 0 16 16" aria-label="{MAP_RIVER_MARK_SHAPES[kind][1]}">{MAP_RIVER_MARK_SHAPES[kind][0]}</svg>'
        for week, kind in MAP_RIVER_MARKS
    )
    stream_labels = "".join(
        f'<li><svg viewBox="0 0 14 14" width="14" height="14" aria-hidden="true"><rect x="0.75" y="0.75" width="12.5" height="12.5" fill="url(#{MAP_PATTERN_ID_PREFIX}{stream % MAP_PATTERN_COUNT})" stroke="currentColor" stroke-width="1.5"/></svg>{escape(label)}</li>'
        for stream, label in reversed(list(enumerate(MAP_RIVER_STREAM_LABELS)))
    )
    legend = "".join(
        f'<li><svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">{MAP_RIVER_MARK_SHAPES[kind][0]}</svg>{label}</li>'
        for kind, label in (("born", "Born"), ("split", "Split"), ("merged", "Merged"))
    )
    return (
        '<section class="map-river-sample is-placeholder" aria-labelledby="map-river-h"><span class="placeholder-tag">Placeholder</span>'
        '<div class="section-heading"><span class="cintillo">Over time</span><h2 id="map-river-h">Cluster river</h2>'
        '<span class="section-heading-note">Sample 26-week history, not real data</span></div>'
        '<p class="map-river-note">The river will show signals per cluster per week, with a time scrubber. This is a sample drawn from made-up numbers to show the design.</p>'
        '<div class="map-river-figure">'
        f'<svg class="map-river-chart" viewBox="0 0 {width} {total_height}" role="img" aria-label="Sample stacked river of four made-up streams over 26 weeks, with a birth in week 9, a split in week 15 and a merge in week 21. Placeholder data.">{marks}{"".join(columns)}</svg>'
        f'<ul class="map-river-labels">{stream_labels}</ul></div>'
        '<div class="map-river-axis kicker"><span>Wk 1</span><span>Wk 6</span><span>Wk 12</span><span>Wk 18</span><span>Wk 26</span></div>'
        f'<ul class="map-river-legend">{legend}<li>Each stream is labelled at its end and filled with its own pattern.</li></ul></section>'
    )


def _map_river(page, attributes):
    source = _map_knowledge_source(page)
    clusters = (source.clusters() if source is not None else None) or {}
    now_html = (
        '<section class="map-now" aria-labelledby="map-now-h"><div class="section-heading"><span class="cintillo">Now</span>'
        '<h2 id="map-now-h">Clusters this week</h2></div>'
        f'{_map_now_html(clusters)}</section>'
    )
    return _map_pattern_defs_html() + now_html + _map_sample_river_html()


def _map_block(name, attributes, page):
    if name == "map-header":
        return _map_header(page, attributes)
    if name == "periodic-table":
        return _periodic_table(page, attributes)
    if name == "map-graph":
        return _map_graph(page, attributes)
    return _map_river(page, attributes)


STORIES_SECTION = "stories"
STORY_KIND = "story"
STORY_VOTE_SUBJECT_TYPE = "story"
APPROVED_STORIES_MEMO = "shipped-approved-stories"
STORY_APPROVED_STATUS = "approved"
STORY_AGENT_AUTHOR = "agent"
STORY_HOME_ALSO_LIMIT = 2
STORY_HOME_LEAD_PAIR_LIMIT = 3
STORY_CITATION_MARKER = re.compile(r"\[(\d+)\]")
STORY_HTML_TAG = re.compile(r"(<[^>]*>)")
STORY_PROJECTION_PATH = Path(__file__).with_name("projection.json")
STORY_ARROW_SVG = (
    '<svg viewBox="0 0 120 14" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true">'
    '<path d="M0 7h110"/><path d="M104 1l9 6-9 6"/></svg>'
)
STORY_PROPOSAL_TAG_SVG = (
    '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">'
    '<path d="M10.5 2.5l3 3-8 8H2.5v-3z"/></svg>'
)
HOME_LEAD_PLACEHOLDER_HTML = (
    '<article class="front-lead is-placeholder" aria-labelledby="front-lead-h">\n'
    '<span class="placeholder-tag">Placeholder</span>\n'
    '<div class="front-lead-figure" role="img" aria-label="Lead image: three lines of descent between decision models">\n'
    '<span class="front-lineage-from">[Later model]</span><svg viewBox="0 0 60 12" width="60" height="12" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true"><path d="M0 6h52"/><path d="M48 1l7 5-7 5"/></svg><span class="front-lineage-to">[Earlier model]</span>\n'
    '<span class="front-lineage-from">[Later model]</span><svg viewBox="0 0 60 12" width="60" height="12" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true"><path d="M0 6h52"/><path d="M48 1l7 5-7 5"/></svg><span class="front-lineage-to">[Earlier model]</span>\n'
    '<span class="front-lineage-from">[Later model]</span><svg viewBox="0 0 60 12" width="60" height="12" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true"><path d="M0 6h52"/><path d="M48 1l7 5-7 5"/></svg><span class="front-lineage-to">[Earlier model]</span>\n'
    '<p class="front-lead-caption">Three “built on” relations from the map · Figure: Shipped map, Edited by AI</p>\n'
    '</div>\n'
    '<div class="front-lead-labels"><span class="cintillo">Lead story</span><span class="kicker">§ Decisions in the wild</span></div>\n'
    '<h1 id="front-lead-h"><a href="/topics/decision-models/">Decision models are starting to have family trees</a></h1>\n'
    '<p class="front-lead-standfirst">Three decision models released since [date] say whose weights they started from. The map now draws those lines, and a new concept is waiting for your vote.</p>\n'
    '<p class="front-provenance"><span class="front-ai-mark">AI</span><span>Edited by AI</span><span aria-hidden="true">·</span><span><b>[n]</b> reader votes</span><span aria-hidden="true">·</span><span>Approved by <b>[editor]</b> on [date]</span></p>\n'
    '<p class="front-chips"><span class="entity-chip"><i>topic</i>Decision models</span><span class="entity-chip"><i>task</i>[task]</span><span class="entity-chip"><i>model</i>[model]</span><span class="entity-chip"><i>maker</i>[maker]</span></p>\n'
    '</article>'
)
HOME_ALSO_PLACEHOLDER_HTML = (
    '<section class="front-stories is-placeholder" aria-labelledby="front-stories-h">\n'
    '<span class="placeholder-tag">Placeholder</span>\n'
    '<div class="front-section-heading"><span class="cintillo">Stories</span><h2 id="front-stories-h">Also on the map this week</h2></div>\n'
    '<div class="front-story-grid">\n'
    '<article class="front-story"><span class="kicker">§ [Section]</span><h3><a href="/new/">[Story headline]</a></h3><p>[One-sentence standfirst, written by AI.]</p><p class="front-provenance"><span class="front-ai-mark">AI</span><span>Edited by AI</span><span aria-hidden="true">·</span><span>Approved by <b>[editor]</b> on [date]</span></p><p class="front-chips"><span class="entity-chip"><i>cluster</i>[cluster]</span><span class="entity-chip"><i>model</i>[model]</span></p></article>\n'
    '<article class="front-story"><span class="kicker">§ [Section]</span><h3><a href="/new/">[Story headline]</a></h3><p>[One-sentence standfirst, written by AI.]</p><p class="front-provenance"><span class="front-ai-mark">AI</span><span>Edited by AI</span><span aria-hidden="true">·</span><span>Approved by <b>[editor]</b> on [date]</span></p><p class="front-chips"><span class="entity-chip"><i>cluster</i>[cluster]</span><span class="entity-chip"><i>model</i>[model]</span></p></article>\n'
    '</div>\n'
    '</section>'
)


@lru_cache(maxsize=1)
def _story_section_labels():
    sections = json.loads(STORY_PROJECTION_PATH.read_text(encoding="utf-8")).get("urls", {}).get("sections", {})
    return {name: entry.get("label", name) for name, entry in sections.items()}


def _story_front(summary):
    return summary.front_matter or {}


def _is_story(summary):
    return _story_front(summary).get("kind") == STORY_KIND


def _story_mapping(front, key):
    value = front.get(key)
    return value if isinstance(value, dict) else {}


def _story_is_approved(summary):
    return _story_mapping(_story_front(summary), "approval").get("status") == STORY_APPROVED_STATUS


def item_filter(summary):
    return not _is_story(summary) or _story_is_approved(summary)


def _read_story_concepts(front):
    raw = front.get("concepts")
    return [
        {"kind": _text(concept.get("kind")), "name": _text(concept.get("name"))}
        for concept in (raw if isinstance(raw, list) else [])
        if isinstance(concept, dict) and _text(concept.get("kind")) and _text(concept.get("name"))
    ]


def _read_story_cites(front):
    raw = front.get("cites")
    cites = []
    for cite in raw if isinstance(raw, list) else []:
        if not isinstance(cite, dict):
            continue
        number = cite.get("n")
        if isinstance(number, bool) or not isinstance(number, int) or not _text(cite.get("title")):
            continue
        url = _text(cite.get("url"))
        if url and (urlparse(url).scheme not in SAFE_URL_SCHEMES or not urlparse(url).netloc):
            url = None
        cites.append({"n": number, "title": _text(cite.get("title")), "url": url, "date": _date_text(cite.get("date"))})
    return cites


def _read_story_pairs(front):
    raw = _story_mapping(front, "figure").get("pairs")
    return [
        {"child": _text(pair.get("child")), "parent": _text(pair.get("parent"))}
        for pair in (raw if isinstance(raw, list) else [])
        if isinstance(pair, dict) and _text(pair.get("child")) and _text(pair.get("parent"))
    ]


def _read_story_proposal(front):
    proposal = front.get("proposes")
    if not isinstance(proposal, dict) or not _text(proposal.get("name")):
        return None
    return {"kind": _text(proposal.get("kind")) or "concept", "name": _text(proposal.get("name")), "why": _text(proposal.get("why"))}


def _read_story(summary, entry=None):
    front = _story_front(summary)
    approval = _story_mapping(front, "approval")
    drafting = _story_mapping(front, "drafting")
    return {
        "title": _text(entry.title if entry is not None else None) or _text(summary.title) or _text(front.get("title")) or "",
        "url": entry.url if entry is not None else None,
        "standfirst": _text(front.get("standfirst")),
        "section": _text(front.get("section")),
        "concepts": _read_story_concepts(front),
        "cites": _read_story_cites(front),
        "pairs": _read_story_pairs(front),
        "proposes": _read_story_proposal(front),
        "drafted_by_ai": drafting.get("by") == STORY_AGENT_AUTHOR,
        "approved_by": _text(approval.get("by")),
        "approved_at": _timestamp_text(approval.get("at")),
    }


def _story_section_label(story):
    return _story_section_labels().get(story["section"], story["section"] or "")


def _approved_stories(page):
    entries_by_id = {entry.item_id: entry for entry in page.entries if entry.url}
    stories = [
        (summary, _read_story(summary, entries_by_id[summary.item_id]))
        for summary in page.summaries
        if _is_story(summary) and _story_is_approved(summary) and summary.item_id in entries_by_id
    ]
    stories.sort(key=lambda pair: (pair[1]["approved_at"] or "", pair[0].slug), reverse=True)
    return [story for _summary, story in stories]


def _story_provenance_html(story, css_prefix):
    separator = '<span aria-hidden="true">&middot;</span>'
    parts = ["Drafted by AI"] if story["drafted_by_ai"] else []
    parts.append(f'Approved by <b>{escape(story["approved_by"])}</b>' if story["approved_by"] else "Approved")
    if story["approved_at"]:
        parts.append(escape(_full_date_label(story["approved_at"])))
    mark = f'<span class="{css_prefix}-ai-mark">AI</span>' if story["drafted_by_ai"] else ""
    return mark + separator.join(f"<span>{part}</span>" for part in parts)


def _story_lineage_row_html(pair):
    return (
        f'<div class="story-lineage-row"><span class="story-node story-node-child"><b>{escape(pair["child"])}</b></span>'
        f'<span class="story-arrow">{STORY_ARROW_SVG}<span>built on</span></span>'
        f'<span class="story-node"><b>{escape(pair["parent"])}</b></span></div>'
    )


def _story_pairs_description(pairs):
    return ", ".join(f'{pair["child"]} built on {pair["parent"]}' for pair in pairs)


def _story_figure_html(story):
    if not story["pairs"]:
        return ""
    rows = "".join(_story_lineage_row_html(pair) for pair in story["pairs"])
    description = escape(_story_pairs_description(story["pairs"]), quote=True)
    return (
        '<figure class="story-figure">'
        f'<div class="story-lineage" role="img" aria-label="Diagram, each joined by a built-on arrow: {description}">{rows}</div>'
        '<figcaption class="story-figcaption"><span>Each model points to the model it is built on.</span>'
        '<span class="story-figure-credit">Figure: Shipped map</span></figcaption></figure>'
    )


def _story_body_with_citations(body_html, story):
    cited_numbers = {str(cite["n"]) for cite in story["cites"]}

    def link_marker(match):
        number = match.group(1)
        if number not in cited_numbers:
            return match.group(0)
        return f'<a href="#src-{number}" class="story-cite" aria-label="Source {number}">{number}</a>'

    inside_link = False
    pieces = []
    for piece in STORY_HTML_TAG.split(body_html):
        if piece.startswith("<"):
            lowered = piece.lower()
            if lowered.startswith("<a ") or lowered == "<a>":
                inside_link = True
            elif lowered.startswith("</a"):
                inside_link = False
            pieces.append(piece)
        else:
            pieces.append(piece if inside_link else STORY_CITATION_MARKER.sub(link_marker, piece))
    return "".join(pieces)


def _story_proposal_html(story):
    proposal = story["proposes"]
    if not proposal:
        return ""
    why = f'<span class="kicker">{escape(proposal["why"])}</span>' if proposal["why"] else ""
    return (
        '<section id="story-map" class="story-map-box" aria-labelledby="story-changes-h"><div class="story-map-head">'
        '<h2 id="story-changes-h">What this changes on the map</h2>'
        f'<span class="story-draft-tag">{STORY_PROPOSAL_TAG_SVG}Proposal &middot; not yet approved</span></div>'
        '<div class="story-map-change"><svg viewBox="0 0 16 16" width="18" height="18" aria-hidden="true"><circle cx="8" cy="8" r="5" fill="currentColor"/></svg>'
        f'<div class="story-map-change-text"><strong>Proposes the new {escape(proposal["kind"])} “{escape(proposal["name"])}”</strong>{why}</div></div></section>'
    )


def _story_react_html(summary):
    subject = {"type": STORY_VOTE_SUBJECT_TYPE, "id": _subject(summary)}
    return (
        '<section id="story-react" class="story-react" aria-labelledby="story-react-h">'
        '<h2 id="story-react-h" class="kicker">Was this story right?</h2>'
        f'{_island("Vote", subject, css_class="story-vote-island")}'
        f'{_island("Flag", subject, css_class="story-flag-island")}</section>'
    )


def _story_source_row_html(cite):
    title = escape(cite["title"])
    host = urlparse(cite["url"]).netloc if cite["url"] else ""
    if cite["url"]:
        title = f'<a href="{escape(cite["url"], quote=True)}" rel="noopener">{title}</a>'
    meta = " &middot; ".join(part for part in (escape(host), escape(_full_date_label(cite["date"])) if cite["date"] else "") if part)
    meta_html = f'<span class="story-source-meta">{meta}</span>' if meta else ""
    return f'<li id="src-{cite["n"]}"><span class="story-cite">{cite["n"]}</span><span class="story-source-title">{title}</span>{meta_html}</li>'


def _story_sources_html(story):
    if not story["cites"]:
        return ""
    rows = "".join(_story_source_row_html(cite) for cite in sorted(story["cites"], key=lambda cite: cite["n"]))
    return f'<ol class="story-sources" aria-label="Signals cited"><li class="kicker story-sources-heading">Signals cited</li>{rows}</ol>'


def _story_rail_html(story, site):
    if not story["concepts"]:
        return ""
    return (
        '<aside class="story-rails"><section class="rail story-rail" aria-labelledby="story-concepts-h">'
        f'<h2 id="story-concepts-h" class="rail-h">Concepts in this story</h2>'
        f'<div class="story-chips">{_entity_chips_html(story["concepts"], site)}</div></section></aside>'
    )


def _story_page_html(html, summary, site):
    story = _read_story(summary)
    header_end = html.find("</header>")
    body_html = (html[header_end + len("</header>"):] if header_end >= 0 else html).strip()
    if body_html.endswith("</article>"):
        body_html = body_html[: -len("</article>")]
    section_label = _story_section_label(story)
    section_crumb = (
        f'<span aria-hidden="true">/</span><a href="/{escape(story["section"], quote=True)}/">{escape(section_label)}</a>' if story["section"] else ""
    )
    standfirst = f'<p class="story-standfirst">{escape(story["standfirst"])}</p>' if story["standfirst"] else ""
    return (
        '<div class="shipped-page story-page"><div class="story-layout"><article class="story-article" aria-labelledby="story-h">'
        '<nav class="story-breadcrumb" aria-label="Breadcrumb"><a href="/">Front</a><span aria-hidden="true">/</span>'
        f'<a href="/{STORIES_SECTION}/">Stories</a>{section_crumb}</nav>'
        f'<div class="story-flags"><span class="cintillo">Story</span><span class="kicker story-flags-section">{escape(section_label)}</span></div>'
        f'<h1 id="story-h" class="story-title">{escape(story["title"])}</h1>{standfirst}'
        f'<div class="story-provenance">{_story_provenance_html(story, "story")}</div>'
        f'{_story_figure_html(story)}'
        f'<div class="story-body">{_story_body_with_citations(body_html, story)}</div>'
        f'{_story_proposal_html(story)}{_story_react_html(summary)}{_story_sources_html(story)}'
        f'</article>{_story_rail_html(story, site)}</div></div>'
    )


def _home_lead_figure_html(story):
    pairs = story["pairs"][:STORY_HOME_LEAD_PAIR_LIMIT]
    if not pairs:
        return ""
    arrow = (
        '<svg viewBox="0 0 60 12" width="60" height="12" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true">'
        '<path d="M0 6h52"/><path d="M48 1l7 5-7 5"/></svg>'
    )
    cells = "".join(
        f'<span class="front-lineage-from">{escape(pair["child"])}</span>{arrow}<span class="front-lineage-to">{escape(pair["parent"])}</span>'
        for pair in pairs
    )
    relations = len(story["pairs"])
    noun = "relation" if relations == 1 else "relations"
    description = escape(_story_pairs_description(pairs), quote=True)
    return (
        f'<div class="front-lead-figure" role="img" aria-label="Lead image, built-on lines of descent: {description}">{cells}'
        f'<p class="front-lead-caption">{relations} “built on” {noun} from the map. Each model points to the model it is built on · Figure: Shipped map</p></div>'
    )


def _home_story_tail_html(story, site):
    chips = _entity_chips_html(story["concepts"], site)
    return f'<p class="front-provenance">{_story_provenance_html(story, "front")}</p>' + (f'<p class="front-chips">{chips}</p>' if chips else "")


def _home_lead_html(story, site):
    standfirst = f'<p class="front-lead-standfirst">{escape(story["standfirst"])}</p>' if story["standfirst"] else ""
    return (
        '<article class="front-lead" aria-labelledby="front-lead-h">'
        f'{_home_lead_figure_html(story)}'
        f'<div class="front-lead-labels"><span class="cintillo">Lead story</span><span class="kicker">&sect; {escape(_story_section_label(story))}</span></div>'
        f'<h1 id="front-lead-h"><a href="{escape(story["url"], quote=True)}">{escape(story["title"])}</a></h1>'
        f'{standfirst}{_home_story_tail_html(story, site)}</article>'
    )


def _home_also_story_html(story, site):
    standfirst = f'<p>{escape(story["standfirst"])}</p>' if story["standfirst"] else ""
    return (
        f'<article class="front-story"><span class="kicker">&sect; {escape(_story_section_label(story))}</span>'
        f'<h3><a href="{escape(story["url"], quote=True)}">{escape(story["title"])}</a></h3>'
        f'{standfirst}{_home_story_tail_html(story, site)}</article>'
    )


def _home_also_html(stories, site):
    cards = "".join(_home_also_story_html(story, site) for story in stories)
    return (
        '<section class="front-stories" aria-labelledby="front-stories-h">'
        '<div class="front-section-heading"><span class="cintillo">Stories</span><h2 id="front-stories-h">Also on the map this week</h2></div>'
        f'<div class="front-story-grid">{cards}</div></section>'
    )


def _stories_block(page, attributes):
    part = attributes.get("part")
    stories = _approved_stories(page)
    if part == "lead":
        return _home_lead_html(stories[0], page.site) if stories else HOME_LEAD_PLACEHOLDER_HTML
    if part == "also":
        also = stories[1 : 1 + STORY_HOME_ALSO_LIMIT]
        return _home_also_html(also, page.site) if also else HOME_ALSO_PLACEHOLDER_HTML
    raise ValueError(f"unknown stories part {part!r}")


def _landing_lead_story_html(story):
    standfirst = f'<p>{escape(story["standfirst"])}</p>' if story["standfirst"] else ""
    return (
        '<article class="landing-lead" aria-labelledby="landing-lead-h">'
        f'<div class="landing-lead-kicker"><span class="cintillo">Lead story</span><span class="kicker">&sect; {escape(_story_section_label(story))}</span></div>'
        f'<h2 id="landing-lead-h"><a href="{escape(story["url"], quote=True)}">{escape(story["title"])}</a></h2>'
        f'{standfirst}<p class="concept-note">{_story_provenance_html(story, "front")}</p></article>'
    )


def _landing_lead_for_section(page, section_name, label):
    story = next((candidate for candidate in _approved_stories(page) if candidate["section"] == section_name), None)
    return _landing_lead_story_html(story) if story else _landing_lead_html(label)


def _citation_page_path(url):
    if not url:
        return None
    path = urlparse(url).path
    if path.endswith("/index.html"):
        path = path[: -len("index.html")]
    trimmed = path.strip("/")
    return f"/{trimmed}/" if trimmed else None


def _approved_story_records(site):
    def build():
        ordered = sorted(
            (
                (summary, _read_story(summary))
                for summary in site.items
                if _is_story(summary) and _story_is_approved(summary)
            ),
            key=lambda pair: (pair[1]["approved_at"] or "", pair[0].slug),
            reverse=True,
        )
        records = []
        for summary, story in ordered:
            story["url"] = _signal_url(summary)
            numbers_by_path = {_citation_page_path(cite["url"]): cite["n"] for cite in sorted(story["cites"], key=lambda cite: -cite["n"])}
            numbers_by_path.pop(None, None)
            story["cited_paths"] = numbers_by_path
            records.append(story)
        return records

    return site.memo(APPROVED_STORIES_MEMO, build)


def _story_approval_text(story):
    parts = [f'Approved by <b>{escape(story["approved_by"])}</b>' if story["approved_by"] else "Approved"]
    if story["approved_at"]:
        parts.append(escape(_full_date_label(story["approved_at"])))
    return " &middot; ".join(parts)


def _stories_citing_signal(site, signal_path):
    return [(story, story["cited_paths"][signal_path]) for story in _approved_story_records(site) if signal_path in story["cited_paths"]]


def _stories_citing_signal_html(summary, site):
    if site is None:
        return ""
    citing = _stories_citing_signal(site, _signal_url(summary))
    if not citing:
        return ""
    rows = "".join(
        f'<li><a class="signal-story-title" href="{escape(story["url"], quote=True)}">{escape(story["title"])}</a>'
        f'<span class="signal-story-meta">Cited as [{number}] &middot; {_story_approval_text(story)}</span></li>'
        for story, number in citing
    )
    return (
        '<section class="signal-rail-block signal-stories" aria-labelledby="signal-stories-h">'
        f'<h2 id="signal-stories-h">Appears in these stories</h2><ul class="signal-story-list">{rows}</ul></section>'
    )


def _topic_signal_paths(site, tag):
    return {
        _signal_url(summary)
        for summary in site.items
        if summary.type not in (WIKI_ITEM_TYPE, PAGE_ITEM_TYPE) and not _is_story(summary) and _read_item(summary)["tags"][:1] == [tag]
    }


def _story_names_concept(story, names):
    return any(concept["name"].lower() in names for concept in story["concepts"])


def _stories_for_topic(site, key, label, tag):
    names = {label.lower(), key.lower()}
    signal_paths = _topic_signal_paths(site, tag)
    return [
        story for story in _approved_story_records(site)
        if _story_names_concept(story, names) or signal_paths & set(story["cited_paths"])
    ]


def _concept_stories(page, attributes):
    stories = _stories_for_topic(page.site, attributes["key"], attributes["label"], attributes["tag"])
    if not stories:
        return ""
    rows = "".join(
        f'<li><a class="concept-story-title" href="{escape(story["url"], quote=True)}">{escape(story["title"])}</a>'
        f'<span class="concept-note">{_story_approval_text(story)}</span></li>'
        for story in stories
    )
    return (
        '<section class="concept-column-narrow concept-stories" aria-labelledby="stories-h">'
        f'<h2 id="stories-h">Stories that cite it</h2><ul class="concept-story-list">{rows}</ul></section>'
    )


def block(name, attributes, page):
    if name in MAP_BLOCK_NAMES:
        return _map_block(name, attributes, page)
    if name == "desk-board":
        return _desk_board(page, attributes)
    if name == "front":
        return _front_block(page, attributes)
    if name == "stories":
        return _stories_block(page, attributes)
    if name == "topic-board":
        return _topic_board(page, attributes)
    if name == "concept-stories":
        return _concept_stories(page, attributes)
    if name == "map-week":
        return _knowledge_week_html(page, attributes)
    if name == "beats-nav":
        return _beats_nav_html(page, attributes)
    if name in CONCEPT_BLOCKS:
        return CONCEPT_BLOCKS[name](page, attributes)
    raise ValueError(f"unknown block {name!r}")


@lru_cache(maxsize=1)
def _newsletter_lists():
    return json.loads(NEWSLETTER_LISTS_PATH.read_text(encoding="utf-8"))


def _newsletter_signup_html():
    lists = _newsletter_lists()
    list_ids = ",".join(entry["id"] for entry in lists)
    return (
        '<section class="newsletter-signup" aria-labelledby="newsletter-signup-heading">'
        f'<h2 id="newsletter-signup-heading">{escape(NEWSLETTER_HEADING)}</h2>'
        f'<p class="newsletter-dek">{escape(NEWSLETTER_DEK)}</p>'
        f'<papyrus-newsletter lists="{escape(list_ids, quote=True)}" '
        f'data-lists="{escape(json.dumps(lists), quote=True)}" '
        f'consent="{escape(NEWSLETTER_CONSENT, quote=True)}" form-id="roundup-archive" '
        'button="Subscribe" label="Email address"></papyrus-newsletter>'
        f'<script src="{NEWSLETTER_SCRIPT_PATH}" defer></script>'
        f'<p class="newsletter-feed-note">{NEWSLETTER_FEED_NOTE}</p>'
        '</section>'
    )


FRONT_NEWSLETTER_HEADING = "The Weekly"
FRONT_NEWSLETTER_DEK = "New arrivals in machine learning. One email on Fridays."
FRONT_NEWSLETTER_FORM_ID = "front-page"


def _front_signal_count_html(page):
    count = len(_board_pairs(page, lambda summary: True))
    label = "signal" if count == 1 else "signals"
    return f'<span class="front-stat"><b>{count}</b> {label}</span>'


def _front_newsletter_html():
    lists = _newsletter_lists()
    list_ids = ",".join(entry["id"] for entry in lists)
    return (
        '<section class="front-weekly" aria-labelledby="front-weekly-heading">'
        '<div class="front-weekly-copy">'
        f'<h2 id="front-weekly-heading">{escape(FRONT_NEWSLETTER_HEADING)}</h2>'
        f'<p>{escape(FRONT_NEWSLETTER_DEK)}</p></div>'
        '<div class="front-weekly-form">'
        f'<papyrus-newsletter lists="{escape(list_ids, quote=True)}" '
        f'data-lists="{escape(json.dumps(lists), quote=True)}" '
        f'consent="{escape(NEWSLETTER_CONSENT, quote=True)}" form-id="{FRONT_NEWSLETTER_FORM_ID}" '
        'button="Subscribe" label="Email address"></papyrus-newsletter>'
        f'<script src="{NEWSLETTER_SCRIPT_PATH}" defer></script></div></section>'
    )


FRONT_TABLE_NEW_WINDOW_DAYS = 7
FRONT_TABLE_UNSTATED_ROW_LABEL = "Not stated"


def _front_table_reference_date(attributes):
    stamp = _text(attributes.get("today"))
    return date.fromisoformat(stamp) if stamp else date.today()


def _front_table_is_new(model, reference_date):
    try:
        released = date.fromisoformat(str(model["sort_date"])[:10])
    except ValueError:
        return False
    return 0 <= (reference_date - released).days < FRONT_TABLE_NEW_WINDOW_DAYS


def _front_table_symbol_html(model, is_new, group_label):
    label = f"{model['name']}, symbol {model['symbol']}, {group_label}" + (", new this week" if is_new else "")
    new_class = " front-table-symbol-new" if is_new else ""
    return (
        f'<a class="front-table-symbol{new_class}" href="{escape(model["url"], quote=True)}" '
        f'title="{escape(label, quote=True)}" aria-label="{escape(label, quote=True)}">{escape(model["symbol"])}</a>'
    )


def _front_table_cell_html(models, new_flags, group_label, colspan=1):
    ordered = sorted(models, key=lambda model: (model["sort_date"], model["name"]), reverse=True)
    symbols = "".join(_front_table_symbol_html(model, new_flags[model["slug"]], group_label) for model in ordered)
    span = f' colspan="{colspan}"' if colspan > 1 else ""
    return f'<td class="front-table-cell"{span}>{symbols}</td>'


def _front_table_markup(models, reference_date):
    table = _map_view()["table"]
    groups = table["groups"]
    new_flags = {model["slug"]: _front_table_is_new(model, reference_date) for model in models}
    on_table = [model for model in models if not model["hosted"]]
    hosted = [model for model in models if model["hosted"]]
    head_cells = "".join(f'<th scope="col" class="front-table-group">{escape(group["short"])}</th>' for group in groups)
    body_rows = []
    for band in table["bands"] + [table["unstatedBand"]]:
        label = FRONT_TABLE_UNSTATED_ROW_LABEL if band["key"] == table["unstatedBand"]["key"] else band["label"]
        cells = "".join(
            _front_table_cell_html([m for m in on_table if m["group"] == group["key"] and _map_band_key(m) == band["key"]], new_flags, group["label"])
            for group in groups
        )
        body_rows.append(f'<tr><th scope="row" class="front-table-band">{escape(label)}</th>{cells}</tr>')
    hosted_label = table["hostedRow"]["label"]
    hosted_cell = _front_table_cell_html(hosted, new_flags, hosted_label, colspan=len(groups))
    body_rows.append(f'<tr><th scope="row" class="front-table-band">{escape(hosted_label)}</th>{hosted_cell}</tr>')
    new_count = sum(new_flags.values())
    return (
        f'<p class="front-table-count"><b>{len(models)}</b> {"model" if len(models) == 1 else "models"} on the table &middot; <b>{new_count}</b> new this week</p>'
        '<table class="front-table"><caption class="front-table-caption">Models we track: columns are task groups, rows are total parameter bands. '
        'Models released in the last 7 days have a heavy border and a dot.</caption>'
        f'<thead><tr><td></td>{head_cells}</tr></thead><tbody>{"".join(body_rows)}</tbody></table>'
        '<ul class="front-table-legend"><li><span class="front-table-symbol front-table-symbol-new front-table-key" aria-hidden="true">Ab</span>'
        'Heavy border and dot: new this week</li>'
        '<li><span class="front-table-symbol front-table-key" aria-hidden="true">Ab</span>Released earlier</li></ul>'
    )


def _front_table_html(page, attributes):
    models = _map_table_models(page, {group["key"] for group in _map_view()["table"]["groups"]})
    body = (
        _front_table_markup(models, _front_table_reference_date(attributes))
        if models else f'<p class="front-side-note">{escape(_map_view()["table"]["emptyTable"])}</p>'
    )
    return (
        '<section class="front-table-entry" aria-labelledby="front-table-h">'
        '<div class="front-side-heading"><h2 id="front-table-h">The table this week</h2><a class="front-link" href="/map/">Open the map &rarr;</a></div>'
        f'{body}</section>'
    )


def _front_block(page, attributes):
    part = attributes.get("part")
    if part == "signals":
        return _front_signal_count_html(page)
    if part == "newsletter":
        return _front_newsletter_html()
    if part == "table":
        return _front_table_html(page, attributes)
    if part == "underrated":
        return _front_underrated_html(page)
    raise ValueError(f"unknown front part {part!r}")


WEEKLY_ARCHIVE_STRAP = "New arrivals in machine learning."
WEEKLY_SAMPLE_ISSUE_PATH = "/sample/roundup/"
WEEKLY_SAMPLE_ISSUE_LABEL = "See what an issue will look like (placeholder)"


def _weekly_archive_intro_html():
    return (
        f'<p class="weekly-archive-strap">{escape(WEEKLY_ARCHIVE_STRAP)}</p>'
        f'<p class="weekly-archive-sample"><a href="{WEEKLY_SAMPLE_ISSUE_PATH}">{escape(WEEKLY_SAMPLE_ISSUE_LABEL)}</a></p>'
    )


def _reader_settings_script():
    vote_subjects = json.dumps(_scoring()["voteSubjects"])
    return f'<script>window.papyrusReader = Object.assign(window.papyrusReader || {{}}, {{ voteSubjects: {vote_subjects} }});</script>\n'


SPONSORSHIP_PATH = Path(__file__).with_name("sponsorship.json")
SPONSORSHIP_STYLESHEET_PATH = "/assets/shipped-sponsorship.css"
SPONSORSHIP_SCRIPT_PATH = "/assets/shipped-sponsorship.js"
SPONSORSHIP_GENERIC_KEY = "generic"
SPONSORSHIP_NO_TOPIC = "none"
SPONSORSHIP_TOPIC_MATCH = "topic"
SPONSORSHIP_FALLBACK_MATCH = "fallback"
SPONSORSHIP_SOURCE_WEIGHTS = {"topic": 4, "name": 3, "cluster": 2, "title": 1}
SPONSORSHIP_UTM_SOURCE = "shipped"
SPONSORSHIP_UTM_MEDIUM = "sponsored"
SPONSORSHIP_LINK_REL = "sponsored noopener"
SPONSORSHIP_DIAMOND_SVG = '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M5 0.5L9.5 5L5 9.5L0.5 5z" fill="currentColor"></path></svg>'
SPONSORSHIP_ROW_RULES = {"front": (10, 2), "new": (10, 3), "list": (10, 3), "concept": (5, 1)}
SPONSORSHIP_ROW_EARLIEST_AFTER_POSITION = 3
SPONSORSHIP_ROW_NEIGHBOUR_COUNT = 3
SPONSORSHIP_FRONT_PROFILE_SIGNALS = 10
SPONSORSHIP_STORY_NOTE_AFTER_PARAGRAPH = 2
SPONSORSHIP_WEEKLY_BANNER_AFTER_PART = 3
SPONSORSHIP_PAGE_TYPES_BY_PATH = {
    "/": "front",
    "/new/": "new",
    "/map/": "map",
    "/proposals/": "proposals",
    "/submit/": "submit",
    "/sign-in/": "sign-in",
}
SPONSORSHIP_ELEMENT_TAG = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b[^>]*?(/?)>")
SPONSORSHIP_ROW_ITEM = re.compile(r'<li class="(?:board|signal)-row">.*?</li>', re.DOTALL)
SPONSORSHIP_ROW_HREF = re.compile(r'class="(?:board|signal)-title" href="([^"]+)"')
SPONSORSHIP_PARAGRAPH_END = "</p>"


@lru_cache(maxsize=1)
def _sponsorship():
    return json.loads(SPONSORSHIP_PATH.read_text(encoding="utf-8"))


def _sponsorship_enabled():
    return _sponsorship().get("enabled") is True


def _sponsorship_slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _sponsorship_words(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


@lru_cache(maxsize=1)
def _sponsorship_rules():
    rules = {}
    for key, solution in _sponsorship()["solutions"].items():
        if key == SPONSORSHIP_GENERIC_KEY:
            continue
        match = solution.get("match") or {}
        keywords = [
            (_sponsorship_slug(keyword), re.compile(r"(?<![a-z0-9])" + re.escape(_sponsorship_words(keyword)) + r"(?:s|es)?(?![a-z0-9])"))
            for keyword in match.get("keywords") or []
        ]
        rules[key] = ({_sponsorship_slug(topic) for topic in match.get("topics") or []}, keywords)
    return rules


def _sponsorship_term_hit(rule, kind, text):
    topics, keywords = rule
    if kind == "topic" and _sponsorship_slug(text) in topics:
        return _sponsorship_slug(text)
    words = _sponsorship_words(text)
    return next((term for term, pattern in keywords if pattern.search(words)), None)


def _sponsorship_candidates(profile):
    """The solutions that fit a page profile, best first, then the generic Anthus unit as the fallback."""
    ranked = []
    for order, (key, rule) in enumerate(_sponsorship_rules().items()):
        score, best_term, best_weight = 0, None, 0
        for kind, text in profile:
            term = _sponsorship_term_hit(rule, kind, text)
            if term is None:
                continue
            weight = SPONSORSHIP_SOURCE_WEIGHTS[kind]
            score += weight
            if weight > best_weight:
                best_term, best_weight = term, weight
        if score:
            ranked.append((-score, order, key, best_term))
    ranked.sort()
    candidates = [{"key": key, "topic": term, "match": SPONSORSHIP_TOPIC_MATCH} for _score, _order, key, term in ranked]
    candidates.append({"key": SPONSORSHIP_GENERIC_KEY, "topic": SPONSORSHIP_NO_TOPIC, "match": SPONSORSHIP_FALLBACK_MATCH})
    return candidates


def _sponsorship_claim(candidates, taken):
    """The best candidate no unit on the page uses yet, or None when the page has run out of solutions."""
    for candidate in candidates:
        if candidate["key"] not in taken:
            taken.add(candidate["key"])
            return candidate
    return None


def _sponsorship_url(url, campaign, unit, page_type, topic):
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True) + [
        ("utm_source", SPONSORSHIP_UTM_SOURCE),
        ("utm_medium", SPONSORSHIP_UTM_MEDIUM),
        ("utm_campaign", campaign),
        ("utm_content", f"{unit}-{page_type}"),
        ("utm_term", topic or SPONSORSHIP_NO_TOPIC),
    ]
    return urlunsplit(parts._replace(path=parts.path or "/", query=urlencode(query)))


def _sponsorship_link_html(context, url, label, css_class, action):
    href = _sponsorship_url(url, context["campaign"], context["unit"], context["page_type"], context["topic"])
    return (
        f'<a class="{css_class}" href="{escape(href, quote=True)}" rel="{SPONSORSHIP_LINK_REL}" '
        f'data-sponsor-action="{action}">{escape(label)}</a>'
    )


def _sponsorship_attributes_html(context, name, slot):
    values = (
        ("unit", context["unit"]),
        ("id", context["campaign"]),
        ("name", name),
        ("slot", slot),
        ("page-type", context["page_type"]),
        ("topic", context["topic"] or SPONSORSHIP_NO_TOPIC),
        ("match", context["match"]),
    )
    return " ".join(f'data-sponsor-{field}="{escape(value, quote=True)}"' for field, value in values)


def _sponsorship_pill_html(extra_class=""):
    return f'<span class="sp-pill{extra_class}">{SPONSORSHIP_DIAMOND_SVG}{escape(_sponsorship()["eyebrow"])}</span>'


def _sponsorship_monogram_html(solution, size):
    return f'<span class="sp-mono sp-mono-{size}" aria-hidden="true">{escape(solution["mark"])}</span>'


def _sponsorship_disclosure_html(form):
    disclosure = _sponsorship()["disclosure"]
    return (
        f'<p class="sp-disc sp-disc-{form}">{escape(disclosure[form])} '
        f'<a href="{escape(disclosure["path"], quote=True)}">{escape(disclosure[form + "LinkLabel"])}</a></p>'
    )


def _sponsorship_context(unit, page_type, candidate):
    return {
        "unit": unit,
        "page_type": page_type,
        "campaign": candidate["key"],
        "topic": candidate["topic"],
        "match": candidate["match"],
    }


def _sponsorship_bar_html(page_type):
    bar = _sponsorship()["bar"]
    candidate = {"key": bar["id"], "topic": SPONSORSHIP_NO_TOPIC, "match": SPONSORSHIP_FALLBACK_MATCH}
    context = _sponsorship_context("bar", page_type, candidate)
    action = _sponsorship_link_html(context, bar["actionUrl"], f'{bar["actionLabel"]} →', "sp-bar-action", "primary")
    return (
        f'<aside class="sp-bar" aria-label="Sponsored: {escape(bar["name"], quote=True)}" {_sponsorship_attributes_html(context, bar["name"], "top")}>'
        f'{_sponsorship_pill_html()}'
        f'<span class="sp-bar-presenter"><span class="sp-bar-full">{escape(bar["presenter"])}</span>'
        f'<span class="sp-bar-short">{escape(bar["presenterShort"])}</span></span>'
        f'<span class="sp-bar-line">{escape(bar["line"])}</span>{action}</aside>'
    )


def _sponsorship_banner_html(candidate, page_type, slot):
    solution = _sponsorship()["solutions"][candidate["key"]]
    labels = _sponsorship()["labels"]
    context = _sponsorship_context("banner", page_type, candidate)
    return (
        f'<aside class="sp-card sp-banner" aria-label="Sponsored: {escape(solution["name"], quote=True)}" {_sponsorship_attributes_html(context, solution["name"], slot)}>'
        f'{_sponsorship_monogram_html(solution, "xl")}'
        '<div class="sp-banner-copy">'
        f'<span class="sp-banner-eyebrow">{_sponsorship_pill_html()}<span class="sp-by">{escape(labels["byFull"])}</span></span>'
        f'<span class="sp-banner-pitch"><b class="sp-name">{escape(solution["name"])}</b> &middot; <span>{escape(solution["pitch"])}</span></span>'
        f'<span class="sp-banner-description">{escape(solution["description"])}</span></div>'
        '<div class="sp-banner-actions">'
        f'{_sponsorship_link_html(context, solution["primary"]["url"], solution["primary"]["label"], "sp-btn", "primary")}'
        f'{_sponsorship_link_html(context, solution["secondary"]["url"], solution["secondary"]["label"], "sp-btn sp-btn2", "secondary")}</div>'
        f'<div class="sp-banner-disclosure">{_sponsorship_disclosure_html("long")}{_sponsorship_disclosure_html("short")}</div></aside>'
    )


def _sponsorship_card_html(candidate, page_type, slot):
    solution = _sponsorship()["solutions"][candidate["key"]]
    context = _sponsorship_context("card", page_type, candidate)
    return (
        f'<aside class="sp-card sp-sidebar-card" aria-label="Sponsored: {escape(solution["name"], quote=True)}" {_sponsorship_attributes_html(context, solution["name"], slot)}>'
        f'<span class="sp-card-top">{_sponsorship_pill_html()}{_sponsorship_monogram_html(solution, "md")}</span>'
        f'<b class="sp-name sp-card-name">{escape(solution["name"])}</b>'
        f'<span class="sp-card-pitch">{escape(solution["cardPitch"])}</span>'
        f'{_sponsorship_link_html(context, solution["primary"]["url"], solution["primary"]["label"], "sp-btn", "primary")}'
        f'{_sponsorship_disclosure_html("short")}</aside>'
    )


def _sponsorship_note_html(candidate, page_type, slot):
    solution = _sponsorship()["solutions"][candidate["key"]]
    labels = _sponsorship()["labels"]
    disclosure = _sponsorship()["disclosure"]
    context = _sponsorship_context("note", page_type, candidate)
    note_link = _sponsorship_link_html(context, solution["primary"]["url"], f'{solution["note"]} {labels["noteAction"]}', "sp-note-link", "primary")
    return (
        f'<aside class="sp-card sp-note" aria-label="Sponsored: {escape(solution["name"], quote=True)}" {_sponsorship_attributes_html(context, solution["name"], slot)}>'
        f'{_sponsorship_monogram_html(solution, "sm")}'
        '<span class="sp-note-body"><span class="sp-note-meta">'
        f'{_sponsorship_pill_html(" sp-pill-small")}<span class="sp-disc">{escape(labels["noteInline"])}</span>'
        f'<a class="sp-note-policy" href="{escape(disclosure["path"], quote=True)}">{escape(disclosure["shortLinkLabel"])}</a></span>'
        f'{note_link}</span></aside>'
    )


def _sponsorship_row_html(candidate, page_type, slot):
    solution = _sponsorship()["solutions"][candidate["key"]]
    labels = _sponsorship()["labels"]
    context = _sponsorship_context("row", page_type, candidate)
    return (
        '<li class="sp-item">'
        f'<aside class="sp-card sp-row" aria-label="Sponsored: {escape(solution["name"], quote=True)}" {_sponsorship_attributes_html(context, solution["name"], slot)}>'
        f'{_sponsorship_monogram_html(solution, "md")}'
        f'<span class="sp-row-copy"><span class="sp-row-meta">{_sponsorship_pill_html()}<span class="sp-row-source">{escape(labels["rowSource"])}</span></span>'
        f'<span class="sp-row-pitch"><b class="sp-name">{escape(solution["name"])}</b> &middot; {escape(solution["rowPitch"])}</span></span>'
        f'{_sponsorship_link_html(context, solution["primary"]["url"], solution["rowAction"], "sp-btn sp-btn-small", "primary")}'
        f'{_sponsorship_disclosure_html("short")}</aside></li>'
    )


def _sponsorship_element_end(html, start):
    """The index just past the element that opens at `start`, counting nested elements of the same tag."""
    opening = SPONSORSHIP_ELEMENT_TAG.match(html, start)
    if opening is None:
        return None
    name = opening.group(2).lower()
    depth = 0
    for match in SPONSORSHIP_ELEMENT_TAG.finditer(html, start):
        if match.group(2).lower() != name or match.group(3):
            continue
        depth += -1 if match.group(1) else 1
        if depth == 0:
            return match.end()
    return None


def _sponsorship_span(html, opening_pattern, search_from=0):
    """The (start, end) of the first element whose opening tag matches the pattern, or None."""
    opening = re.compile(opening_pattern).search(html, search_from)
    if opening is None:
        return None
    end = _sponsorship_element_end(html, opening.start())
    return (opening.start(), end) if end is not None else None


def _sponsorship_insert_after(html, opening_pattern, fragment_for):
    span = _sponsorship_span(html, opening_pattern)
    if span is None:
        return html
    fragment = fragment_for()
    return html if fragment is None else html[: span[1]] + fragment + html[span[1] :]


def _sponsorship_append_inside(html, opening_pattern, fragment_for, require_section=False):
    span = _sponsorship_span(html, opening_pattern)
    if span is None:
        return html
    closing = html.rfind("</", span[0], span[1])
    if require_section and "<section" not in html[span[0] : closing]:
        return html
    fragment = fragment_for()
    return html if fragment is None else html[:closing] + fragment + html[closing:]


def _sponsorship_wrap(html, opening_pattern, wrapper_class, fragment_for):
    span = _sponsorship_span(html, opening_pattern)
    if span is None:
        return html
    fragment = fragment_for()
    if fragment is None:
        return html
    return html[: span[0]] + f'<div class="{wrapper_class}">' + html[span[0] : span[1]] + fragment + "</div>" + html[span[1] :]


def _sponsorship_unit(builder, candidates, taken, page_type, slot):
    """A closure that claims the next free solution and renders one unit, or returns None when none is left."""

    def build():
        candidate = _sponsorship_claim(candidates, taken)
        return builder(candidate, page_type, slot) if candidate is not None else None

    return build


def _sponsorship_entry_summaries(page):
    def build():
        return {entry.url: entry.summary for entry in page.entries if entry.url}

    return page.site.memo("shipped-sponsorship-summaries", build) if page.site is not None else build()


def _sponsorship_item_profile(summary, page):
    item = _read_item(summary)
    profile = [("topic", tag) for tag in item["tags"]]
    if summary.section:
        profile.append(("topic", summary.section))
    profile += [("name", entity["name"]) for entity in item["entities"]]
    profile += [("cluster", str(cluster.get("name"))) for tag in item["tags"][:1] for cluster in _beat_clusters(page, tag) if cluster.get("name")]
    profile.append(("title", _signal_title(summary)))
    return profile


def _sponsorship_story_profile(summary):
    story = _read_story(summary)
    profile = [("topic", story["section"])] if story["section"] else []
    profile += [("name", concept["name"]) for concept in story["concepts"]]
    profile += [("title", text) for text in (story["title"], story["standfirst"]) if text]
    return profile


def _sponsorship_concept_profile(page):
    key = page.path.strip("/").rsplit("/", 1)[-1]
    profile = [("topic", key), ("title", page.title)]
    profile += [("cluster", str(cluster.get("name"))) for cluster in _beat_clusters(page, key) if cluster.get("name")]
    return profile


def _sponsorship_front_profile(page):
    profile = []
    for summary, _entry, _label in _board_pairs(page, lambda candidate: True)[:SPONSORSHIP_FRONT_PROFILE_SIGNALS]:
        profile += _sponsorship_item_profile(summary, page)
    return profile


def _sponsorship_map_profile(page):
    return [("topic", "map")] + [("cluster", str(cluster.get("name"))) for cluster in _knowledge_clusters(page) if cluster.get("name")]


def _sponsorship_row_positions(row_count, page_type):
    interval, maximum = SPONSORSHIP_ROW_RULES[page_type]
    positions = range(interval, row_count + 1, interval)
    return [position for position in positions if position >= SPONSORSHIP_ROW_EARLIEST_AFTER_POSITION][:maximum]


def _sponsorship_rows(html, page, page_type, taken, list_pattern, search_from=0):
    """Feed rows after every tenth signal of the first signal list at or after `search_from`, matched to the signals around them."""
    span = _sponsorship_span(html, list_pattern, search_from)
    if span is None:
        return html
    list_html = html[span[0] : span[1]]
    rows = list(SPONSORSHIP_ROW_ITEM.finditer(list_html))
    summaries = _sponsorship_entry_summaries(page)
    placed = []
    for position in _sponsorship_row_positions(len(rows), page_type):
        neighbours = rows[max(0, position - SPONSORSHIP_ROW_NEIGHBOUR_COUNT) : position]
        profile = []
        for row in neighbours:
            href = SPONSORSHIP_ROW_HREF.search(row.group(0))
            summary = summaries.get(unescape(href.group(1))) if href else None
            if summary is not None:
                profile += _sponsorship_item_profile(summary, page)
        candidate = _sponsorship_claim(_sponsorship_candidates(profile), taken)
        if candidate is not None:
            placed.append((rows[position - 1].end(), _sponsorship_row_html(candidate, page_type, f"after-signal-{position}")))
    for insert_at, row_html in reversed(placed):
        list_html = list_html[:insert_at] + row_html + list_html[insert_at:]
    return html[: span[0]] + list_html + html[span[1] :]


def _sponsorship_signal_units(html, page, page_type):
    candidates = _sponsorship_candidates(_sponsorship_item_profile(page.entry.summary, page))
    taken = set()
    html = _sponsorship_insert_after(
        html, r'<section class="signal-section" aria-labelledby="signal-map-h">',
        _sponsorship_unit(_sponsorship_note_html, candidates, taken, page_type, "after-on-the-map"),
    )
    html = _sponsorship_append_inside(
        html, r'<div class="signal-main">', _sponsorship_unit(_sponsorship_banner_html, candidates, taken, page_type, "before-nearby")
    )
    return _sponsorship_append_inside(
        html, r'<aside class="signal-rail"', _sponsorship_unit(_sponsorship_card_html, candidates, taken, page_type, "rail-last"), require_section=True
    )


def _sponsorship_story_note(html, candidates, taken, page_type):
    span = _sponsorship_span(html, r'<div class="story-body">')
    if span is None:
        return html
    body = html[span[0] : span[1]]
    ends = [match.end() for match in re.finditer(re.escape(SPONSORSHIP_PARAGRAPH_END), body)]
    if len(ends) <= SPONSORSHIP_STORY_NOTE_AFTER_PARAGRAPH:
        return html
    note = _sponsorship_unit(_sponsorship_note_html, candidates, taken, page_type, f"after-paragraph-{SPONSORSHIP_STORY_NOTE_AFTER_PARAGRAPH}")()
    if note is None:
        return html
    cut = span[0] + ends[SPONSORSHIP_STORY_NOTE_AFTER_PARAGRAPH - 1]
    return html[:cut] + note + html[cut:]


def _sponsorship_story_units(html, page, page_type):
    candidates = _sponsorship_candidates(_sponsorship_story_profile(page.entry.summary))
    taken = set()
    html = _sponsorship_story_note(html, candidates, taken, page_type)
    html = _sponsorship_insert_after(
        html, r'<div class="story-body">', _sponsorship_unit(_sponsorship_banner_html, candidates, taken, page_type, "after-body")
    )
    return _sponsorship_append_inside(
        html, r'<article class="story-article"', _sponsorship_unit(_sponsorship_card_html, candidates, taken, page_type, "after-sources")
    )


def _sponsorship_concept_units(html, page, page_type):
    candidates = _sponsorship_candidates(_sponsorship_concept_profile(page))
    taken = set()
    html = _sponsorship_insert_after(
        html, r'<div class="concept-row">', _sponsorship_unit(_sponsorship_banner_html, candidates, taken, page_type, "between-sections")
    )
    rows = list(re.finditer(r'<div class="concept-row">', html))
    if not rows:
        return html
    last_row = rows[-1].start()
    html = _sponsorship_concept_card(html, last_row, _sponsorship_unit(_sponsorship_card_html, candidates, taken, page_type, "rail-last"))
    return _sponsorship_rows(html, page, page_type, taken, r'<ol class="signal-list">', last_row)


def _sponsorship_concept_card(html, row_start, card_for):
    row_end = _sponsorship_element_end(html, row_start)
    if row_end is None:
        return html
    row_html = html[row_start:row_end]
    stories = _sponsorship_span(row_html, r'<section class="concept-column-narrow concept-stories"')
    if stories is not None:
        card = card_for()
        if card is None:
            return html
        rail = (
            '<div class="concept-column-narrow sp-rail">'
            + row_html[stories[0] : stories[1]].replace("concept-column-narrow concept-stories", "concept-stories", 1)
            + card
            + "</div>"
        )
        return html[:row_start] + row_html[: stories[0]] + rail + row_html[stories[1] :] + html[row_end:]
    card = card_for()
    if card is None:
        return html
    closing = row_end - len("</div>")
    return html[:closing] + f'<div class="concept-column-narrow sp-rail">{card}</div>' + html[closing:]


def _sponsorship_front_units(html, page, page_type):
    candidates = _sponsorship_candidates(_sponsorship_front_profile(page))
    taken = set()
    html = _sponsorship_wrap(
        html, r'<section class="rail front-rising"', "front-rising-rail",
        _sponsorship_unit(_sponsorship_card_html, candidates, taken, page_type, "rail-last"),
    )
    latest = html.find('<div class="front-latest">')
    return _sponsorship_rows(html, page, page_type, taken, r'<ol class="board-list">', max(latest, 0))


def _sponsorship_map_units(html, page, page_type):
    candidates = _sponsorship_candidates(_sponsorship_map_profile(page))
    return _sponsorship_wrap(
        html, r'<aside class="map-new"', "map-new-rail",
        _sponsorship_unit(_sponsorship_card_html, candidates, set(), page_type, "below-new-on-the-map"),
    )


def _sponsorship_weekly_units(html, page, page_type):
    candidates = _sponsorship_candidates([("topic", "weekly")])
    parts = list(re.finditer(r'<section class="weekly-part[^"]*"', html))
    if len(parts) < SPONSORSHIP_WEEKLY_BANNER_AFTER_PART:
        return html
    part = parts[SPONSORSHIP_WEEKLY_BANNER_AFTER_PART - 1]
    end = _sponsorship_element_end(html, part.start())
    banner = _sponsorship_unit(
        _sponsorship_banner_html, candidates, set(), page_type, f"after-part-{SPONSORSHIP_WEEKLY_BANNER_AFTER_PART}"
    )()
    return html if end is None or banner is None else html[:end] + banner + html[end:]


def _sponsorship_list_units(html, page, page_type):
    return _sponsorship_rows(html, page, page_type, set(), r'<ol class="signal-list">', max(html.find('<section class="landing-signals"'), 0))


def _sponsorship_new_units(html, page, page_type):
    return _sponsorship_rows(html, page, page_type, set(), r'<ol class="board-list">')


SPONSORSHIP_PAGE_HANDLERS = {
    "signal": _sponsorship_signal_units,
    "story": _sponsorship_story_units,
    "concept": _sponsorship_concept_units,
    "front": _sponsorship_front_units,
    "map": _sponsorship_map_units,
    "weekly": _sponsorship_weekly_units,
    "list": _sponsorship_list_units,
    "new": _sponsorship_new_units,
}


def _sponsorship_page_type(html, page):
    if page.kind == "item" and page.entry is not None:
        summary = page.entry.summary
        if summary.type == PAGE_ITEM_TYPE:
            return "policies" if page.path.startswith("/policies/") else "other"
        if summary.type == WIKI_ITEM_TYPE:
            return "other"
        if _is_story(summary):
            return "story"
        return "weekly" if summary.section == ROUNDUP_SECTION else "signal"
    if page.kind == "listing":
        return "list" if 'class="shipped-page section-landing"' in html else "other"
    if page.kind == "custom":
        if page.path in SPONSORSHIP_PAGE_TYPES_BY_PATH:
            return SPONSORSHIP_PAGE_TYPES_BY_PATH[page.path]
        if "concept-page" in html:
            return "concept"
        if "weekly-issue" in html:
            return "weekly"
    return "other"


def _sponsorship_finish(html, page):
    if not _sponsorship_enabled():
        return html
    page_type = _sponsorship_page_type(html, page)
    handler = SPONSORSHIP_PAGE_HANDLERS.get(page_type)
    if handler is not None:
        html = handler(html, page, page_type)
    masthead = html.find('<header class="markus-site-masthead"')
    if masthead < 0:
        LOGGER.warning("page has no masthead; sponsor bar left out")
        return html
    return html[:masthead] + _sponsorship_bar_html(page_type) + html[masthead:]


def _sponsorship_head_html():
    return (
        f'\n<link rel="stylesheet" href="{SPONSORSHIP_STYLESHEET_PATH}">\n'
        f'<script src="{SPONSORSHIP_SCRIPT_PATH}" defer></script>'
    )


def _footer_links():
    if not _sponsorship_enabled():
        return FOOTER_LINKS
    footer = _sponsorship()["footer"]
    links = list(FOOTER_LINKS)
    position = next((index for index, (_label, href) in enumerate(links) if href == "/policies/"), len(links) - 1) + 1
    links.insert(position, ("Sponsorship", footer["linkPath"]))
    return tuple(links)


def _footer_text_html():
    if not _sponsorship_enabled():
        return escape(FOOTER_LINE)
    footer = _sponsorship()["footer"]
    return f'{escape(footer["line"])} <a href="{escape(footer["linkPath"], quote=True)}">{escape(footer["linkLabel"])}</a>'


def head_extra(page):
    return (
        f'<link rel="stylesheet" href="{READER_STYLESHEET_PATH}">\n'
        + _reader_settings_script()
        + f'<script src="{READER_SCRIPT_PATH}" defer></script>\n'
        f'<script src="{PROPOSALS_SCRIPT_PATH}" defer></script>'
        + (_sponsorship_head_html() if _sponsorship_enabled() else "")
    )


def _reader_sign_in(html):
    """Put the ReaderSignIn island where the static Sign in link is; the link stays inside it for readers without JavaScript."""
    header_end = html.find("</header>")
    if header_end < 0:
        LOGGER.warning("page has no header; reader sign-in left out")
        return html
    header, rest = html[:header_end], html[header_end:]
    mounted, count = SIGN_IN_LINK.subn(
        lambda link: _island("ReaderSignIn", tag="span", css_class="nav-reader", fallback=link.group(0)), header, count=1
    )
    if not count:
        LOGGER.warning("header has no Sign in link; reader sign-in left out")
    return mounted + rest


LOGOTYPE_BARCODE_PREFIX = "SHP"
LOGOTYPE_BARCODE_PLACEHOLDER = '<span class="brand-barcode" data-brand-barcode></span>'
LOGOTYPE_BARCODE_SCRIPT = '<script src="/assets/shipped-barcode.js" defer></script>'
LOGOTYPE_TAGLINE_PARAGRAPH = re.compile(r'<p class="markus-site-tagline">(.*?)</p>', re.DOTALL)
CODE128_START_B = 104
CODE128_STOP = 106
CODE128_TERMINATION_BAR = "11"
CODE128_PATTERNS = (
    "11011001100 11001101100 11001100110 10010011000 "
    "10010001100 10001001100 10011001000 10011000100 "
    "10001100100 11001001000 11001000100 11000100100 "
    "10110011100 10011011100 10011001110 10111001100 "
    "10011101100 10011100110 11001110010 11001011100 "
    "11001001110 11011100100 11001110100 11101101110 "
    "11101001100 11100101100 11100100110 11101100100 "
    "11100110100 11100110010 11011011000 11011000110 "
    "11000110110 10100011000 10001011000 10001000110 "
    "10110001000 10001101000 10001100010 11010001000 "
    "11000101000 11000100010 10110111000 10110001110 "
    "10001101110 10111011000 10111000110 10001110110 "
    "11101110110 11010001110 11000101110 11011101000 "
    "11011100010 11011101110 11101011000 11101000110 "
    "11100010110 11101101000 11101100010 11100011010 "
    "11101111010 11001000010 11110001010 10100110000 "
    "10100001100 10010110000 10010000110 10000101100 "
    "10000100110 10110010000 10110000100 10011010000 "
    "10011000010 10000110100 10000110010 11000010010 "
    "11001010000 11110111010 11000010100 10001111010 "
    "10100111100 10010111100 10010011110 10111100100 "
    "10011110100 10011110010 11110100100 11110010100 "
    "11110010010 11011011110 11011110110 11110110110 "
    "10101111000 10100011110 10001011110 10111101000 "
    "10111100010 11110101000 11110100010 10111011110 "
    "10111101110 11101011110 11110101110 11010000100 "
   "11010010000 11010011100 11000111010"
).split()
BARCODE_HEIGHT_UNITS = 46
BARCODE_INSET_UNITS = 10
BARCODE_INSET_FIRST_MODULE = 55
BARCODE_INSET_END_MODULE = 134


def _code128_set_b_modules(text):
    values = []
    for character in text:
        value = ord(character) - 32
        if not 0 <= value <= 94:
            raise ValueError(f"{character!r} is not in Code 128 code set B")
        values.append(value)
    checksum = (CODE128_START_B + sum(position * value for position, value in enumerate(values, start=1))) % 103
    symbols = [CODE128_START_B, *values, checksum, CODE128_STOP]
    return "".join(CODE128_PATTERNS[symbol] for symbol in symbols) + CODE128_TERMINATION_BAR


def _logotype_barcode_text(day):
    return f"{LOGOTYPE_BARCODE_PREFIX} {day.isoformat()}"


def _barcode_bar_crosses_inset(position, width):
    return position < BARCODE_INSET_END_MODULE and position + width > BARCODE_INSET_FIRST_MODULE


def _barcode_bar_rects(position, width):
    if not _barcode_bar_crosses_inset(position, width):
        return [f'<rect x="{position}" y="0" width="{width}" height="{BARCODE_HEIGHT_UNITS}"/>']
    above_inset = BARCODE_HEIGHT_UNITS - BARCODE_INSET_UNITS
    return [
        f'<rect x="{position}" y="0" width="{width}" height="{above_inset}"/>',
        f'<rect class="brand-barcode-inset" x="{position}" y="{above_inset}" width="{width}" height="{BARCODE_INSET_UNITS}"/>',
    ]


def _barcode_svg(modules, label):
    bars = []
    position = 0
    while position < len(modules):
        if modules[position] != "1":
            position += 1
            continue
        end = position
        while end < len(modules) and modules[end] == "1":
            end += 1
        bars.extend(_barcode_bar_rects(position, end - position))
        position = end
    return (
        f'<svg class="brand-barcode-bars" viewBox="0 0 {len(modules)} {BARCODE_HEIGHT_UNITS}" preserveAspectRatio="none" '
        f'role="img" aria-label="{escape(label, quote=True)}" fill="currentColor" shape-rendering="crispEdges">'
        f'{"".join(bars)}</svg>'
    )


def _logotype_barcode_html(day):
    text = _logotype_barcode_text(day)
    label = f"Barcode for {text}, today's date"
    return (
        '<span class="brand-barcode" data-brand-barcode>'
        f'{_barcode_svg(_code128_set_b_modules(text), label)}'
        f'<span class="brand-barcode-text" data-brand-barcode-text aria-hidden="true">{escape(text)}</span></span>'
    )


def _mast_logotype(html, day):
    header_end = html.find("</header>")
    if header_end < 0:
        return html
    header, rest = html[:header_end], html[header_end:]
    header = header.replace(LOGOTYPE_BARCODE_PLACEHOLDER, _logotype_barcode_html(day), 1)
    header = LOGOTYPE_TAGLINE_PARAGRAPH.sub(
        lambda tagline: (
            '<div class="markus-site-tagwrap">'
            f'<p class="markus-site-tagline">{tagline.group(1)}</p></div>'
        ),
        header,
        count=1,
    )
    return header + LOGOTYPE_BARCODE_SCRIPT + rest


def page_finish(html, page):
    html = _reader_sign_in(html)
    html = _mast_logotype(html, date.today())
    html = _sponsorship_finish(html, page)
    if page.kind != "listing" or page.path != ROUNDUP_ARCHIVE_PATH:
        return html
    heading_end = html.find("</h1>")
    if heading_end < 0:
        LOGGER.warning("roundup archive has no heading; newsletter signup left out")
        return html
    insert_at = heading_end + len("</h1>")
    return html[:insert_at] + _weekly_archive_intro_html() + _newsletter_signup_html() + html[insert_at:]

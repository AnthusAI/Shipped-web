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
from html import escape
from pathlib import Path
from urllib.parse import urlparse

LOGGER = logging.getLogger("shipped.hooks")

SCORING_PATH = Path(__file__).with_name("scoring.json")
NEWSLETTER_LISTS_PATH = Path(__file__).with_name("newsletter-lists.json")

ROUNDUP_ARCHIVE_PATH = "/roundup/"
ROUNDUP_SECTION = "roundup"
WIKI_ITEM_TYPE = "wiki_page"
READER_SCRIPT_PATH = "/_plugins/papyrus-reader@1.js"
READER_STYLESHEET_PATH = "/_plugins/papyrus-reader@1.css"
PAGE_ITEM_TYPE = "page"
VERSION_SUFFIX = re.compile(r"-v\d+$")
SIGN_IN_LINK = re.compile(r'<a href="/sign-in/"[^>]*>Sign in</a>')
NEWSLETTER_SCRIPT_PATH = "/_plugins/papyrus-newsletter@1.js"
NEWSLETTER_CONSENT = "Email me the lists I ticked. I can unsubscribe in one click."
NEWSLETTER_HEADING = "Get The Weekly by email"
NEWSLETTER_DEK = "Tick the lists you want: The Weekly, and a short alert when something is added to a section. Nothing is sent until you confirm your address from the email we send you."
NEWSLETTER_FEED_NOTE = 'Prefer a feed? <a href="/feed.xml">RSS</a> carries the latest items.'

DEPENDS_ON = {"*": [], "item": ["*"]}

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
STORIES_PLACEHOLDER_TEXT = "Stories that cite this signal will be listed here, with who approved them."
WARNINGS_ALREADY_LOGGED = set()
STAMP_NOTE_VERBS = {"available": "Confirmed by", "verified": "Verified by"}
STAMP_NOTE_UNNAMED_VERBS = {"available": "Confirmed on", "verified": "Verified on"}
FOOTER_LINKS = (
    ("How the map works", "/map/"),
    ("How steering works", "/policies/#steering"),
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
        return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%-d %b %Y")
    except (TypeError, ValueError):
        return iso_date or ""


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


def _rail_placeholder_html(heading_id, heading, text):
    return (
        f'<section class="signal-rail-block is-placeholder" aria-labelledby="{heading_id}"><span class="placeholder-tag">Placeholder</span>'
        f'<h2 id="{heading_id}">{escape(heading)}</h2><p>{escape(text)}</p></section>'
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
        _rail_placeholder_html("signal-stories-h", "Appears in these stories", STORIES_PLACEHOLDER_TEXT)
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
        if summary.section in section_labels and summary.section != ROUNDUP_SECTION and summary.type != WIKI_ITEM_TYPE and summary.item_id in entries_by_id and keep(summary)
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
LANDING_EXCLUDED_SECTIONS = {ROUNDUP_SECTION, WIKI_SECTION}
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
        '<p>AI-written stories are not switched on yet. When they are, readers steer which one leads and an editor approves it.</p>'
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
        f'<div class="landing-layout">{_landing_lead_html(section.label)}'
        f'<aside class="landing-rails">{_landing_clusters_html(page)}{_landing_concepts_html(items, page.site)}</aside></div>'
        f'{signals_html}</div>'
    )


def footer(page):
    links = "".join(f'<li><a href="{escape(href, quote=True)}">{escape(label)}</a></li>' for label, href in FOOTER_LINKS)
    return (
        '<div class="shipped-footer">'
        '<a class="shipped-footer-wordmark" href="/"><span class="brand-word">Shipped</span></a>'
        f'<nav aria-label="Footer"><ul class="shipped-footer-links">{links}</ul></nav>'
        f'<p class="markus-footer-text">{escape(FOOTER_LINE)}</p></div>'
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
MAP_COLD_START_TEXT = (
    "This is the first build, so there is nothing to replay yet. Each Friday adds a column here; "
    "after 8 weeks the river below starts to show births, merges and splits."
)
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
        if summary.type not in (WIKI_ITEM_TYPE, PAGE_ITEM_TYPE) and summary.section != ROUNDUP_SECTION and summary.item_id in entries_by_id
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
        f'{_map_now_html(clusters)}'
        f'<div class="map-cold-start"><b>No history yet</b><p>{escape(MAP_COLD_START_TEXT)}</p></div></section>'
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


def block(name, attributes, page):
    if name in MAP_BLOCK_NAMES:
        return _map_block(name, attributes, page)
    if name == "desk-board":
        return _desk_board(page, attributes)
    if name == "front":
        return _front_block(page, attributes)
    if name == "topic-board":
        return _topic_board(page, attributes)
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


def head_extra(page):
    return (
        f'<link rel="stylesheet" href="{READER_STYLESHEET_PATH}">\n'
        f'<script src="{READER_SCRIPT_PATH}" defer></script>'
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
LOGOTYPE_DESCRIPTOR = "Open weights, decision models, real products. Mapped as they land."
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
        bars.append(f'<rect x="{position}" y="0" width="{end - position}" height="{BARCODE_HEIGHT_UNITS}"/>')
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
            f'<p class="markus-site-tagline">{tagline.group(1)}</p>'
            f'<p class="markus-site-descriptor">{escape(LOGOTYPE_DESCRIPTOR)}</p></div>'
        ),
        header,
        count=1,
    )
    return header + LOGOTYPE_BARCODE_SCRIPT + rest


def page_finish(html, page):
    html = _reader_sign_in(html)
    html = _mast_logotype(html, date.today())
    if page.kind != "listing" or page.path != ROUNDUP_ARCHIVE_PATH:
        return html
    heading_end = html.find("</h1>")
    if heading_end < 0:
        LOGGER.warning("roundup archive has no heading; newsletter signup left out")
        return html
    insert_at = heading_end + len("</h1>")
    return html[:insert_at] + _weekly_archive_intro_html() + _newsletter_signup_html() + html[insert_at:]

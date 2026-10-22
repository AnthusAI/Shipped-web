"""Shipped named hooks for the standard Papyrus front end (projection.json names this module).

Editors set the verdict, the four editor scores, the evidence and the entities in an item's front matter.
The dimensions and the verdicts are data in scoring.json; this code only iterates them.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
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

DEPENDS_ON = {"*": [], "item": []}

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
UNDERRATED_PLACEHOLDER_TEXT = "Shown here when Useful and Ready are both high and the signal has few mentions. Works better than it\u2019s talked about."
STORIES_PLACEHOLDER_TEXT = "Stories that cite this signal will be listed here, with who approved them."
NEARBY_PLACEHOLDER_TEXT = "Signals that share entities or a cluster with this one will be listed here."
WARNINGS_ALREADY_LOGGED = set()
STAMP_NOTE_VERBS = {"available": "Confirmed by", "verified": "Verified by"}
STAMP_NOTE_UNNAMED_VERBS = {"available": "Confirmed on", "verified": "Verified on"}
FOOTER_LINKS = (
    ("How the map works", "/map/"),
    ("How steering works", "/policies/#steering"),
    ("Policies", "/policies/"),
    ("All issues", "/roundup/"),
    ("RSS", "/feed.xml"),
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


def _underrated_placeholder_html():
    return (
        '<div class="signal-underrated is-placeholder"><span class="placeholder-tag">Placeholder</span>'
        '<span class="underrated-mark"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">'
        '<path d="M2 13.5h12"/><path d="M4 11l4-4 2 2 3.5-3.5"/><path d="M10 5.5h3.5V9"/></svg>Underrated</span>'
        f'<span>{escape(UNDERRATED_PLACEHOLDER_TEXT)}</span></div>'
    )


def _rail_placeholder_html(heading_id, heading, text):
    return (
        f'<section class="signal-rail-block is-placeholder" aria-labelledby="{heading_id}"><span class="placeholder-tag">Placeholder</span>'
        f'<h2 id="{heading_id}">{escape(heading)}</h2><p>{escape(text)}</p></section>'
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
    main = (
        _article_with_status(html, item, summary)
        + _evidence_section_html(item)
        + _map_section_html(item, site)
        + _ratings_section_html(item, summary)
        + _underrated_placeholder_html()
    )
    rail = (
        _rail_placeholder_html("signal-stories-h", "Appears in these stories", STORIES_PLACEHOLDER_TEXT)
        + _rail_placeholder_html("signal-nearby-h", "Nearby on the map", NEARBY_PLACEHOLDER_TEXT)
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


def block(name, attributes, page):
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
FRONT_NEWSLETTER_DEK = "In the wild, and mapped as it moves. One email on Fridays."
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


def _front_block(page, attributes):
    part = attributes.get("part")
    if part == "signals":
        return _front_signal_count_html(page)
    if part == "newsletter":
        return _front_newsletter_html()
    raise ValueError(f"unknown front part {part!r}")


WEEKLY_ARCHIVE_STRAP = "In the wild, and mapped as it moves."
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


def page_finish(html, page):
    html = _reader_sign_in(html)
    if page.kind != "listing" or page.path != ROUNDUP_ARCHIVE_PATH:
        return html
    heading_end = html.find("</h1>")
    if heading_end < 0:
        LOGGER.warning("roundup archive has no heading; newsletter signup left out")
        return html
    insert_at = heading_end + len("</h1>")
    return html[:insert_at] + _weekly_archive_intro_html() + _newsletter_signup_html() + html[insert_at:]

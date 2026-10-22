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
AGENT_TAG_TEXT = "AI first pass"
SCORING_POLICY_PATH = "/policies/#scores"
RANKING_POLICY_PATH = "/policies/#ranking"
BOARD_HELP_TEXT = (
    "Newest first. Scores are the editor’s, and the editor’s score is the headline figure. "
    "Once readers sign in, upvotes and ratings from readers will be counted apart, on each item."
)
READER_KEY_TEXT = (
    "Upvotes count the readers who want this seen. Ratings are 1 to 5 scores on the four dimensions; the rating count is the number of readers who rated it. "
    "The editor’s score is shown on its own and is the headline figure. Once readers sign in, their ratings will pull a score toward the readers’ view only as more of them rate, "
    "and a reader mean from fewer than 5 ratings is too few to print."
)
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


def _item_reader_html(summary):
    subject = _subject(summary)
    dimensions = [dimension["key"] for dimension in _scoring()["dimensions"]]
    return (
        '<section class="item-reader" aria-labelledby="item-reader-h">'
        '<div class="section-heading"><h2 id="item-reader-h">Readers</h2></div>'
        f'<p class="reader-key">{escape(READER_KEY_TEXT)} <a href="{RANKING_POLICY_PATH}">How ranking works &rarr;</a></p>'
        f'<div class="item-reader-actions">{_island("Vote", {"subject": subject})}{_island("UsedIt", {"subject": subject})}</div>'
        f'{_island("Rating", {"subject": subject, "dimensions": dimensions})}</section>'
    )


def _item_comments_html(summary):
    return (
        '<section class="item-comments" aria-labelledby="item-comments-h">'
        '<div class="section-heading"><h2 id="item-comments-h">Comments</h2></div>'
        f'{_island("Comments", {"subject": _subject(summary)})}</section>'
    )


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
        return {"by": None, "label": None}
    return {"by": _text(raw.get("by")), "label": _text(raw.get("label"))}


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
            f'<span class="score-dimension-value" aria-label="{escape(label)} not scored">&mdash;</span>{note_html}</div>'
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


def _dimensions_html(scores, notes=None, trailing_html=""):
    notes = notes or {}
    return "".join(
        _score_dimension_html(dimension["label"], scores.get(dimension["key"]), notes.get(dimension["key"]))
        for dimension in _scoring()["dimensions"]
    ) + trailing_html


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


def item_decorator(html, summary, site=None):
    if summary.type in (WIKI_ITEM_TYPE, PAGE_ITEM_TYPE):
        return html
    item = _read_item(summary)
    note = _checked_note(item)
    note_html = f'<div class="item-stamp-note">{note}</div>' if note else ""
    maker_html = f'<span class="kicker maker-display">{_maker_html(item)}</span>' if _maker_key(item) else ""
    chips = _entity_chips_html(item["entities"], site)
    chips_html = f'<div class="desk-entities">{chips}</div>' if chips else ""
    scores_html = ""
    if item["scores"]:
        notes_class = " has-notes" if item["score_notes"] else ""
        agent_scored = _is_agent_scored(item)
        scores_label = (item["scoring"]["label"] or DEFAULT_AGENT_SCORES_LABEL) if agent_scored else DEFAULT_SCORES_LABEL
        provenance_html = (
            f'<p class="scoring-provenance">{escape(AGENT_SCORING_NOTICE)} <a href="{SCORING_POLICY_PATH}">How we score &rarr;</a></p>'
            if agent_scored else ""
        )
        scores_html = (
            f'<div class="desk-scores{notes_class}"><p class="kicker">{escape(scores_label)}</p>{provenance_html}'
            f'<div class="desk-score-grid">{_dimensions_html(item["scores"], item["score_notes"])}</div></div>'
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
        f'<div class="item-header-meta"><span class="kicker kicker-ink">Verdict</span>{maker_html}</div>'
        f"{_strip_links_html(item)}{scores_html}{chips_html}</div>"
        f'<div class="item-stamp-block">{_stamp_html(item["verdict"], " status-stamp-xl")}{note_html}</div></header>'
    )
    return strip + _item_reader_html(summary) + html + evidence_html + _item_comments_html(summary)


def _date_label(summary):
    published = _text(_read_item(summary)["released_on"]) or _text(summary.published_at)
    if not published:
        return ""
    try:
        return datetime.fromisoformat(published.replace("Z", "+00:00")).strftime("%-d %b")
    except ValueError:
        return published[:10]


def _source_domain(item):
    if item["source_url"]:
        return urlparse(item["source_url"]).netloc
    for entry in item["evidence"]:
        return urlparse(entry["url"]).netloc
    return ""


def _board_row_html(position, summary, entry, section_label, site=None):
    item = _read_item(summary)
    meta = [f"<b>{escape(_source_domain(item))}</b>"] if _source_domain(item) else []
    meta.append(f"<span>&sect; {escape(section_label)}</span>")
    if _maker_key(item):
        meta.append(f"<span>{_maker_html(item)}</span>")
    date_label = _date_label(summary)
    if date_label:
        meta.append(f"<span>{escape(date_label)}</span>")
    chips = _entity_chips_html(item["entities"], site)
    agent_tag_html = f'<span class="ai-first-pass-tag">{AGENT_TAG_TEXT}</span>' if _is_agent_scored(item) else ""
    return (
        '<li class="board-row">'
        f'<span class="board-rank">{position}</span>'
        f'<div class="board-main"><a class="board-title" href="{escape(entry.url, quote=True)}">{escape(entry.title)}</a>'
        f'<div class="board-meta">{"".join(meta)}</div>'
        + (f'<div class="board-entities">{chips}</div>' if chips else "")
        + _board_reader_html(summary)
        + "</div>"
        f'<div class="board-status">{_stamp_html(item["verdict"])}</div>'
        f'<div class="board-dimensions">{_dimensions_html(item["scores"], None, agent_tag_html)}</div>'
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
    head_dimensions = "".join(f'<span>{escape(dimension["label"])}</span>' for dimension in _scoring()["dimensions"])
    return (
        f'<div class="board-head kicker" aria-hidden="true"><span>Rank</span><span>Item</span><span>Status</span>'
        f'<span class="board-head-dims">{head_dimensions}</span></div>'
        f'<ol class="board-list">{body}</ol>'
    )


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

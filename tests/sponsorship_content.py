"""Extra fictional content for the sponsorship tests: enough signals to carry feed rows, and stories long enough to carry notes.

The base fixtures hold a handful of items, too few for "one row per ten signals". `write_extended_content(directory)` copies
the base fixtures into `directory` and adds the signals and stories below.

Write it for a manual build:  python3 tests/sponsorship_content.py /tmp/shipped-sponsorship-content
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

BASE_CONTENT_DIRECTORY = Path(__file__).resolve().parent / "fixtures" / "content"
DECISION_SIGNAL_COUNT = 24
SPEECH_SIGNAL_COUNT = 14
AGENT_SIGNAL_COUNT = 4

SIGNAL_TEMPLATE = """---
title: "{title}"
date: {date}
releasedOn: {date}
verdict: available
maker: Fixture Lab {number}
tags: [{tags}]
sourceUrl: "https://source.fixture.example/{slug}"
scores: {{useful: 4, ready: 3.5, advances: 3, open: 4}}
entities:
  - {{kind: task, name: {entity}}}
---

This is a fictional fixture item used only by the test suite.
"""

STORY_TEMPLATE = """---
title: "{title}"
standfirst: "{standfirst}"
section: {section}
kind: story
concepts:
{concepts}
cites:
  - {{n: 1, title: "Fixture source", url: "https://source.fixture.example/story-source", date: 2026-10-20}}
drafting: {{by: agent, at: 2026-10-21}}
approval: {{status: approved, by: fixture-editor, at: 2026-10-22}}
---

First paragraph of a fictional fixture story[1].

Second paragraph of a fictional fixture story.

Third paragraph of a fictional fixture story.

Fourth paragraph of a fictional fixture story.

Fifth paragraph of a fictional fixture story.
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _signals(directory: Path, section: str, prefix: str, count: int, tags: str, entity: str, first_day: int, month: int) -> None:
    for number in range(count):
        slug = f"{prefix}-{number:02d}"
        _write(
            directory / section / f"{slug}.md",
            SIGNAL_TEMPLATE.format(
                title=f"Fixture {prefix} signal {number:02d}", date=f"2026-{month:02d}-{first_day - number:02d}",
                number=number, tags=tags, slug=slug, entity=entity,
            ),
        )


def write_extended_content(directory: Path) -> Path:
    shutil.copytree(BASE_CONTENT_DIRECTORY, directory, dirs_exist_ok=True)
    _signals(directory, "decisions", "extra-decision", DECISION_SIGNAL_COUNT, "decision-models, guard-model", "fixture task", 28, 9)
    _signals(directory, "open-weights", "extra-speech", SPEECH_SIGNAL_COUNT, "open-tts, voice-cloning", "text to speech", 28, 8)
    _signals(directory, "shipped", "extra-agent", AGENT_SIGNAL_COUNT, "agents", "tool use agent", 28, 7)
    concepts = "\n".join(f"  - {{kind: task, name: {name}}}" for name in ("text to speech", "fixture task"))
    _write(
        directory / "stories" / "extra-long-story.md",
        STORY_TEMPLATE.format(
            title="Fixture story: decision models learn to speak", standfirst="A fictional story that spans two topics.",
            section="decisions", concepts=concepts,
        ),
    )
    _write(
        directory / "stories" / "extra-plain-story.md",
        STORY_TEMPLATE.format(
            title="Fixture story: nothing in particular", standfirst="A fictional story about nothing the map names.",
            section="shipped", concepts="  - {kind: task, name: fixture misc}",
        ),
    )
    return directory


if __name__ == "__main__":
    write_extended_content(Path(sys.argv[1]))

---
title: "Fixture: a complete item with every field"
date: 2026-10-20
verdict: verified
verdictBy: the fixture editor
verdictAt: 2026-10-20
maker: Fixture Lab
tags: [open-tts, voice-cloning]
releasedOn: 2026-10-20
sourceUrl: "https://source.fixture.example/tts"
scoreNotes: {open: "Weights are public in the fixture."}
scores: {useful: 4, ready: 3.5, advances: 3}
relations:
  - {subject: Fixture model, relation: built on, object: Fixture parent}
evidence:
  - {kind: weights, url: "https://weights.fixture.example/model", check: checked}
  - {kind: eval, url: "https://eval.fixture.example/table", check: partly}
  - {kind: data, url: "https://data.fixture.example/request", check: unchecked}
entities:
  - {kind: task, name: fixture task}
  - {kind: maker, name: Unlisted Fixture Lab}
---

This is a fictional fixture item used only by the test suite.

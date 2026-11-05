---
title: "Fixture story: guard models now name their parents"
standfirst: "Two fictional guard models say which weights they started from, and the map now draws those lines."
section: decisions
kind: story
concepts:
  - {kind: task, name: fixture task}
  - {kind: model, name: Fixture Guard Two}
cites:
  - {n: 1, title: "Fixture Guard Two is built on Fixture Guard One", url: "https://source.fixture.example/guard-two", date: 2026-10-20}
  - {n: 2, title: "Fixture Guard One ships under a permissive licence", url: "https://shipped.anth.us/decisions/fixture-guard-one/", date: 2026-10-18}
figure:
  type: lineage
  pairs:
    - {child: Fixture Guard Two, parent: Fixture Guard One}
    - {child: Fixture Router Three, parent: Fixture Router Two}
proposes: {kind: concept, name: guard-model lineage, why: "Links two models to their parents so later stories can cite the relation."}
drafting: {by: agent, at: 2026-10-21}
approval: {status: approved, by: fixture-editor, at: 2026-10-22}
---

Fixture Guard Two says it is built on Fixture Guard One[1], which shipped earlier under a permissive licence[2].

A marker that cites nothing stays plain text: [9].

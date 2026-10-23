# Editing items

Editors set the verdict, the editor scores, the evidence and the entities of an item in its front matter (the item's `metadata` in the Papyrus CMS). `web/hooks.py` renders them statically on the item page and on the "Latest" board of Front and New. The dimensions and the verdicts are data in `web/scoring.json`.

```yaml
verdict: verified          # available, verified or announced; missing means announced (the old shipped, pending and vapor read as available, announced and announced)
verdictBy: an editor       # optional
verdictAt: 2026-10-20      # optional
scores: {useful: 4, ready: 3.5, advances: 3, open: 4.5}   # editor's 1-5 per dimension; any subset
evidence:
  - {kind: weights, url: https://example.org/weights, check: checked}   # check: checked, partly or unchecked
maker: Some Lab            # optional, shown exactly as stored
makerHandle: some-lab      # optional Hub handle; alone it is shown verbatim in mono
scoring: {by: agent, label: "Editor's first pass (AI-assisted)", at: 2026-10-21}   # by: agent or human; see docs/placeholders.md
entities: [{kind: task, name: code completion}]          # optional, hand-entered until extraction lands
model:                     # optional; puts the signal on the periodic table at /map/. Stated values only, null otherwise
  taskGroup: decide        # decide, route, guard, speak, language, code or see (web/map-view.json)
  parametersTotal: 27      # billions; parametersActive for mixture-of-experts; parameterRange [0.8, 27] for families
  hosted: false            # true: hosted API only, shown below the table
  licence: Apache-2.0      # SPDX id, "non-commercial", a custom licence string, or null
  symbol: Pd               # two letters, unique across items, stable once assigned
  builtOn: pplx-decider    # the parent model as stated, or null
```

The board's source domain is the domain of the first valid evidence link.

Invalid values (a score outside 1 to 5, an unknown dimension, verdict or check, an evidence link that is not http or https) are left out of the page, and a warning with the item key is logged. They never fail the build.

Tests use fictional items in `tests/fixtures/content/`. They are projected only by `tests/test_hooks.py` and are never deployed: deploy projection reads CMS items.

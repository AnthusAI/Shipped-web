# Editing items

Editors set the verdict, the editor scores, the evidence and the entities of an item in its front matter (the item's `metadata` in the Papyrus CMS). `web/hooks.py` renders them statically on the item page and on the "From the desk" board of Front and New. The dimensions, the hype gap formula and the verdicts are data in `web/scoring.json`.

```yaml
verdict: verified          # shipped, verified, pending or vapor; missing means pending
verdictBy: the desk        # optional
verdictAt: 2026-10-20      # optional
scores: {real: 4.5, useful: 4, notable: 3.5, novel: 3}   # editor's 1-5 per dimension; any subset
evidence:
  - {kind: weights, url: https://example.org/weights, check: checked}   # check: checked, partly or unchecked
maker: Some Lab            # optional
entities: [{kind: task, name: code completion}]          # optional, hand-entered until extraction lands
```

The hype gap is shown only when every dimension named in `hypeGap` has a score: the mean of the `plus` dimensions minus the mean of the `minus` dimensions. The board's source domain is the domain of the first valid evidence link.

Invalid values (a score outside 1 to 5, an unknown dimension, verdict or check, an evidence link that is not http or https) are left out of the page, and a warning with the item key is logged. They never fail the build.

Tests use fictional items in `tests/fixtures/content/`. They are projected only by `tests/test_hooks.py` and are never deployed: deploy projection reads CMS items.

# Shipped: operating manual for agents

Read `README.md` first. This repository holds only Shipped's configuration, theme, page files, hooks and tests. The engine is Papyrus: the `@anthusai/papyrus` npm package and the `papyrus-newsroom` Python package. Never copy Papyrus code here. Fix Papyrus in the Papyrus repository and bump the pins.

## Map of the parts

| Part | Where | Docs |
|---|---|---|
| Site and backend registration (`defineSite`), plugins | `papyrus.config.ts` | Papyrus `docs/standard-site.md`, `docs/plugins.md` |
| Public site settings: sections, nav, pages, chrome, SEO, icons, consent | `web/projection.json` | Papyrus `docs/building-a-papyrus-static-site.md` |
| Page files (Markus) | `web/pages/*.md` | Papyrus `docs/markus-content-markup.md` |
| Named hooks and blocks: signal pages, boards, Front, Map and periodic table, concept and section pages, stories, Underrated, Nearby | `web/hooks.py` | the module docstring; `docs/architecture.md` |
| Scoring data: dimensions, statuses, Underrated and Nearby thresholds, `voteSubjects` | `web/scoring.json` | `docs/editing-items.md` |
| Map data: task-group columns, size bands, licence markers | `web/map-view.json` | `web/hooks.py` map group |
| Theme and component CSS, client scripts | `web/css/`, `web/assets/` (`shipped-proposals.js`, `shipped-barcode.js`) | `docs/placeholders.md` |
| Newsroom (CMS) brand | `publication/brand.ts`, `publication/theme.css` | |
| Reader steering: votes, ratings, used-it, flags, comments, submissions, Proposals, snapshots | Papyrus `reader-steering` plugin, configured in `papyrus.config.ts` | Papyrus `docs/reader-steering.md` |
| Newsletter: The Weekly, alerts, branded email | Papyrus `newsletter` plugin, configured in `papyrus.config.ts`, `web/newsletter-lists.json`, `web/assets/email/` | Papyrus `docs/newsletter.md` |
| Edge: CloudFront, the NotFoundPage Lambda@Edge, `/api/*` pass-through to the CMS | `infra/edge/shipped.yaml` | `infra/README.md`, Papyrus `infra/edge/README.md` |
| CMS app shell | `infra/site.json`, `amplify/`, `amplify.yml` | `infra/README.md` |
| Weekly knowledge run (cloud, unattended) | Papyrus scheduled container job | Papyrus `docs/knowledge-cloud-run.md` |
| GA4 and consent | `web/projection.json` `chrome.ga_measurement_id` and `chrome.consent_mode` | Papyrus `docs/site-hosting.md` "Analytics" |

Not used by Shipped today: monitoring and the router, the shared relevance Cyclotron, the procedure runner and Tactus procedures, automations, review requests and the Notification Center. See the Papyrus docs if a task needs them.

## Content model, in brief

- **Signals** are CMS items in the sections `shipped` (labelled "In use"), `open-weights` and `decisions`. Their front matter shape is in `docs/editing-items.md`: `verdict`, `scores`, `scoreNotes`, `scoring`, `evidence`, `entities`, and a `model:` block for the periodic table.
- **Stories** are CMS items in the section `stories`, with `kind: story`. A story renders **only** when `approval.status: approved`. Pending stories never appear in pages, listings or feeds.
- **Proposals** are Papyrus records, filed and transitioned with the `papyrus proposals` CLI by an editor or admin, and published as `/_data/proposals/index.json`. Shipped renders them client-side, and keeps the placeholders until data exists.
- The rating dimensions are `useful`, `ready`, `advances` and `open`. They are configured in `papyrus.config.ts` (reader-steering `dimensions`) and mirrored in `web/scoring.json` for rendering. The vote subject types are mirrored the same way (`subjects.types` and `voteSubjects`). `tests/test_hooks.py` keeps each pair in sync.

## Common tasks

Set up and test:

```bash
npm ci
python3 -m venv .venv && .venv/bin/pip install -r requirements-publication.txt behave
.venv/bin/python -m unittest discover -s tests
.venv/bin/behave features
```

The CI typecheck:

```bash
echo '{}' > amplify_outputs.json
npx papyrus-app sync
npx tsc --noEmit
rm amplify_outputs.json
```

`papyrus-app sync` writes gitignored route shims under `app/`; don't commit them.

**Bump Papyrus:** set the exact version in `package.json`, `infra/package.json`, `infra/site.json` (`papyrusVersion`) and `requirements-publication.txt`. Then refresh both lockfiles and test:

```bash
npm install --package-lock-only
(cd infra && npm install --package-lock-only)
```

**Before bumping Papyrus past 5.32.0:** Papyrus #641 makes proposals private by default; the snapshot only publishes `/_data/proposals/*` when the site sets `proposals.publish: true`. Shipped renders `/proposals/` publicly, so add that setting, in the place Papyrus `docs/reader-steering.md` names, in the same PR as the bump. Otherwise the queue goes empty on the next snapshot.

**Deploy:** merge to `main`. The push run deploys through OIDC, and the `current-main` job stops a late run from deploying an older commit over a newer one. If GitHub does not create the push run (an Actions incident), and only with the owner's OK, start the same job by hand:

```bash
aws amplify start-job --app-id dkycd9pntgo6d --branch-name main --job-type RELEASE --commit-id <sha> --profile papyrus-production
```

**Preview locally:** project the fixtures, as in the README, and serve them over HTTP.

**Re-project production:** happens on every deploy, and the weekly knowledge run projects too. Projections take the projection lease, which ships in Papyrus 5.28.0 and later. A full re-projection without a deploy is a Papyrus CLI task: ask the Papyrus implementation owner.

## Hard rules

- **Never** run a projection `--reconcile` without the deployed plugin list, and never use `--allow-deletions`. The newsletter pages under `/newsletter/*` and `/_plugins/*` are produced at deploy time.
- Secrets go in SSM SecureString, never in the repository. No real email addresses, `amplify_outputs.json` or build output in commits.
- Shared checkouts: never switch branches in someone else's checkout, and never use bare `git stash`. Use your own git worktree.
- Every behaviour change gets a test, plus a Gherkin scenario in `features/` where it is user-visible.
- No line-level comments. Use long, clear names, and match the surrounding style.
- Author content reaches pages only through Markus, with raw HTML disabled. Page files may use `::raw` blocks for layout, as the existing pages do.
- Public data must never carry a reader's Person ID, site subject or email. `tests/reader_privacy.py` scans the built pages, the snapshots and the gtag payloads.
- Placeholders: show the design for anything not built yet, dimmed with one "Placeholder" tag per section. Never put invented numbers beside real data. See `docs/placeholders.md`.
- Wording: never "desk". Attribution is "AI" ("Edited by AI on DATE", "Drafted by AI"), and human sign-off is "Approved by <name>". Say "machine learning" rather than "AI" in descriptive copy. Never "vapor" or "hype gap".
- Colour is never the only signal (the owner is colourblind). Use marks, words and patterns.
- Editorial guidance, sections' missions and the policies page live in the CMS, not in code. Plans, research and roadmap ideas belong in Kanbus issues, not in docs.

## Ownership and coordination

- **Shipped-web**, this repository and the site: the Shipped implementation (product owner) session.
- **Papyrus engine:** plugins, projector, CLI, cloud knowledge run, email rendering. Owned by the Papyrus implementation session. Ask it for engine changes, releases, CMS data publishes and Proposals filing.
- **Prospectus:** reader identity. Tell the Prospectus session before anything touches Prospectus `main`.
- **Owner decisions:** Ryan decides product and policy. A change he relays through another session is confirmed with him before it is acted on.

## Current state (2026-10-24)

**Live:**
- GA4 with the anth.us standard Consent Mode (2026-10-24, Ryan's decision): Accept all grants analytics and the three ad signals; Reject all denies all; the EEA, UK and CH start denied; `analytics_only` stays off; no reader identity is sent.
- the living-map redesign, with the label logotype and daily barcode;
- Front, the Map (periodic table, graph, river), signal, concept, section and story pages, Submit, The Weekly and Proposals;
- 70 signals rescored on the new dimensions;
- three approved stories, leading Front and two section pages;
- Papyrus 5.33.1, with voting on items, submissions, stories and proposals, `proposals: { publish: true }`, and the newsroom Notification Center and review requests;
- the branded newsletter, with one-click unsubscribe proven server-side;
- the unattended weekly knowledge run, with about 376 wiki pages.

**Open:**
- The first proposal needs Ryan's editor login (`papyrus login`) before it can be filed. Until then the Proposals placeholders stay.
- A real end-to-end Google sign-in and vote by a person is still to be confirmed. The server path was verified with a synthetic reader.
- The 26-week river fills in as weekly history accumulates.

## Where to look next

- `docs/`: architecture, editing items, placeholders.
- The Kanbus board, project key `ship`. Use the `kbs` CLI (`pip install kanbus`) with `KANBUS_NO_DAEMON=1 KANBUS_REALTIME_TRANSPORT=none KANBUS_REALTIME_BROKER=off KANBUS_REALTIME_AUTOSTART=false`. Never edit `project/` by hand. Board changes go through a PR into `main`. Statuses move open → in_progress → blocked → closed. The initiative "Launch Shipped" (ship-57b2b2) and its epics list what remains.

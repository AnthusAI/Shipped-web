# Shipped architecture: reader interaction on a static site

Status: decided 2026-10-21 for the pilot. Generic pieces are built in Papyrus (initiative PPY-77bb3b, collaborative steering, and PPY-428252, public knowledge base). This repository holds only Shipped's settings, theme and pages.

## The shape in one paragraph

The public site stays a static S3 projection behind the `papyrus-edge-shipped` CloudFront distribution. Readers sign in with Prospectus accounts (Google only) through the CMS app's existing `/api/auth/prospectus/*` routes, which the edge already serves on the same origin (`/api/*` → CMS app). Votes, ratings, submissions, comments and reports go to a small authenticated **reader API**, `/api/reader/*`, in the same CMS app. The route checks the sealed session cookie and the Origin, then invokes one Papyrus plugin Lambda that owns validation, rate limits, moderation state and storage. Nothing a reader writes is readable through GraphQL by guests. Public numbers reach the page as **snapshot JSON** in the site bucket (`/_data/...`), rebuilt by the content-actions Lambda after writes and every 6 hours, and read by small client islands that poll. No AppSync subscriptions.

```
reader ── static pages (S3 via CloudFront) ── islands poll /_data/*.json
   │
   └── same origin /api/* ── CMS app (Next.js on Amplify)
          ├── /api/auth/prospectus/*   sign-in, session cookie (exists)
          └── /api/reader/*            identity + Origin check → invoke reader-actions Lambda
                                          └── DynamoDB models (staff/IAM only) ──▶ snapshot task ──▶ /_data/*.json
```

## 1. Reader identity

- **Prospectus accounts**, Google only (standing rule: never Cognito password users). The CMS app already has sign-in, callback, session and sign-out routes. They need `PAPYRUS_SITE_ORIGIN` (Papyrus ≥ 5.15.1, delivered by the app-shell deploy), Shipped's registration in Prospectus `accounts/papyrus-sites.json`, and `cms.prospectusAccountsApiStageArn` in `infra/site.json`.
- The session is the sealed `__Host-papyrus-prospectus-session` cookie (`personId`). It is first-party, `Secure`, and scoped to `shipped.anth.us`.
- **Reader profile** (new Papyrus model `ReaderProfile`, keyed by publication and `personId`): a public handle picked at first sign-in, a created time, karma (derived), and a moderation state (`active`, `limited`, `banned`). No email or name is ever published.
- Editors are readers too. Their votes carry `voterRole: editor`, derived server-side from their staff group, never sent by the client.
- Static pages learn who is signed in from `GET /api/reader/me` (no-store). It returns the handle, karma and the reader's own votes for the items on the page, so the page shows them at once without waiting for a snapshot.

## 2. Public write API

Choice: **routes in the CMS app plus one plugin Lambda.** The alternatives were a separate API Gateway with a Lambda authorizer, and guest GraphQL mutations. This choice reuses the session code and the edge behaviour that already exist and adds no new public endpoint. The domain logic stays in a Papyrus plugin (`reader-steering`, under the plugin contract in `docs/plugins.md`), so other publications get it by configuration.

| Route | Does |
|---|---|
| `GET /api/reader/me` | handle, karma, own votes for the given item ids |
| `POST /api/reader/handle` | choose the handle once (unique per publication, a reserved-word list) |
| `POST /api/reader/vote` | upvote toggle on an item |
| `POST /api/reader/rating` | 1–5 on one dimension; the dimensions are publication data (Shipped: real, useful, notable, novel) |
| `POST /api/reader/used-it` | "I used it" report (feeds the Shipped rule) |
| `POST /api/reader/submit` | submit a link; public at once as Pending; extraction is asynchronous |
| `POST /api/reader/comment` | comment, optionally attached to the reader's rating as its rationale |
| `POST /api/reader/report` | report an item or comment for moderation |

Every write route does the same things in the same order:
1. Require a valid session, then an `Origin` equal to `PAPYRUS_SITE_ORIGIN` (CSRF), then a JSON body under a size cap.
2. Invoke `reader-actions` with `{publicationId, personId, role, action, payload}`. The compute role holds `lambda:InvokeFunction` on that one function only.
3. The Lambda validates against publication data (dimensions, sections, moderation mode), applies rate limits, writes, and returns the new own-state. The page updates optimistically.

## 3. Storage

DynamoDB through Amplify Data models in Papyrus. All are **staff/IAM-only**: guests never read them through GraphQL. Public data leaves only through the snapshot.

| Model | Key | Notes |
|---|---|---|
| `ReaderProfile` | publication + personId | handle (unique GSI), state, createdAt |
| `ReaderVote` | deterministic id `subject#person#dimension` | `dimension` ∈ {`up`, publication dimensions, `used-it`}, `value`, `voterRole`, timestamps. One row per person, subject and dimension, so a revote overwrites it. |
| Submission | the existing `Reference` (pending), with provenance | `submittedBy` personId; canonical-URL dedupe via `canonical_source_url` |
| Comment | `Message` with `messageKind: reader_comment` | `threadId` = subject, `moderationState` |
| `ModerationAction` | id | who, what, why, when; the audit for hide, approve and ban |
| `ReaderRateWindow` | person + action + window | counter with a TTL (see 4) |

Editorial facts (verdict, editor scores, evidence links) stay **item front matter** in the CMS. They are public by design and render statically.

## 4. Rate limits and abuse controls

- **Per-person limits** in `reader-actions`, from a conditional DynamoDB counter per person, action and window, with a TTL. Starting limits (publication data, not code): 120 votes/ratings per hour, 10 submissions per day, 30 comments per hour, 20 reports per day. A new account (under 24 h) gets a third of each.
- **Moderation mode** per publication: `off`, `human` (post-hoc queue; content is public at once, as Ryan decided) or `ai` (GPT-6 Luna verdict with human override). Shipped starts in `human`. The queue lives in the newsroom Administration panel, with approve, hide, ban and an undo for each action.
- **Content checks**: submissions get Humanus checks and URL normalisation; comments get a length cap and a link cap. A hidden item or comment is dropped from the next snapshot.
- **Edge**: no WAF. Ryan rejected it on 2026-10-21: a rate spike costs less than the rule's $6/month. Per-person limits and the Lambda's reserved concurrency (a cap of 10) bound the cost.
- Bans are by `personId`. Prospectus is Google-only, so making new accounts takes effort.

## 5. Publishing numbers: snapshots plus client components

- **Snapshot task** `reader-snapshot` in the content-actions Lambda reads votes, profiles and published items with IAM and writes public-safe JSON. That means ids, handles, counts, means, n, histograms and timestamps, and never private text.
  - `/_data/board/front.json`, `new.json`, `rising.json`, `vapor.json`: ranked rows.
  - `/_data/items/<itemKey>.json`: per-dimension mean, n and histogram, editor mean, upvotes, used-it count, hype gap (blank under n=5), comment count and approved comments.
  - `/_data/readers/top.json`: karma leaderboard.
  - Every file carries `generatedAt`.
- **Triggers**: a debounced run after writes (the `reader-actions` Lambda queues one asynchronous invoke at most per minute), plus an EventBridge schedule every 6 hours (4 runs a day) for time decay and Rising. Ryan approved it on 2026-10-21.
- **Caching**: `/_data/*` is served with `Cache-Control: max-age=30`, and the task invalidates `/_data/*` after it writes.
- **Client components**: small islands in Papyrus (`papyrus-board`, `papyrus-score-readout`, `papyrus-vote`, `papyrus-freshness`). Each prerenders the last values into the page where possible, fetches the JSON on load, polls every 60 s while the tab is visible, and shows "Updated N min ago". The reader's own vote is optimistic and comes from `/api/reader/me`.
- **Ranking**: v1 orders the Front by editor composite × time decay until readers have rated. How reader and editor scores combine is an open exploration (PPY-0b2cbb). The snapshot writes both values separately so the formula can change without moving any data.
- **Score combination (exploration ship-1f3d29, PPY-0b2cbb; awaiting Ryan's decision, nothing changed in production).** Simulated on the 70 published items (editor composite sd 0.28) with honest, disagreeing, brigading, cold-start and overhyped readers. Recommended: Bayesian shrinkage per dimension with prior strength k = 20 and the reader share capped at 0.4 (`share = min(n / (20 + n), 0.4)`), ratings from profiles under 24 h counted at 1/3, no `readerMinimum`. Against the current blend it removes the jump at the fifth rating (7 ranks to about 1), needs 28 sock accounts instead of 13 to push a mid-table item into the top 5 (96 at 1/3 weight), and follows genuine reader disagreement more slowly (gap closure 0.36 against 0.44 at 30 raters). Wilson on upvotes for Front is not recommended: it ignores the editors, is unstable at likely volume and ranks an overhyped item first. Rising and the 3-report "Shipped" stamp are exposed to a handful of accounts whatever the formula, so they should count only profiles older than 24 h. Full write-up and simulation: Papyrus `docs/score-combination.md`.

## 6. Item pages

- **Editorial items** are Papyrus `article` Items in the three sections. Front matter: `verdict` (`shipped`, `verified`, `pending`, `vapor`), `scores` (the editor's 1–5 per dimension), `evidence` (a typed link list with a check state), `entities` (until extraction lands), and `maker`. The site's `hooks.py` renders the stamp, the scores, the hype gap and the evidence on the item page and as board cards, statically.
- **Reader submissions** are public at once as Pending rows on New, from snapshot JSON. Each row links to its source. An item page appears when an editor promotes the submission to an Item. Pending items therefore have no static page in v1. They are listed and agent-readable through the JSON. This keeps unreviewed text out of the sitemap.

## 7. What needs approval or input

- Decided 2026-10-21: the EventBridge schedule is approved at every 6 hours; the WAF rule is rejected.
- Shipped's registration in Prospectus (a Prospectus repo change, cyclotron-production) and the app-shell deploy for `PAPYRUS_SITE_ORIGIN`. The deploy is approved; the change set is reviewed before it is executed.
- Google client redirect URIs for the Shipped Cognito domain: Ryan adds them himself.
- Real editorial items: long term they come from standard Papyrus monitoring. To start, editors seed them by manual research, in this order: decision models, then open TTS models from the last year, then open LLMs. Each item is a real, verifiable release with a primary source. Sample items and their marks go once real items fill the board.

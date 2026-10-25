# Shipped

**New arrivals in machine learning.** https://shipped.anth.us

Shipped is a Papyrus publication in three layers:
- **Signals:** machine-learning releases and deployments, the CMS items. Each has a status (Available, Verified or Announced) and ratings on Useful, Ready, Advances and Open.
- **The map:** concepts, entities, clusters and trends, built weekly from the signals. It includes a periodic table of the models Shipped tracks.
- **Stories:** AI-drafted insight about what changed, published only after an editor approves them.

Signed-in readers steer by voting on signals, stories and proposals and by flagging mistakes. Editors decide, and can override readers, with a public reason.

This repository holds **only what is specific to Shipped**: configuration, theme, page files, hooks and tests. The engine is [Papyrus](https://github.com/AnthusAI/Papyrus). It supplies the newsroom (CMS), the Amplify Gen 2 backend, the static projector, the reader-steering and newsletter plugins, and the cloud knowledge run. Related systems:
- **Prospectus:** reader accounts, Google sign-in and pairwise per-site reader ids.
- **Biblicus:** topic modelling and entity extraction, used by the knowledge run.

## Where it runs

| What | Where |
|---|---|
| Public site | https://shipped.anth.us: a static S3 projection behind the CloudFront stack `papyrus-edge-shipped` (`infra/edge/shipped.yaml`) |
| Newsroom (CMS) | https://shipped.anth.us/newsroom: Amplify app `dkycd9pntgo6d`, branch `main`, app-shell stack `amplify-app-shell-shipped-cms` |
| Reader API, newsletter routes | `/api/*` on the same origin, routed by the edge to the CMS app |
| AWS | account `papyrus-production` (`712236451410`), `us-east-1` |
| Weekly knowledge run | Papyrus scheduled container job (Step Functions + ECS Fargate), Mondays 05:00 UTC. Runbook: Papyrus `docs/knowledge-cloud-run.md` |

## Quick start

Prerequisites: Node 22, Python 3.12, and the GitHub CLI for PRs.

```bash
npm ci
python3 -m venv .venv && .venv/bin/pip install -r requirements-publication.txt behave
.venv/bin/python -m unittest discover -s tests
.venv/bin/behave features
```

`requirements-publication.txt` pins `papyrus-newsroom[markus]` to the same version as `@anthusai/papyrus` in `package.json` (currently **5.33.1**).

Build the public site locally from the test fixtures, then serve it over HTTP. Opening the pages from disk breaks the root-relative assets.

```bash
.venv/bin/papyrus ops content project --all --from-dir tests/fixtures/content --static-dir web --knowledge-dir tests/fixtures/knowledge --out /tmp/shipped-out
python3 -m http.server 8000 --directory /tmp/shipped-out
```

The CMS dev server (`npm run dev`) needs a deployed backend's `amplify_outputs.json`, which is gitignored and never committed.

## Sponsorship

Anthus sponsorship units (a bar on every page, and banners, sidebar cards, contextual notes and feed rows on some) are built in `web/hooks.py` from `web/sponsorship.json`, which holds the switch, the disclosure copy, the six solutions with their pitches and landing URLs, and the keywords that match a page to a solution. The switch is `"enabled": false`: while it is off, no page carries a unit, the sponsorship stylesheet or script, and the footer is unchanged. Set `"enabled": true` to turn everything on, and add a `#sponsorship` section to the policies page first, because the disclosure and footer links point at `/policies/#sponsorship`.

Units are the only rounded shapes on the site and always show the word "Sponsored", a diamond mark and the Anthus name. `web/assets/shipped-sponsorship.js` sends the Google Analytics events `view_promotion` (once per unit, after half the unit has been visible for one second) and `select_promotion` (on a click of a sponsored link), carrying only the unit and page fields in the `data-sponsor-*` attributes and never a reader id. `tests/reader_privacy.py` scans both. `tests/test_sponsorship.py` builds the site switched off and switched on from `tests/sponsorship_content.py`.

## How a change reaches production

1. Branch from `main`, open a PR into `main`, and get CI green. `develop` exists but is stale; work goes to `main`.
2. Merging to `main` runs `.github/workflows/deploy.yml`:
   - CI: typecheck, unit tests, behave;
   - `current-main`: skips the deploy if a later commit has already landed;
   - the deploy, which starts the Amplify RELEASE job for that commit through GitHub OIDC (role `shipped-github-deploy`). No AWS keys are stored.
3. The Amplify job builds the CMS, deploys the backend and re-projects the public site.
4. Papyrus versions: Papyrus releases with semantic-release. To adopt a release, bump the exact pin in `package.json`, `infra/package.json`, `infra/site.json` and `requirements-publication.txt` together, and update both lockfiles.

See [`AGENTS.md`](AGENTS.md) for the operating manual, and [`docs/`](docs/) for architecture, editing items and placeholders.

---

Built by [Anthus AI Solutions](https://anth.us) on [Papyrus](https://github.com/AnthusAI/Papyrus).

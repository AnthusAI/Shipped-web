# Shipped publication

This repository holds only what is specific to Shipped (shipped.anth.us): community-ranked AI that actually shipped, meaning announcements and real-world deployments (including open-weights releases and decision models used in the wild), scored on dimensions such as real, useful, notable and novel. The newsroom application, the Amplify Gen 2 backend, the S3 projection engine and the deployment constructs come from the pinned `@anthusai/papyrus` npm package and the `papyrus-newsroom` Python package. Do not copy Papyrus code into this repository. Fix Papyrus in the Papyrus repository and bump the pins.

## Layout

- `papyrus.config.ts`: registers the brand and the backend (`defineSite`). `backend.publication` is the S3 projection: the standard Papyrus front end renders pages from `web/projection.json`, and the whole `web/` directory is bundled into the content-actions Lambda as `site_static/`.
- `publication/brand.ts`, `publication/theme.css`: the newsroom (CMS) brand. The CMS uses the generic Papyrus theme pack with the `newspaper-gothic` Kanbus theme.
- `web/projection.json`, `web/css/site-theme.css`: the settings and the placeholder theme of the standard Papyrus front end. No hooks module. The design is made by Ryan in Claude Design and lands later. See the Papyrus guide "Building a Papyrus static site".
- `amplify/`, `amplify.yml`, `infra/`: the CMS app and backend, and the edge stack (`infra/edge/shipped.yaml`), as for every Papyrus site. See `infra/README.md`.

## Development policy (Ryan, 2026-11-04)

- Develop and verify on a local dev server: `npm ci` then `npm run dev` (runs `papyrus-app sync`, then `next dev` on port 3001; it needs a backend's `amplify_outputs.json`, gitignored). For the seeded console with no AWS, run `npm run dev:preview` in a Papyrus checkout. Do not deploy to see whether something works.
- **Merge** means merging a pull request into `develop`; that is where things are reviewed. `develop` builds nothing in Amplify.
- **Release** means merging `develop` into `main`, which deploys. Aim for once or twice a day, batching what is ready. An extra release needs Ryan's say-so.
- Papyrus version bumps go to this site's `develop` and ship in this site's release. A Papyrus release can add a GSI and a deploy can add only one per table, so a site cannot skip a release that adds one.
- Say "merged to develop" or "released" precisely.

## Workflow

1. CMS: `npm ci` then `npm run dev` (runs `papyrus-app sync`, which writes gitignored route shims). It needs a backend's `amplify_outputs.json` (gitignored).
2. Changing the Papyrus version: edit the exact pin in `package.json`, `infra/package.json`, `infra/site.json` and `requirements-publication.txt` together, in a pull request into `develop`. It ships in the next release.
3. Git Flow: branch from `develop`, open a pull request into `develop` (a merge), and release by merging `develop` into `main`. The release deploys the CMS build and re-projects the public site.
4. Never commit secrets, real email addresses, `amplify_outputs.json` or build output.

## Rules

- No line-level comments. Use long, clear names.
- This repository is public and its code is a generic container. Sections, editorial missions, scoring dimensions and policies live only in the newsroom's backend data, never in code or seed files. Plans, research and roadmap ideas belong in Kanbus issues.
- Author content reaches pages only through Markus with raw HTML disabled.
- Kanbus is the record of work (project key `ship`). Use the `kbs` CLI (`pip install kanbus`); never read or edit the `project/` directory directly. Without a realtime broker, run it with `KANBUS_NO_DAEMON=1 KANBUS_REALTIME_TRANSPORT=none KANBUS_REALTIME_BROKER=off KANBUS_REALTIME_AUTOSTART=false`. The initiative "Launch Shipped" lists what remains.

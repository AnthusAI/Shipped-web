# Shipped publication

This repository holds only what is specific to Shipped (shipped.anth.us): community-ranked AI that actually shipped, meaning announcements and real-world deployments (including open-weights releases and decision models used in the wild), scored on dimensions such as real, useful, notable and novel. The newsroom application, the Amplify Gen 2 backend, the S3 projection engine and the deployment constructs come from the pinned `@anthusai/papyrus` npm package and the `papyrus-newsroom` Python package. Do not copy Papyrus code into this repository. Fix Papyrus in the Papyrus repository and bump the pins.

## Layout

- `papyrus.config.ts`: registers the brand and the backend (`defineSite`). `backend.publication` is the S3 projection: the standard Papyrus front end renders pages from `web/projection.json`, and the whole `web/` directory is bundled into the content-actions Lambda as `site_static/`.
- `publication/brand.ts`, `publication/theme.css`: the newsroom (CMS) brand. The CMS uses the generic Papyrus theme pack with the `newspaper-gothic` Kanbus theme.
- `web/projection.json`, `web/css/site-theme.css`: the settings and the placeholder theme of the standard Papyrus front end. No hooks module. The design is made by Ryan in Claude Design and lands later. See the Papyrus guide "Building a Papyrus static site".
- `amplify/`, `amplify.yml`, `infra/`: the CMS app and backend, and the edge stack (`infra/edge/shipped.yaml`), as for every Papyrus site. See `infra/README.md`.

## Workflow

1. CMS: `npm ci` then `npm run dev` (runs `papyrus-app sync`, which writes gitignored route shims). It needs a backend's `amplify_outputs.json` (gitignored).
2. Changing the Papyrus version: edit the exact pin in `package.json`, `infra/package.json`, `infra/site.json` and `requirements-publication.txt` together.
3. Git Flow: branch from `develop`, open a pull request into `develop`, and release by merging `develop` into `main`. Merging to `main` deploys the CMS build and re-projects the public site.
4. Never commit secrets, real email addresses, `amplify_outputs.json` or build output.

## Rules

- No line-level comments. Use long, clear names.
- This repository is public and its code is a generic container. Sections, editorial missions, scoring dimensions and policies live only in the newsroom's backend data, never in code or seed files. Plans, research and roadmap ideas belong in Kanbus issues.
- Author content reaches pages only through Markus with raw HTML disabled.
- Kanbus is the record of work (project key `ship`). Use the `kbs` CLI (`pip install kanbus`); never read or edit the `project/` directory directly. Without a realtime broker, run it with `KANBUS_NO_DAEMON=1 KANBUS_REALTIME_TRANSPORT=none KANBUS_REALTIME_BROKER=off KANBUS_REALTIME_AUTOSTART=false`. The initiative "Launch Shipped" lists what remains.

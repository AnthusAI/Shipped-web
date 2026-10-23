# Placeholders

Parts of the site still show a design with fictional data. Each one carries the class `is-placeholder`, defined once in `web/assets/shipped-components.css`: dimmed to 0.6 opacity, a dashed outline, and one small "Placeholder" tag (`.placeholder-tag`) at the top-left of the block. A real item never sits inside a dimmed wrapper.

- Whole section or block: add `is-placeholder` to the section and put one `<span class="placeholder-tag">Placeholder</span>` inside it.
- Inline number or chip inside a real component: add `is-placeholder is-placeholder-inline` and `title="Placeholder"`. This dims it and gives it a dotted underline, with no outline and no tag.
- Pages that are placeholders from top to bottom (Rising, Roundup, the sample item and topic pages) wrap the mocked part, not the preview line that explains it.

When a feature goes live, remove the class (and the tag) from that block in the same change that makes the data real.

## Score provenance

Item front matter may carry `scoring: {by: agent, label: "Editor's first pass (AI-assisted)", at: 2026-10-21}`. With `by: agent` the item page labels the scores with `label` and says an AI research pass produced them; the editors column of the ratings table carries an "AI first pass" tag; the topic page profile says "Editor scores (AI-assisted first pass)". With `by: human` or no `scoring`, the label is "Editor score". Optional `makerHandle` is shown as stored, in mono, beside `maker` (as "maker (handle)") or alone.

## Signal page

"Appears in these stories" on signal pages and "Stories that cite it" on concept pages are real: they list approved stories that cite the page, and hide when none do. Items still carrying the old score keys (real, notable, novel) show no scores for them, show the new dimensions as "Not yet rated", and log one warning per item.

The Underrated mark, the Underrated panel on the home page and "Nearby on the map" are real, built at projection time from the items and the knowledge snapshot (`site.knowledge`):

- Mentions of a signal: how many other accepted signals share at least one of its accepted entities. An entity counts only when the snapshot has it; unresolved names are ignored.
- Underrated: editor Useful and Ready both at least `underrated.minimumUseful` and `underrated.minimumReady` in `web/scoring.json` (4 and 4), and mentions within the quietest `underrated.quietestShare` of the signals that pass those two (about the bottom third, ties kept), never above `underrated.mentionCeiling`. The mark and the figures are labelled with the item's score label ("Editor's first pass" for agent-scored items). A signal that fails the rule shows nothing, and the home panel (up to `underrated.homeLimit` signals) is left out when none qualify.
- Nearby: up to `nearby.limit` other signals, ranked by shared accepted entities, then the same beat (topic), then newest. The reason reads "Shares maker X and task Y", or "Same beat: Decision models" when only the beat is shared. Cluster membership is not in the snapshot, so beats stand in for clusters. The block is left out when there are none.
- The sample item page (`/sample/tern-3/`) still shows a dimmed Underrated design reference.

## Reader steering is live

Reader sign-in, votes, "I used it", ratings, comments and submissions are real (Papyrus 5.22.0 `reader-steering` plugin; `web/hooks.py` mounts the islands and `head_extra` loads the reader script). The Submit and Sign in pages are real. The steering invitation on home and concept pages ("Sign in to vote, rate and say what you've used.") is live and carries no placeholder marking; drafts voting stays a placeholder inside the Proposals sections only. "The table this week" on home is real: a compact periodic table built from the same model data as the map (symbols only, models released in the last 7 days marked with a heavy border and a dot, counts in the header). Still placeholders: the Rising board and rail (waiting for a ranked-list island; a real line above each says so) The sample item and topic pages stay as dimmed design references.

## Proposals render from published data

`web/assets/shipped-proposals.js` fetches `/_data/proposals/index.json` and fills the Proposals queue, the home "Steer the map" list (top 3 by net among in steering and editor review) and "Open proposals touching this concept" (matched on the concept name or key). Until the file exists and has entries, the placeholder markup stays exactly as built. Concept pages hide the block when data exists but nothing matches. Voting uses its own buttons posting `{subject: {type: "proposal", id}, value: 1 | -1 | null}` to `/api/reader/vote`; they stay disabled with "Proposal voting opens soon" until `window.papyrusReader.proposalVoting` is true. The "Two tiers" example on the Proposals page remains a placeholder.

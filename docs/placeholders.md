# Placeholders

Parts of the site still show a design with fictional data. Each one carries the class `is-placeholder`, defined once in `web/assets/shipped-components.css`: dimmed to 0.6 opacity, a dashed outline, and one small "Placeholder" tag (`.placeholder-tag`) at the top-left of the block. A real item never sits inside a dimmed wrapper.

- Whole section or block: add `is-placeholder` to the section and put one `<span class="placeholder-tag">Placeholder</span>` inside it.
- Inline number or chip inside a real component: add `is-placeholder is-placeholder-inline` and `title="Placeholder"`. This dims it and gives it a dotted underline, with no outline and no tag.
- Pages that are placeholders from top to bottom (Rising, Roundup, Submit, Sign in, the sample item and topic pages) wrap the mocked part, not the preview line that explains it.

When a feature goes live, remove the class (and the tag) from that block in the same change that makes the data real.

## Score provenance

Item front matter may carry `scoring: {by: agent, label: "Editor's first pass (AI-assisted)", at: 2026-10-21}`. With `by: agent` the item page labels the scores with `label` and says an AI research pass produced them; board rows show an "AI first pass" tag; the topic page profile says "Editor scores (AI-assisted first pass)". With `by: human` or no `scoring`, the label is "Editor score". Optional `makerHandle` is shown as stored, in mono, beside `maker` (as "maker (handle)") or alone.

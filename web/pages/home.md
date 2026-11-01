::band{size="bare"}

::raw
<div class="shipped-page front">
<div class="front-bar">
<p class="front-stats">
::endraw

::include{kind="block" name="front" part="signals"}

::include{kind="block" name="knowledge-topic-count" count=entities label="{n} entities on the map"}

::raw
</p>
<div class="front-invite">
<span class="front-invite-out">Readers vote on what goes on this map. Sign in to vote, rate and say what you've used.</span>
<span class="front-invite-in">You are signed in. Vote, rate and say what you've used on any signal.</span>
<div class="front-invite-action" data-island="ReaderSignIn" data-props="{}"><a class="front-quiet-button" href="/sign-in/">Sign in</a></div>
</div>
</div>

<div class="front-row front-row-lead">
::endraw

::include{kind="block" name="stories" part="lead"}

::raw

<aside class="front-side" aria-label="This week on the map">
<section class="front-map" aria-labelledby="front-map-h">
<div class="front-side-heading"><h2 id="front-map-h">The map this week</h2><a class="front-link" href="/map/">Open the map</a></div>
::endraw

::include{kind="block" name="map-week"}

::include{kind="block" name="knowledge-clusters" limit=4 terms=3 empty="No clusters yet. They appear when the topic model finds a group of items that belong together."}

::include{kind="block" name="map-changes"}

::raw
</section>
</aside>
</div>

<div class="front-row front-row-wide">
::endraw

::include{kind="block" name="front" part="table"}

::raw
</div>

<div class="front-row">
::endraw

::include{kind="block" name="stories" part="also"}

::raw

<section class="rail front-rising" aria-labelledby="front-rising-h">
<div class="rail-heading"><h2 id="front-rising-h" class="rail-h">Rising concepts</h2><span class="kicker">8 weeks</span></div>
::endraw

::include{kind="block" name="knowledge-trending-list" limit=5 definition=false empty="Nothing is rising yet. Concepts need a month of coverage to show a trend."}

::raw
</section>
</div>

<div class="front-row front-row-wide">
<section class="front-proposals is-placeholder" aria-labelledby="front-proposals-h" data-proposals-live="home">
<span class="placeholder-tag">Placeholder</span>
<div class="front-section-heading"><span class="cintillo">Proposals</span><h2 id="front-proposals-h">Up for a vote</h2><a class="front-link front-link-end" href="/sign-in/">Sign in to vote</a></div>
<p class="front-proposals-note">AI-written drafts, not yet approved · ranked by reader votes · editors decide</p>
<ul class="front-proposal-list">
<li class="front-proposal"><div class="front-vote"><button type="button" disabled aria-label="Vote up: [proposal title]"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="M8 3l5.5 9h-11z"/></svg></button><span class="front-vote-count">[n]</span><button type="button" disabled aria-label="Vote down: [proposal title]"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="M8 13l5.5-9h-11z"/></svg></button></div><div class="front-proposal-body"><div class="front-proposal-tags"><span class="front-draft-tag"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M10.5 2.5l3 3-8 8H2.5v-3z"/></svg>Draft · not yet approved</span><span class="front-steering-tag"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M5 13V3M2.5 5.5L5 3l2.5 2.5"/><path d="M11 3v10M8.5 10.5L11 13l2.5-2.5"/></svg>Open for votes</span><span class="kicker">Concept</span></div><a class="front-proposal-title" href="/sign-in/">[Proposal title]</a><span class="front-proposal-change">[What changes on the map if this is approved.]</span></div></li>
<li class="front-proposal"><div class="front-vote"><button type="button" disabled aria-label="Vote up: [proposal title]"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="M8 3l5.5 9h-11z"/></svg></button><span class="front-vote-count">[n]</span><button type="button" disabled aria-label="Vote down: [proposal title]"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="M8 13l5.5-9h-11z"/></svg></button></div><div class="front-proposal-body"><div class="front-proposal-tags"><span class="front-draft-tag"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M10.5 2.5l3 3-8 8H2.5v-3z"/></svg>Draft · not yet approved</span><span class="front-steering-tag"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M5 13V3M2.5 5.5L5 3l2.5 2.5"/><path d="M11 3v10M8.5 10.5L11 13l2.5-2.5"/></svg>Open for votes</span><span class="kicker">Map change</span></div><a class="front-proposal-title" href="/sign-in/">[Proposal title]</a><span class="front-proposal-change">[What changes on the map if this is approved.]</span></div></li>
<li class="front-proposal"><div class="front-vote"><button type="button" disabled aria-label="Vote up: [proposal title]"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="M8 3l5.5 9h-11z"/></svg></button><span class="front-vote-count">[n]</span><button type="button" disabled aria-label="Vote down: [proposal title]"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="M8 13l5.5-9h-11z"/></svg></button></div><div class="front-proposal-body"><div class="front-proposal-tags"><span class="front-draft-tag"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M10.5 2.5l3 3-8 8H2.5v-3z"/></svg>Draft · not yet approved</span><span class="front-steering-tag"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M5 13V3M2.5 5.5L5 3l2.5 2.5"/><path d="M11 3v10M8.5 10.5L11 13l2.5-2.5"/></svg>Open for votes</span><span class="kicker">Story</span></div><a class="front-proposal-title" href="/sign-in/">[Proposal title]</a><span class="front-proposal-change">[What changes on the map if this is approved.]</span></div></li>
</ul>
</section>

::endraw

::include{kind="block" name="front" part="underrated" depends="*"}

::raw
</div>

<div class="front-latest">
::endraw

::include{kind="block" name="desk-board" depends="*" heading="Latest signals" more="true"}

::raw
<p class="front-footnote">Scores on seeded items are an AI-assisted first pass from the linked sources; human editors re-score them. <a href="/policies/#ranking">How ranking works →</a> <a href="/policies/#scores">How we score →</a></p>
</div>

::endraw

::include{kind="block" name="front" part="newsletter"}

::raw
</div>
::endraw

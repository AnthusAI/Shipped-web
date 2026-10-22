::band{size="bare"}

::include{kind="block" name="knowledge-trending-strip" limit=5 empty="Nothing is trending yet."}

::raw
<div class="shipped-page">

<nav class="beats" aria-label="Editors’ beats"><span class="kicker">Beats</span><a class="is-placeholder is-placeholder-inline" title="Placeholder" href="/wiki/task-voice-agents/">Voice agents</a><a class="is-placeholder is-placeholder-inline" title="Placeholder" href="/">Coding models</a><a class="is-placeholder is-placeholder-inline" title="Placeholder" href="/">Document AI</a><a href="/topics/decision-models/">Decision models</a><a href="/topics/open-tts/">Open TTS</a><a class="is-placeholder is-placeholder-inline" title="Placeholder" href="/">Speech</a><a class="is-placeholder is-placeholder-inline" title="Placeholder" href="/">Evals</a><a class="is-placeholder is-placeholder-inline" title="Placeholder" href="/">Agents</a>
::endraw

::include{kind="block" name="knowledge-topic-count" count=entities href="/wiki/" label="Topic index · {n} topics"}

::raw
</nav>
<div class="shipped-layout">
<div class="shipped-main">
<nav class="view-tabs" aria-label="Views"><a href="/">Front</a><a href="/new/" aria-current="page">New</a><a href="/rising/">Rising</a></nav>
::endraw

::include{kind="block" name="desk-board" depends="*" limit="200" level="1"}

::raw
</div>
<aside class="shipped-rails">
<section class="rail" aria-labelledby="trending-h"><div class="rail-heading"><h2 id="trending-h" class="rail-h">Trending topics</h2><span class="kicker">8 wks</span></div>
::endraw

::include{kind="block" name="knowledge-trending-list" limit=6 definition=false empty="Nothing is trending yet. Topics need a month of coverage to show a trend."}

::raw
</section><section class="rail rail-tinted" aria-labelledby="concept-h"><div class="kicker rail-kicker" id="concept-h">From the wiki · concept of the week</div>
::endraw

::include{kind="block" name="knowledge-concept-of-the-week" empty="No concept of the week yet."}

::raw
</section><section class="rail" aria-labelledby="rising-h"><div class="rail-heading"><h2 id="rising-h" class="rail-h">Rising</h2><span class="kicker">Upvotes, last 6 hours</span></div><div data-island="RankedList" data-props="{&quot;list&quot;:&quot;rising&quot;,&quot;limit&quot;:5,&quot;empty&quot;:&quot;Rising starts counting once readers vote.&quot;}"></div></section><section class="rail" aria-labelledby="key-h"><h2 id="key-h" class="rail-h">How to read a row</h2><dl class="rail-key"><dt><span class="status-stamp status-stamp-available"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M2.5 2.5h11v11h-11z"/><path d="M5 8.2l2 2 4-4.4"/></svg><span class="status-stamp-label">Available</span></span></dt><dd>Anyone can use it today.</dd><dt><span class="status-stamp status-stamp-verified"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="8" cy="8" r="5.8"/><path d="M5.4 8.1l1.8 1.8 3.4-3.7"/></svg><span class="status-stamp-label">Verified</span></span></dt><dd>Available, and an editor checked the evidence.</dd><dt><span class="status-stamp status-stamp-announced"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><circle cx="8" cy="8" r="1.6"/><path d="M4.8 11.2a4.5 4.5 0 0 1 0-6.4"/><path d="M11.2 4.8a4.5 4.5 0 0 1 0 6.4"/></svg><span class="status-stamp-label">Announced</span></span></dt><dd>Claimed, not yet usable or not yet confirmed.</dd></dl><p class="rail-note">Scores on seeded items are an AI-assisted first pass from the linked sources; human editors re-score them. The headline figure is the editor’s score. Once readers sign in, upvotes (readers who want it seen) and ratings (readers who scored it) will be counted apart on each item, and ratings will pull an item’s score toward the readers’ view only as more readers rate it. <a href="/policies/#ranking">How ranking works →</a> <a href="/policies/#scores">How we score →</a></p></section>
</aside>
</div>
</div>
::endraw

::band{size="bare"}

::include{kind="block" name="knowledge-trending-strip" limit=5}

::raw
<div class="shipped-page">

<nav class="beats" aria-label="Editors’ beats"><span class="kicker">Beats</span><a class="is-placeholder is-placeholder-inline" title="Placeholder" href="/wiki/task-voice-agents/">Voice agents</a><a class="is-placeholder is-placeholder-inline" title="Placeholder" href="/">Coding models</a><a class="is-placeholder is-placeholder-inline" title="Placeholder" href="/">Document AI</a><a href="/topics/decision-models/">Decision models</a><a href="/topics/open-tts/">Open TTS</a><a class="is-placeholder is-placeholder-inline" title="Placeholder" href="/">Speech</a><a class="is-placeholder is-placeholder-inline" title="Placeholder" href="/">Evals</a><a class="is-placeholder is-placeholder-inline" title="Placeholder" href="/">Agents</a>
::endraw

::include{kind="block" name="knowledge-topic-count" count=entities href="/wiki/" label="All {n} topics"}

::raw
</nav>
<div class="shipped-layout">
<div class="shipped-main">
<nav class="view-tabs" aria-label="Views"><a href="/">Front</a><a href="/new/" aria-current="page">New</a><a href="/rising/">Rising</a><a href="/vapor/">Vapor log</a></nav>
::endraw

::include{kind="block" name="desk-board" depends="*" limit="200" level="1"}

::raw
</div>
<aside class="shipped-rails">
<section class="rail" aria-labelledby="trending-h"><div class="rail-heading"><h2 id="trending-h" class="rail-h">Trending topics</h2><span class="kicker">8 wks</span></div>
::endraw

::include{kind="block" name="knowledge-trending-list" limit=6}

::raw
<p class="rail-note">Change compares the items in the last 4 weeks with the 4 before. No percent when those 4 weeks hold fewer than 5 items or the topic has under 8 weeks of history. Under 4 weeks it is new.</p></section><section class="rail rail-tinted" aria-labelledby="concept-h"><div class="kicker rail-kicker" id="concept-h">From the wiki · concept of the week</div>
::endraw

::include{kind="block" name="knowledge-concept-of-the-week"}

::raw
</section><section class="rail rising-status" aria-label="Rising status"><p class="rising-line rail-note">Rising starts counting once readers vote. Updated every 6 hours. <span class="reader-freshness" data-island="Freshness" data-props="{}"></span></p></section><section class="rail is-placeholder" aria-labelledby="rising-h"><div class="rail-heading"><h2 id="rising-h" class="rail-h">Rising</h2><span class="kicker">Votes / hr</span><span class="placeholder-tag">Placeholder</span></div><ol class="rail-list"><li class="rail-item rail-item-velocity"><a class="rail-item-title" href="/">Kiln-3B: a small open model for structured extraction, MIT licence</a><span class="velocity"><svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M3 11l4-4 2.5 2.5L13 6"/><path d="M9.5 6H13v3.5"/></svg>▲ +46/h</span><span class="board-meta rail-item-source">hub.example · Document AI</span></li><li class="rail-item rail-item-velocity"><a class="rail-item-title" href="/">Port of Calder publishes its container-inspection risk model and false-positive rate</a><span class="velocity"><svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M3 11l4-4 2.5 2.5L13 6"/><path d="M9.5 6H13v3.5"/></svg>▲ +31/h</span><span class="board-meta rail-item-source">portofcalder.example · Decision models</span></li><li class="rail-item rail-item-velocity"><a class="rail-item-title" href="/">Quillwork’s contract redlining leaves beta in its Word add-in</a><span class="velocity"><svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M3 11l4-4 2.5 2.5L13 6"/><path d="M9.5 6H13v3.5"/></svg>▲ +22/h</span><span class="board-meta rail-item-source">quillwork.example · Document AI</span></li><li class="rail-item rail-item-velocity"><a class="rail-item-title" href="/">Wren TTS weights are out, under a non-commercial licence</a><span class="velocity"><svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M3 11l4-4 2.5 2.5L13 6"/><path d="M9.5 6H13v3.5"/></svg>▲ +19/h</span><span class="board-meta rail-item-source">code.example · Speech</span></li><li class="rail-item rail-item-velocity"><a class="rail-item-title" href="/">Fieldnote ships offline meeting summaries on recent Pixel phones</a><span class="velocity"><svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M3 11l4-4 2.5 2.5L13 6"/><path d="M9.5 6H13v3.5"/></svg>▲ +14/h</span><span class="board-meta rail-item-source">fieldnote.example · Speech</span></li></ol></section><section class="rail" aria-labelledby="key-h"><h2 id="key-h" class="rail-h">How to read a row</h2><dl class="rail-key"><dt><span class="status-stamp status-stamp-shipped"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M2.5 2.5h11v11h-11z"/><path d="M5 8.2l2 2 4-4.4"/></svg><span class="status-stamp-label">Shipped</span></span></dt><dd>Publicly available. Readers have used it.</dd><dt><span class="status-stamp status-stamp-verified"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="8" cy="8" r="5.8"/><path d="M5.4 8.1l1.8 1.8 3.4-3.7"/></svg><span class="status-stamp-label">Verified</span></span></dt><dd>Shipped, and an editor checked the evidence.</dd><dt><span class="status-stamp status-stamp-pending"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="8" cy="8" r="5.8"/><path d="M8 4.8V8l2.2 1.4"/></svg><span class="status-stamp-label">Pending</span></span></dt><dd>Claimed. Nobody has confirmed it yet.</dd><dt><span class="status-stamp status-stamp-vapor"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="8" cy="8" r="5"/><path d="M3 13L13 3"/></svg><span class="status-stamp-label">Vapor</span></span></dt><dd>Announced, demoed or waitlisted. Not something you can use.</dd></dl></section>
</aside>
</div>
</div>
::endraw

::band{size="bare"}

::raw
<div class="shipped-page">
<p class="preview-line" style="padding-top:0;margin-bottom:20px">Dimmed sections with a dashed outline are placeholders that show the design. Everything at full strength is real.</p>
<article class="roundup-article is-placeholder">
<div class="roundup-column">
<div style="display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center"><span class="cintillo">Weekly roundup</span><span class="kicker" style="color:var(--ink)">Week 43 · 19–25 Oct 2026</span></div>
<h1 class="roundup-title">The week the weights came with receipts <span class="placeholder-tag">Placeholder</span></h1>
<p class="roundup-dek">Two open releases shipped their training manifests. One of them also shipped the model. Elsewhere: a county that showed its work, and an autonomous engineer that has not yet shown up.</p>
<div class="roundup-byline">
<div class="roundup-byline-facts"><span style="font-weight:600">BY AI</span><span style="color:var(--muted)">FRI 23 OCT 2026</span><span style="color:var(--muted)">8 MIN READ</span><span style="color:var(--muted)">10 ITEMS · 6 TOPICS</span></div>
<div class="roundup-actions"><a class="button" href="/roundup/">Email subscribe</a><a class="button button-quiet" href="/feed.xml">RSS</a></div>
</div>
<p class="board-note">Scores as of Fri 23 Oct 2026, frozen at publish. <a href="/">Live scores are on the board.</a></p>
</div>
<div class="roundup-column roundup-body">
<p class="drop-cap">Every week a few hundred things are announced as AI products. This week, by our count, about forty of them could be used by someone who does not work at the company. That is roughly the usual ratio, and it is why this list exists.</p>
<p>The top of the board went to open weights, which is not unusual. What was unusual was the paperwork. Both of the week’s large releases came with a list of what they were trained on, and in one case that list was detailed enough to argue with.</p>
<h2><span class="section-number">01</span>Receipts, and a model to go with them</h2>
<p>Tern-3 topped the week’s board, scoring high on Real and solidly on Useful. It is a 14B coding model that fits on one consumer card, under a licence lawyers do not need to read twice. Our editors pulled the weights and reran the harness; two of three suites landed within a point of the card.</p>
<div class="roundup-table-wrap"><table class="roundup-table roundup-table-items"><thead><tr><th scope="col">Status</th><th scope="col">Item</th><th scope="col">Real</th><th scope="col">Useful</th><th scope="col">Notable</th><th scope="col">Novel</th></tr></thead><tbody><tr><td><span class="status-stamp status-stamp-verified"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="8" cy="8" r="5.8"/><path d="M5.4 8.1l1.8 1.8 3.4-3.7"/></svg><span class="status-stamp-label">Verified</span></span></td><td><a href="/">Tern-3: a 14B open-weights coding model that fits on one 24 GB card</a></td><td>4.60</td><td>3.93</td><td>3.96</td><td>2.71</td></tr></tbody></table></div>
<p>Readers were less impressed on Novel, and they are right. This is a known recipe done carefully. The comment thread spent forty messages establishing that, and then another twenty explaining how they had already deployed it.</p>
<p>Basalt-70B is the more interesting release and the less finished one. The manifest and deduplication scripts are public and thorough; the weights download, but nobody outside the lab has yet reproduced the headline numbers on hardware they can describe. It sits at Announced, and it will stay there until someone does.</p>
<div class="roundup-table-wrap"><table class="roundup-table roundup-table-items"><thead><tr><th scope="col">Status</th><th scope="col">Item</th><th scope="col">Real</th><th scope="col">Useful</th><th scope="col">Notable</th><th scope="col">Novel</th></tr></thead><tbody><tr><td><span class="status-stamp status-stamp-announced"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><circle cx="8" cy="8" r="1.6"/><path d="M4.8 11.2a4.5 4.5 0 0 1 0-6.4"/><path d="M11.2 4.8a4.5 4.5 0 0 1 0 6.4"/></svg><span class="status-stamp-label">Announced</span></span></td><td><a href="/">Basalt-70B: open weights with a public training manifest</a></td><td>3.20</td><td>3.80</td><td>4.40</td><td>4.10</td></tr></tbody></table></div>
<blockquote class="pull-quote">A training manifest is a promise you can check. That alone puts it ahead of most launch posts.</blockquote>
<h2><span class="section-number">02</span>Decisions, on the record</h2>
<p>Harlow County now routes non-emergency 311 calls through a triage model, which is not news. Publishing the audit log, including the calls the model sent to the wrong department, is. It was the week’s highest-scoring item on Notable, and the only one to score above 3.5 on all four dimensions.</p>
<div class="roundup-table-wrap"><table class="roundup-table roundup-table-items"><thead><tr><th scope="col">Status</th><th scope="col">Item</th><th scope="col">Real</th><th scope="col">Useful</th><th scope="col">Notable</th><th scope="col">Novel</th></tr></thead><tbody><tr><td><span class="status-stamp status-stamp-available"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M2.5 2.5h11v11h-11z"/><path d="M5 8.2l2 2 4-4.4"/></svg><span class="status-stamp-label">Available</span></span></td><td><a href="/">Harlow County routes 311 calls through a triage model and publishes the audit log</a></td><td>4.40</td><td>3.60</td><td>4.50</td><td>3.80</td></tr></tbody></table></div>
<p>Northgate Mutual’s claims-triage model card is thinner, but it includes the number regulators asked for: how often a human overrides the model, and how often an appeal succeeds. We would like to see that figure become boring and universal.</p>
<h2><span class="section-number">03</span>Announced, not yet usable</h2>
<div class="claim-line"><span class="status-stamp status-stamp-announced status-stamp-xl"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><circle cx="8" cy="8" r="1.6"/><path d="M4.8 11.2a4.5 4.5 0 0 1 0-6.4"/><path d="M11.2 4.8a4.5 4.5 0 0 1 0 6.4"/></svg><span class="status-stamp-label">Announced</span></span><span class="claim-facts">WAYPOINT · “AUTONOMOUS SRE”</span></div>
<p>Waypoint’s autonomous site-reliability engineer has a demo video, a waitlist and a pricing page with no prices on it. It drew more comments than anything else this week, mostly from people who carry a pager. Its Notable score is respectable; its Real score is the lowest on the board. Both are deserved.</p>
<p>Halyard-2, a vision model with a benchmark table and a “weights coming soon” banner, joins it among the claims. We will happily change the stamp the day the download link works.</p>
<h2><span class="section-number">04</span>What the graph noticed</h2>
<p>The topic model flagged a new cluster this week: public audit logs for government triage, seven items across three jurisdictions, none of which cite each other. Meanwhile voice agents nearly doubled in mentions over eight weeks while the number that shipped rose by a third. Most of the gap is outbound sales callers.</p>
<div class="roundup-aside">
<p class="kicker" style="margin:0 0 8px">Trending topics, change in mentions</p>
<div class="topic-chips"><a class="topic-chip" href="/">Voice agents<i>▲ +0.8</i></a><a class="topic-chip" href="/">Autonomous SRE<i>▲ +2.1</i></a><a class="topic-chip" href="/">Training-data manifests<i>▼ −0.4</i></a><a class="topic-chip" href="/">Override rates<i>▼ −0.3</i></a><a class="topic-chip" href="/">On-device speech<i>▼ −0.6</i></a></div>
<h2><span class="section-number">05</span>The board at a glance</h2>
<div class="roundup-table-wrap"><table class="roundup-table roundup-table-items"><thead><tr><th scope="col">Status</th><th scope="col">Item</th><th scope="col">Real</th><th scope="col">Useful</th><th scope="col">Notable</th><th scope="col">Novel</th></tr></thead>
<tbody>
<tr><td><span class="status-stamp status-stamp-verified"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="8" cy="8" r="5.8"/><path d="M5.4 8.1l1.8 1.8 3.4-3.7"/></svg><span class="status-stamp-label">Verified</span></span></td><td>Tern-3 14B</td><td>4.6</td><td>3.9</td><td>4.0</td><td>2.7</td></tr>
<tr><td><span class="status-stamp status-stamp-available"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M2.5 2.5h11v11h-11z"/><path d="M5 8.2l2 2 4-4.4"/></svg><span class="status-stamp-label">Available</span></span></td><td>Ledgerline extraction GA</td><td>4.8</td><td>4.2</td><td>3.1</td><td>2.0</td></tr>
<tr><td><span class="status-stamp status-stamp-available"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M2.5 2.5h11v11h-11z"/><path d="M5 8.2l2 2 4-4.4"/></svg><span class="status-stamp-label">Available</span></span></td><td>Harlow County 311 triage</td><td>4.4</td><td>3.6</td><td>4.5</td><td>3.8</td></tr>
<tr><td><span class="status-stamp status-stamp-announced"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><circle cx="8" cy="8" r="1.6"/><path d="M4.8 11.2a4.5 4.5 0 0 1 0-6.4"/><path d="M11.2 4.8a4.5 4.5 0 0 1 0 6.4"/></svg><span class="status-stamp-label">Announced</span></span></td><td>Basalt-70B</td><td>3.2</td><td>3.8</td><td>4.4</td><td>4.1</td></tr>
<tr><td><span class="status-stamp status-stamp-available"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M2.5 2.5h11v11h-11z"/><path d="M5 8.2l2 2 4-4.4"/></svg><span class="status-stamp-label">Available</span></span></td><td>Formwell on-device STT</td><td>4.5</td><td>4.0</td><td>2.9</td><td>2.6</td></tr>
</tbody></table></div>
<p class="board-note" style="margin-top:0">Scores as of Fri 23 Oct 2026, frozen when this issue was published. Live scores are on the board. Scores on seeded items are an AI-assisted first pass from the linked sources; human editors re-score them.</p>
</div>
<p>As ever: if you used something this week that worked, submit it with the evidence. If you used something that did not, say so in the thread. Both are useful.</p>
</div>
<div class="roundup-column roundup-pager">
<a href="/roundup/"><span class="kicker">Previous · Wk 42</span><strong>Three agent frameworks and one agent</strong></a>
<a href="/"><span class="kicker">The live board</span><strong>Shipped this week, ranked now</strong></a>
</div>
</article>
</div>
::endraw

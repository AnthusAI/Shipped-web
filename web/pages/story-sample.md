::band{size="bare"}

::raw
<div class="shipped-page story-page">
<p class="preview-line">Dimmed sections with a dashed outline are placeholders that show the design. This sample story and every lineage claim in it stay unverified until a real story replaces them.</p>
<div class="story-layout">
<article class="story-article is-placeholder" aria-labelledby="story-h">
<span class="placeholder-tag">Placeholder</span>
<nav class="story-breadcrumb" aria-label="Breadcrumb"><a href="/">Front</a><span aria-hidden="true">/</span><a href="/decisions/">Decisions in the wild</a><span aria-hidden="true">/</span><a href="/topics/decision-models/">Decision models</a></nav>
<div class="story-flags"><span class="cintillo">Story</span><span class="kicker story-flags-section">Decisions in the wild</span></div>
<h1 id="story-h" class="story-title">Decision models are starting to have family trees</h1>
<p class="story-standfirst">Three decision models released since 20 September say whose weights they started from. The map now draws those lines, and this story proposes a concept to track them.</p>
<div class="story-provenance"><span class="story-ai-mark">AI</span><span>Drafted by AI</span><span aria-hidden="true">·</span><span><b>[n]</b> readers steered it</span><span aria-hidden="true">·</span><span>Approved by <b>[editor]</b></span><span aria-hidden="true">·</span><span>[DATE]</span></div>

<figure class="story-figure">
<p class="kicker story-figure-note">Sample lineage · not yet verified</p>
<div class="story-lineage" role="img" aria-label="Diagram: pplx-decider to REAX 1.1, StartLux weights to Torchcast Decision 27B, Qwen3.5-9B to Kev-9B, each joined by a built-on arrow">
<div class="story-lineage-row"><span class="story-node"><b>pplx-decider</b><span>Perplexity · 1 Oct</span></span><span class="story-arrow"><svg viewBox="0 0 120 14" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true"><path d="M0 7h110"/><path d="M104 1l9 6-9 6"/></svg><span>built on</span></span><span class="story-node story-node-child"><b>REAX 1.1</b><span>REAX · 21 Oct</span></span></div>
<div class="story-lineage-row"><span class="story-node"><b>StartLux weights</b><span>StartLux</span></span><span class="story-arrow"><svg viewBox="0 0 120 14" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true"><path d="M0 7h110"/><path d="M104 1l9 6-9 6"/></svg><span>built on</span></span><span class="story-node story-node-child"><b>Torchcast Decision 27B</b><span>Torchcast AI · 3 Oct</span></span></div>
<div class="story-lineage-row"><span class="story-node"><b>Qwen3.5-9B</b><span>Qwen</span></span><span class="story-arrow"><svg viewBox="0 0 120 14" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true"><path d="M0 7h110"/><path d="M104 1l9 6-9 6"/></svg><span>built on</span></span><span class="story-node story-node-child"><b>Kev-9B</b><span>Jared Palmer · 20 Sep</span></span></div>
</div>
<figcaption class="story-figcaption"><span>Parents on the left, children on the right. Each arrow is a “built on” relation taken from the release itself.</span><span class="story-figure-credit">Figure: Shipped map · Edited by AI</span></figcaption>
</figure>

<div class="story-body">
<p>A decision model is a model whose job is to make a judgement rather than write prose. Twenty of them now sit in the map’s Decision models cluster, and three of the newest say exactly whose weights they started from.</p>
<p><span class="story-entity">REAX 1.1</span> is a 27B decision model fine-tuned from Perplexity’s <span class="story-entity">pplx-decider</span><a href="#src-1" class="story-cite" aria-label="Source 1">1</a>, which shipped three weeks earlier under Apache-2.0<a href="#src-2" class="story-cite" aria-label="Source 2">2</a>. <span class="story-entity">Torchcast Decision 27B</span> is built on StartLux weights<a href="#src-3" class="story-cite" aria-label="Source 3">3</a>, and StartLux’s own Decision v1.1 ships with non-commercial weights<a href="#src-4" class="story-cite" aria-label="Source 4">4</a>. <span class="story-entity">Kev-9B</span> is a LoRA on Qwen3.5-9B<a href="#src-5" class="story-cite" aria-label="Source 5">5</a>.</p>
<p>Until this week the map stored those as loose mentions. Now they are “built on” relations, and together they form something the map had no name for: a lineage. That raises the question every adopter asks of a fine-tune. When the parent changes, what do its children inherit?</p>
<p>So this story proposes a new concept, <b>decision-model lineage</b>, so the map can track parents and children directly. It is in the Proposals queue now. If editors approve it, it becomes a node, and later stories will cite it.</p>
</div>

<section id="story-map" class="story-map-box" aria-labelledby="story-changes-h">
<div class="story-map-head">
<h2 id="story-changes-h">What this changes on the map</h2>
<span class="story-draft-tag"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M10.5 2.5l3 3-8 8H2.5v-3z"/></svg>Draft · not yet approved</span>
</div>
<div class="story-map-change">
<svg viewBox="0 0 16 16" width="18" height="18" aria-hidden="true"><circle cx="8" cy="8" r="5" fill="currentColor"/></svg>
<div class="story-map-change-text"><strong>Proposes the new concept “decision-model lineage”</strong><span class="kicker">Concept proposal · links 3 models to their parents</span></div>
<span class="status-stamp story-steering-mark"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M5 13V3M2.5 5.5L5 3l2.5 2.5"/><path d="M11 3v10M8.5 10.5L11 13l2.5-2.5"/></svg>In steering</span>
<div class="story-vote" role="group" aria-label="Vote on the concept proposal"><a class="story-vote-button" href="#story-signin-concept" aria-label="Vote up the concept proposal"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="M8 3l5.5 9h-11z"/></svg></a><span class="story-vote-count">[n]</span><a class="story-vote-button" href="#story-signin-concept" aria-label="Vote down the concept proposal"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="M8 13l5.5-9h-11z"/></svg></a></div>
</div>
<div id="story-signin-concept" class="story-signin" role="group" aria-label="Sign in to steer"><strong>Sign in to steer this.</strong><span>Takes 10 seconds; we never publish your email. You come back here with your vote counted.</span><span class="story-signin-actions"><a class="button" href="/sign-in/">Sign in</a><a class="button button-quiet" href="#story-map">Not now</a></span></div>
<div class="story-relations">
<p class="kicker">Strengthens these relations</p>
<div class="story-relation"><span>REAX 1.1</span><span class="story-relation-arrow"><svg viewBox="0 0 92 10" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true"><path d="M0 5h82"/><path d="M78 .5l8 4.5-8 4.5"/></svg>built on</span><span>pplx-decider</span></div>
<div class="story-relation"><span>Torchcast Decision 27B</span><span class="story-relation-arrow"><svg viewBox="0 0 92 10" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true"><path d="M0 5h82"/><path d="M78 .5l8 4.5-8 4.5"/></svg>built on</span><span>StartLux weights</span></div>
<div class="story-relation"><span>Kev-9B</span><span class="story-relation-arrow"><svg viewBox="0 0 92 10" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true"><path d="M0 5h82"/><path d="M78 .5l8 4.5-8 4.5"/></svg>built on</span><span>Qwen3.5-9B</span></div>
</div>
</section>

<section id="story-react" class="story-react" aria-labelledby="story-react-h">
<h2 id="story-react-h" class="kicker">Was this story right?</h2>
<div class="story-vote" role="group" aria-label="Vote on the story"><a class="story-vote-button" href="#story-signin-story" aria-label="Vote the story up"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="M8 3l5.5 9h-11z"/></svg></a><span class="story-vote-count">[n]</span><a class="story-vote-button" href="#story-signin-story" aria-label="Vote the story down"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="M8 13l5.5-9h-11z"/></svg></a></div>
<a class="story-quiet-button" href="#story-signin-story"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M3.5 14V2.5"/><path d="M3.5 3h8l-2 3 2 3h-8"/></svg>This is wrong</a>
<span class="story-comment-count">[n] comments</span>
<div id="story-signin-story" class="story-signin" role="group" aria-label="Sign in to steer"><strong>Sign in to steer this.</strong><span>Takes 10 seconds; we never publish your email. Editors read every “This is wrong”.</span><span class="story-signin-actions"><a class="button" href="/sign-in/">Sign in</a><a class="button button-quiet" href="#story-react">Not now</a></span></div>
</section>

<ol class="story-sources" aria-label="Signals cited">
<li class="kicker story-sources-heading">Signals cited</li>
<li id="src-1"><span class="story-cite">1</span><span class="story-source-title">REAX 1.1: a 27B decision model fine-tuned from pplx-decider</span><span class="story-source-meta">huggingface.co · 21 Oct</span></li>
<li id="src-2"><span class="story-cite">2</span><span class="story-source-title">Perplexity releases pplx-decider, an Apache-2.0 27B decision model</span><span class="story-source-meta">huggingface.co · 1 Oct</span></li>
<li id="src-3"><span class="story-cite">3</span><span class="story-source-title">Torchcast AI releases Torchcast Decision 27B, built on StartLux weights</span><span class="story-source-meta">huggingface.co · 3 Oct</span></li>
<li id="src-4"><span class="story-cite">4</span><span class="story-source-title">StartLux releases Decision v1.1, from 0.8B to 27B, with non-commercial weights</span><span class="story-source-meta">huggingface.co · 11 Oct</span></li>
<li id="src-5"><span class="story-cite">5</span><span class="story-source-title">Jared Palmer releases Kev-9B, an Apache-2.0 LoRA decision model on Qwen3.5-9B</span><span class="story-source-meta">huggingface.co · 20 Sep</span></li>
</ol>
</article>

<aside class="story-rails">
<section class="rail story-rail is-placeholder" aria-labelledby="story-concepts-h">
<span class="placeholder-tag">Placeholder</span>
<h2 id="story-concepts-h" class="rail-h">Concepts in this story</h2>
<div class="story-chips"><span class="entity-chip"><i>topic</i>Decision models</span><span class="entity-chip"><i>model</i>pplx-decider</span><span class="entity-chip"><i>model</i>REAX 1.1</span><span class="entity-chip"><i>maker</i>StartLux</span><span class="entity-chip"><i>model</i>Qwen3.5-9B</span><span class="entity-chip"><i>licence</i>Apache-2.0</span></div>
</section>
<section class="rail story-rail is-placeholder" aria-labelledby="story-related-h">
<span class="placeholder-tag">Placeholder</span>
<h2 id="story-related-h" class="rail-h">Related stories</h2>
<p class="story-related"><span>[STORY HEADLINE] on routers and typed decisions</span><span class="kicker">Decisions in the wild · [DATE]</span></p>
<p class="story-related"><span>[STORY HEADLINE] on guard models</span><span class="kicker">Decisions in the wild · [DATE]</span></p>
<p class="story-related"><span>[STORY HEADLINE] on open licences</span><span class="kicker">Open weights · [DATE]</span></p>
</section>
</aside>
</div>
</div>
::endraw

::band{size="bare"}

::raw
<div class="shipped-page topic-page concept-page">
<nav class="crumbs" aria-label="Breadcrumb"><a href="/">Front</a><span aria-hidden="true">/</span><a href="/open-weights/">Open weights</a><span aria-hidden="true">/</span><span>Open TTS</span></nav>
<header class="concept-header">
<div class="concept-header-main">
<div class="concept-kinds"><span class="concept-kind">TOPIC</span><span>FOLLOWED AS A BEAT</span></div>
<h1 class="concept-title">Open TTS</h1>
<p class="concept-definition">Open-weights text-to-speech and voice-cloning models from the last year. Each entry states the licence of the weights, or says that it is not stated.</p>
::endraw

::include{kind="block" name="concept-provenance" key=open-tts depends="*"}

::raw
</div>
<div class="concept-header-side">
::endraw

::include{kind="block" name="concept-stats" key=open-tts tag="open-tts" depends="*"}

::include{kind="block" name="concept-actions" depends="*"}

::raw
</div>
</header>

<div class="concept-invite">
<span>This map is steered by its readers. Sign in to vote, rate and say what you've used.</span>
<a class="concept-button concept-button-small" href="/sign-in/">Sign in</a>
<a class="concept-link" href="/policies/#ranking">How steering works</a>
</div>

<div class="concept-row">
<section class="concept-column-narrow" aria-labelledby="lineage-h"><div class="section-heading"><span class="cintillo">Lineage</span><h2 id="lineage-h">Where it came from</h2></div>
::endraw

::include{kind="block" name="concept-lineage" tag="open-tts" depends="*"}

::raw
</section>
<section class="concept-column-wide" aria-labelledby="beat-trend-h"><div class="section-heading"><span class="cintillo">Trend</span><h2 id="beat-trend-h">Signals per week</h2></div>
::endraw

::include{kind="block" name="knowledge-beat" key=open-tts part=trend}

::raw
</section>
</div>

<div class="concept-row">
<section class="concept-column-wide" aria-labelledby="hood-h"><div class="section-heading"><span class="cintillo">Graph</span><h2 id="hood-h">Neighbourhood</h2><span class="section-heading-note">WEIGHT = SIGNALS LINKING BOTH</span></div>
::endraw

::include{kind="block" name="concept-neighbourhood" tag="open-tts" label="Open TTS" depends="*"}

::raw
</section>
<section class="concept-column-narrow" aria-labelledby="beat-entities-h"><div class="section-heading"><span class="cintillo">Inside</span><h2 id="beat-entities-h">Sub-concepts</h2></div>
::endraw

::include{kind="block" name="knowledge-beat" key=open-tts part=entities limit=24}

::raw
<h3 class="concept-subhead" id="beat-clusters-h">Clusters it touches</h3>
::endraw

::include{kind="block" name="knowledge-beat" key=open-tts part=clusters limit=6}

::raw
</section>
</div>

<section class="concept-proposals is-placeholder" aria-labelledby="proposals-h" data-proposals-live="concept" data-concept-name="Open TTS" data-concept-key="open-tts"><span class="placeholder-tag">Placeholder</span>
<div class="section-heading"><span class="cintillo">Proposals</span><h2 id="proposals-h">Open proposals touching this concept</h2></div>
<p class="concept-note">Reader proposals are not switched on yet. When they are, open proposals about this concept will be listed here, newest votes first.</p>
<ul class="concept-proposal-list"><li><span class="concept-proposal-kind">New concept</span> [Proposed title] <span class="concept-note">[n] votes</span></li><li><span class="concept-proposal-kind">Merge</span> [Proposed title] <span class="concept-note">[n] votes</span></li></ul>
</section>

<div class="concept-row">
<section class="concept-column-wide" aria-labelledby="signals-h"><div class="section-heading"><span class="cintillo">Signals</span><h2 id="signals-h">Latest signals</h2></div>
::endraw

::include{kind="block" name="concept-signals" tag="open-tts" limit=10 depends="*"}

::raw
</section>
::endraw

::include{kind="block" name="concept-stories" key=open-tts label="Open TTS" tag="open-tts" depends="*"}

::raw
</div>
</div>
::endraw

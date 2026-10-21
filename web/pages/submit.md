::band{size="bare"}

::raw
<div class="shipped-page">
<div class="form-layout">
<div class="form-main">
<p class="preview-notice" role="note"><span class="cintillo">Preview</span><span>Preview: submitting is not open yet. This form shows the design; nothing you type here is sent.</span></p>
<span class="cintillo">Submit · signed-in view</span> <span class="sample-mark" title="Fictional sample data that previews the design">Sample</span>
<h1 class="form-title">Submit something that shipped</h1>
<p class="form-dek">Link to the thing itself, not the announcement about the thing. If it has a waitlist, it goes in as a claim and probably comes out stamped Vapor.</p>
<fieldset disabled class="form-fields">
<legend class="kicker">Submission form (preview, not working)</legend>
<section class="form-section" aria-labelledby="link-h">
<div class="step-line"><span class="cintillo">01</span><h2 id="link-h">The link</h2></div>
<div class="field"><label for="url">Primary URL</label><input id="url" class="field-input field-input-mono" type="url" value="https://hub.example/kiln-ai/kiln-3b" aria-describedby="url-hint"><span id="url-hint" class="field-hint">The weights, the product page you can sign up and use today, the changelog entry or the public record of the decision.</span></div>
<div class="duplicate-warning" role="status"><svg viewBox="0 0 16 16" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><circle cx="8" cy="8" r="5.8"/><path d="M8 5v3.4"/><path d="M8 10.6v.2"/></svg><div><strong>Possible duplicate.</strong> “Kiln-3B: a small open model for structured extraction, MIT licence” was submitted 5h ago from the same domain. <a href="/">Add your evidence there</a> instead, or carry on if this is a different release. <span class="sample-mark" title="Fictional sample data that previews the design">Sample</span></div></div>
<div class="field"><label for="title">Title</label><input id="title" class="field-input" type="text" value="Kiln-3B: a small open model for structured extraction, MIT licence" aria-describedby="title-hint"><span id="title-hint" class="field-hint">Say what shipped and who shipped it. No adjectives the maker would use. 90 characters max · <span class="counter">62 / 90</span></span></div>
</section>
<fieldset class="form-section">
<legend class="field-legend" style="padding:0;float:left;width:100%;margin-bottom:14px"><span class="step-line"><span class="cintillo">02</span><span style="font-family:var(--font-title);font-size:25px;font-weight:700">Type</span></span></legend>
<div class="choice-grid">
<label class="choice"><input type="radio" name="type" value="shipped"><div><strong>Shipped</strong><span>A product or feature you can use today.</span></div></label>
<label class="choice choice-on"><input type="radio" name="type" value="weights" checked><div><strong>Open weights</strong><span>Downloadable weights with a stated licence.</span></div></label>
<label class="choice"><input type="radio" name="type" value="decisions"><div><strong>Decisions in the wild</strong><span>A model making real decisions about real people, on the record.</span></div></label>
</div>
</fieldset>
<section class="form-section" aria-labelledby="tags-h">
<div class="step-line"><span class="cintillo">03</span><h2 id="tags-h">Topics and entities</h2></div>
<p class="field-hint" style="margin:0">We read the link and pulled these out for the knowledge graph. Confirm, fix or remove them. Solid outline with “confirmed” is a known entity; dashed with “proposed” would be a new one. <span class="sample-mark" title="Fictional sample data that previews the design">Sample</span></p>
<div class="tag-table">
<div class="tag-row"><span class="kicker">Beat</span><span class="tag-chips"><span class="entity-chip entity-chip-confirmed"><i>confirmed</i>Document AI</span></span><button type="button" class="button button-quiet mini-button">Change</button></div>
<div class="tag-row"><span class="kicker">Maker</span><span class="tag-chips"><span class="entity-chip entity-chip-confirmed"><i>confirmed</i>Kiln AI</span></span><button type="button" class="button button-quiet mini-button">Fix</button></div>
<div class="tag-row"><span class="kicker">Task</span><span class="tag-chips"><span class="entity-chip entity-chip-confirmed"><i>confirmed</i>structured extraction</span><span class="entity-chip entity-chip-confirmed"><i>confirmed</i>invoice extraction</span></span><button type="button" class="button button-quiet mini-button">Fix</button></div>
<div class="tag-row"><span class="kicker">Technique</span><span class="tag-chips"><span class="entity-chip entity-chip-proposed"><i>proposed</i>schema-constrained decoding</span></span><button type="button" class="button button-quiet mini-button">Fix</button></div>
<div class="tag-row"><span class="kicker">Licence</span><span class="tag-chips"><span class="entity-chip entity-chip-confirmed"><i>confirmed</i>MIT</span></span><button type="button" class="button button-quiet mini-button">Fix</button></div>
</div>
<div class="field"><label for="addtag">Add a topic</label><input id="addtag" class="field-input" type="text" placeholder="Search topics and the wiki"></div>
</section>
<section class="form-section" aria-labelledby="evidence-h">
<div class="step-line"><span class="cintillo">04</span><h2 id="evidence-h">Primary evidence</h2></div>
<p class="field-hint" style="margin:0">Each link should let a stranger check one claim. Editors check these before anything is stamped Verified.</p>
<div class="evidence-row"><div class="field"><label for="ev1-type">Type</label><select id="ev1-type" class="field-input"><option>Weights</option></select></div><div class="field"><label for="ev1-url">URL</label><input id="ev1-url" class="field-input field-input-mono" type="url" value="https://hub.example/kiln-ai/kiln-3b/tree/main"></div><button type="button" class="button button-quiet icon-button" aria-label="Remove evidence link 1"><svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8"/></svg></button></div>
<div class="evidence-row"><div class="field"><label for="ev2-type">Type</label><select id="ev2-type" class="field-input"><option>Licence</option></select></div><div class="field"><label for="ev2-url">URL</label><input id="ev2-url" class="field-input field-input-mono" type="url" value="https://hub.example/kiln-ai/kiln-3b/blob/main/LICENSE"></div><button type="button" class="button button-quiet icon-button" aria-label="Remove evidence link 2"><svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8"/></svg></button></div>
<div class="evidence-row"><div class="field"><label for="ev3-type">Type</label><select id="ev3-type" class="field-input"><option>Choose…</option><option>Weights</option><option>Licence</option><option>Code</option><option>Eval</option><option>Data</option><option>Docs / API</option><option>Public record</option></select></div><div class="field"><label for="ev3-url">URL</label><input id="ev3-url" class="field-input field-input-mono" type="url" placeholder="https://"></div><span></span></div>
<button type="button" class="button button-quiet" style="align-self:flex-start">Add another link</button>
</section>
<section class="form-section" aria-labelledby="checked-h">
<div class="step-line"><span class="cintillo">05</span><h2 id="checked-h">What you checked</h2></div>
<div class="field"><label for="checked">How do you know it works?</label><textarea id="checked" class="field-input" rows="5" aria-describedby="checked-hint">Pulled the weights and ran the extraction example from the README against 50 of our own invoices on a laptop CPU. Field-level output matched the schema on 47; the misses were all handwritten totals.</textarea><span id="checked-hint" class="field-hint">What you ran, on what, and what happened. “Looks promising” is not a check.</span></div>
<fieldset class="form-section" style="gap:10px">
<legend class="field-legend" style="padding:0;margin-bottom:4px">Disclosure</legend>
<label class="choice choice-on"><input type="radio" name="disclosure" value="none" checked><div><strong>No connection to the maker</strong></div></label>
<label class="choice"><input type="radio" name="disclosure" value="connected"><div><strong>I work for, invest in, or am paid by the maker</strong><span>Fine, but it is shown on the item.</span></div></label>
</fieldset>
</section>
<div class="submit-bar">
<button type="submit" class="button" disabled aria-disabled="true">Submit for checking (not open yet)</button>
<button type="button" class="button button-quiet">Save draft</button>
<span class="field-hint">New items start as <span class="status-stamp status-stamp-pending"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="8" cy="8" r="5.8"/><path d="M8 4.8V8l2.2 1.4"/></svg><span class="status-stamp-label">Pending</span></span></span>
</div>
</fieldset>
</div>
<aside class="form-side">
<section class="rail" aria-labelledby="account-h">
<h2 id="account-h" class="rail-h">Your account</h2> <span class="sample-mark" title="Fictional sample data that previews the design">Sample</span>
<div class="account-panel"><span class="account-figure">14 submissions</span><span>Karma: shown only once it is a defined number. For now: submission count and account age (9 months).</span><span class="field-hint">Signed in as a sample reader, “ryan-sample”.</span></div>
</section>
<section class="rail" aria-labelledby="counts-h">
<h2 id="counts-h" class="rail-h">What counts</h2>
<ul class="rail-points">
<li>A product or feature a stranger can use today, at a price on the page.</li>
<li>Weights you can download, with the licence stated where the weights are.</li>
<li>A model making decisions about people, with a public record: a policy, a filing, an audit, published outcomes.</li>
</ul>
</section>
<section class="rail" aria-labelledby="stamps-h">
<h2 id="stamps-h" class="rail-h">How it gets stamped</h2>
<dl class="rail-stamps">
<div><dt><span class="status-stamp status-stamp-pending"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="8" cy="8" r="5.8"/><path d="M8 4.8V8l2.2 1.4"/></svg><span class="status-stamp-label">Pending</span></span></dt><dd>Every submission, until someone other than you confirms it.</dd></div>
<div><dt><span class="status-stamp status-stamp-shipped"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M2.5 2.5h11v11h-11z"/><path d="M5 8.2l2 2 4-4.4"/></svg><span class="status-stamp-label">Shipped</span></span></dt><dd>An editor confirmed it, or 3 signed-in readers reported using it.</dd></div>
<div><dt><span class="status-stamp status-stamp-verified"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="8" cy="8" r="5.8"/><path d="M5.4 8.1l1.8 1.8 3.4-3.7"/></svg><span class="status-stamp-label">Verified</span></span></dt><dd>An editor has checked the primary evidence against the claim.</dd></div>
<div><dt><span class="status-stamp status-stamp-vapor"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><circle cx="8" cy="8" r="5"/><path d="M3 13L13 3"/></svg><span class="status-stamp-label">Vapor</span></span></dt><dd>Waitlists, demo videos, “coming soon”, private betas. It stays listed so the claim is on the record.</dd></div>
</dl>
</section>
</aside>
</div>
</div>
::endraw

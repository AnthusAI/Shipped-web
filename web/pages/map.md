::band{size="bare"}

::raw
<div class="shipped-page map-page">
<header class="map-header">
<div class="map-header-main">
<h1>The map</h1>
<p class="map-subtitle">How the field is taking shape</p>
</div>
::endraw

::include{kind="block" name="map-header" depends="*"}

::raw
</header>
<div class="map-views">
<input class="map-view-input" type="radio" name="map-view" id="map-view-table" checked>
<input class="map-view-input" type="radio" name="map-view" id="map-view-graph">
<input class="map-view-input" type="radio" name="map-view" id="map-view-river">
<div class="map-tablist" role="group" aria-label="Map views">
<label for="map-view-table">Table</label>
<label for="map-view-graph">Graph</label>
<label for="map-view-river">River</label>
</div>
<p class="map-tab-intro">Table: every model we track. Graph: how concepts connect. River: how clusters change week to week.</p>
<div class="map-panels">
<section class="map-panel map-panel-table" aria-labelledby="map-table-heading">
<div class="section-heading"><span class="cintillo">Table</span><h2 id="map-table-heading">The periodic table of what is in the wild</h2></div>
<p class="map-panel-dek">Every model we track, as an element. Columns are what it does; rows are how big it is. Where a cell is empty, nothing we track has shipped there yet.</p>
::endraw

::include{kind="block" name="periodic-table" depends="*"}

::raw
</section>
<section class="map-panel map-panel-graph" aria-labelledby="map-graph-heading">
<div class="section-heading"><span class="cintillo">Graph</span><h2 id="map-graph-heading">Concept graph</h2></div>
<p class="map-panel-dek">Concepts, makers and models are nodes; the lines are how the knowledge base says they relate.</p>
::endraw

::include{kind="block" name="map-graph" depends="*"}

::raw
</section>
<section class="map-panel map-panel-river" aria-label="River">
::endraw

::include{kind="block" name="map-river" depends="*"}

::raw
</section>
</div>
</div>
</div>
<script>
(function () {
  var views = ["table", "graph", "river"];
  function select(name) {
    var input = document.getElementById("map-view-" + name);
    if (input) { input.checked = true; }
  }
  var wanted = window.location.hash.replace("#", "");
  if (views.indexOf(wanted) > 0) { select(wanted); }
  views.forEach(function (name) {
    var input = document.getElementById("map-view-" + name);
    if (input) {
      input.addEventListener("change", function () {
        if (window.history && window.history.replaceState) {
          window.history.replaceState(null, "", name === "table" ? window.location.pathname : "#" + name);
        }
      });
    }
  });
})();
</script>
::endraw

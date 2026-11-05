import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIRECTORY = REPOSITORY_ROOT / "web"
MAP_CONTENT_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "map-content"
MAP_KNOWLEDGE_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "map-knowledge"
PLAIN_CONTENT_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "content"
PLAIN_KNOWLEDGE_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "knowledge"
MODEL_FIXTURE_COUNT = 15


def _papyrus_executable():
    beside_interpreter = Path(sys.executable).parent / "papyrus"
    if beside_interpreter.exists():
        return str(beside_interpreter)
    return shutil.which("papyrus") or "papyrus"


def _project(content_directory, knowledge_directory):
    output_directory = Path(tempfile.mkdtemp(prefix="shipped-map-"))
    result = subprocess.run(
        [
            _papyrus_executable(), "ops", "content", "project", "--all",
            "--from-dir", str(content_directory),
            "--static-dir", str(STATIC_DIRECTORY),
            "--knowledge-dir", str(knowledge_directory),
            "--out", str(output_directory),
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return output_directory


@unittest.skipUnless(
    (Path(sys.executable).parent / "papyrus").exists() or shutil.which("papyrus"),
    "the papyrus command from papyrus-newsroom is not installed",
)
class MapPageWithModelsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output_directory = _project(MAP_CONTENT_DIRECTORY, MAP_KNOWLEDGE_DIRECTORY)
        cls.page = (cls.output_directory / "map" / "index.html").read_text(encoding="utf-8")
        cls.table = cls.page.split('<table class="map-table">')[1].split("</table>")[0]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.output_directory, ignore_errors=True)

    def test_page_has_title_subtitle_and_three_tabs_with_table_first_and_selected(self):
        self.assertIn("<h1>The map</h1>", self.page)
        self.assertIn("How the field is taking shape", self.page)
        tabs = re.findall(r'<label for="map-view-(\w+)">(\w+)</label>', self.page)
        self.assertEqual(tabs, [("table", "Table"), ("graph", "Graph"), ("river", "River")])
        self.assertRegex(self.page, r'id="map-view-table" checked')
        self.assertIn("Table: every model we track. Graph: how concepts connect. River: how clusters change week to week.", self.page)

    def test_columns_are_the_seven_stable_groups_in_order_with_definitions(self):
        heads = re.findall(r'<th scope="col" class="map-group-head">.*?<b>(.*?)</b><span class="map-group-definition">(.*?)</span>', self.table)
        self.assertEqual([label for label, _ in heads], ["Decide", "Route", "Guard &amp; judge", "Speak", "Language", "Code", "See"])
        self.assertEqual(heads[0][1], "Models whose job is a judgement, not prose")
        self.assertEqual(heads[2][1], "Safety classifiers and judges")

    def test_rows_are_size_bands_then_size_not_stated_then_hosted(self):
        rows = re.findall(r'<th scope="row" class="map-row-head">.*?<b>(.*?)</b>', self.table)
        self.assertEqual(rows, ["&lt;1B", "1–10B", "10–50B", "50–300B", "300B+", "Size not stated", "Hosted"])

    def test_items_without_a_model_block_are_left_out(self):
        self.assertEqual(len(re.findall(r'<a class="map-tile ', self.table)), MODEL_FIXTURE_COUNT)
        self.assertNotIn("no model block", self.table)

    def test_a_crowded_cell_shows_four_tiles_then_a_more_tile_that_expands_in_place(self):
        crowded = re.search(r'<div class="map-cell-tiles">((?:(?!</td>).)*?<details class="map-more">.*?</details>)</div>', self.table, re.S)
        self.assertIsNotNone(crowded)
        before_details = crowded.group(1).split("<details")[0]
        self.assertEqual(before_details.count('<a class="map-tile '), 4)
        self.assertIn("+1 more", crowded.group(1))
        self.assertEqual(crowded.group(1).count('<a class="map-tile '), 5)

    def test_empty_cells_say_nothing_we_track_yet_and_never_a_prediction(self):
        self.assertIn('<span class="map-gap">Nothing we track yet</span>', self.table)
        self.assertNotIn("prediction", self.page.lower())

    def test_tile_shows_symbol_name_date_and_mass(self):
        tile = re.search(r'<a class="map-tile map-licence-open" href="[^"]*quillon-decide/"[^>]*>.*?</a>', self.table).group(0)
        for text in (">Qd<", "Quillon Decide 27B", "1 Oct", "27B"):
            self.assertIn(text, tile)
        self.assertIn("Apache-2.0 licence", tile)

    def test_mixture_of_experts_shows_total_and_active_and_a_range_shows_the_range(self):
        self.assertIn("230B / 17B active", self.table)
        self.assertIn("0.8–27B", self.table)

    def test_built_on_shows_on_the_symbol_of_the_model_it_is_built_on(self):
        tile = re.search(r'<a class="map-tile [^"]*" href="[^"]*tarn-decide/"[^>]*>.*?</a>', self.table).group(0)
        self.assertIn('<span class="map-tile-foot">on Qd</span>', tile)
        self.assertIn("built on Quillon Decide 27B", tile)

    def test_licence_is_shown_by_border_class(self):
        self.assertRegex(self.table, r'map-licence-open" href="[^"]*pellet-decide/')
        self.assertRegex(self.table, r'map-licence-restricted" href="[^"]*tarn-decide/')
        self.assertRegex(self.table, r'map-licence-unstated" href="[^"]*marrow-decide/')

    def test_hosted_models_sit_in_their_own_row_below_the_table(self):
        hosted = self.table.split('<tbody class="map-hosted">')[1]
        self.assertEqual(len(re.findall(r'<a class="map-tile ', hosted)), 2)
        self.assertIn("Off the table", hosted)
        self.assertEqual(len(re.findall(r'<a class="map-tile ', self.table.split('<tbody class="map-hosted">')[0])), MODEL_FIXTURE_COUNT - 2)

    def test_a_model_without_a_size_goes_to_the_size_not_stated_row(self):
        unstated_row = re.search(r'<b>Size not stated</b>.*?</tr>', self.table, re.S).group(0)
        self.assertIn("Rook Coder", unstated_row)

    def test_every_tile_is_a_link_to_its_signal_page(self):
        for href in re.findall(r'<a class="map-tile [^"]*" href="([^"]*)"', self.table):
            self.assertTrue((self.output_directory / href.strip("/") / "index.html").exists(), href)

    def test_symbols_are_two_letters_and_unique(self):
        symbols = re.findall(r'<span class="map-tile-symbol">([^<]*)</span>', self.table)
        self.assertEqual(len(symbols), len(set(symbols)))
        for symbol in symbols:
            self.assertRegex(symbol, r"^[A-Z][a-z]$")

    def test_legend_and_footer_notes(self):
        self.assertIn("How to read a tile", self.page)
        self.assertIn("Rows: total parameters. Mixture-of-experts shows total / active.", self.page)
        self.assertIn("two letters, unique across the table, and stable once assigned", self.page)
        self.assertIn("Why a periodic table", self.page)
        self.assertRegex(self.page, r"Edited by AI on \d+ \w+ 2026")

    def test_table_is_a_real_table_with_pinned_headers_in_its_own_scroll_box(self):
        self.assertIn('<div class="map-table-scroll" tabindex="0" role="region"', self.page)
        self.assertIn("position:sticky", (STATIC_DIRECTORY / "assets" / "shipped-map.css").read_text(encoding="utf-8"))

    def test_status_is_a_mark_and_a_word_never_colour_alone(self):
        self.assertIn("Verified", self.table)
        self.assertRegex(self.table, r'class="map-tile-status"[^>]*aria-hidden="true"')
        self.assertIn(", Announced,", self.table)

    def test_graph_view_groups_neighbours_by_relation_with_line_glyphs(self):
        graph = self.page.split("map-graph-layout")[1]
        for relation in ("mentioned with", "made by", "built on"):
            self.assertIn(f"<span>{relation}</span>", graph)
        self.assertIn('class="map-line-glyph"', graph)
        self.assertIn("Weight is the number of signals that link both ends.", graph)

    def test_graph_view_lists_what_is_new_on_the_map_from_the_knowledge_data(self):
        self.assertIn("New on the map this week", self.page)
        self.assertIn("fixture concept", self.page.split('class="map-new"')[1])

    def test_river_view_is_drawn_from_the_cluster_history_in_the_knowledge_snapshot(self):
        self.assertNotIn("first build", self.page)
        self.assertNotIn("map-river-sample", self.page)
        river = self.page.split('<section class="map-river"')[1].split("</section>")[0]
        self.assertIn("2 weeks of history", river)
        self.assertIn("Week of 26 Oct", river)
        for label in ("Agent tooling", "Speech synthesis", "Other clusters"):
            self.assertIn(label, river)
        self.assertNotIn('class="placeholder-tag"', river)
        self.assertNotIn('type="range"', self.page)

    def test_the_map_page_uses_the_agreed_vocabulary(self):
        lowered = self.page.lower()
        for word in ("vapor", "hype", "desk"):
            self.assertNotIn(word, re.sub(r"<[^>]+>", " ", lowered).replace("desktop", ""))


@unittest.skipUnless(
    (Path(sys.executable).parent / "papyrus").exists() or shutil.which("papyrus"),
    "the papyrus command from papyrus-newsroom is not installed",
)
class MapPageWithoutModelsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output_directory = _project(PLAIN_CONTENT_DIRECTORY, PLAIN_KNOWLEDGE_DIRECTORY)
        cls.page = (cls.output_directory / "map" / "index.html").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.output_directory, ignore_errors=True)

    def test_empty_state_explains_how_the_table_fills_in(self):
        self.assertIn("The table fills in as signals are tagged with their model details.", self.page)
        self.assertNotIn('<table class="map-table">', self.page)

    def test_empty_state_still_defines_the_seven_groups(self):
        for label in ("Decide", "Route", "Guard", "Speak", "Language", "Code", "See"):
            self.assertIn(f"<dt>{label}", self.page.replace("&amp;", "&"))

    def test_graph_view_without_entity_files_says_so_plainly(self):
        self.assertIn("No concept has recorded connections yet.", self.page)

    def test_river_view_without_cluster_history_shows_the_sample_as_a_placeholder(self):
        sample = self.page.split('class="map-river-sample is-placeholder"')[1].split("</section>")[0]
        self.assertEqual(sample.count('class="placeholder-tag"'), 1)
        self.assertIn("not real data", sample)


if __name__ == "__main__":
    unittest.main()


class MapLicenceStyleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.util

        hooks_path = Path(__file__).resolve().parent.parent / "web" / "hooks.py"
        specification = importlib.util.spec_from_file_location("shipped_hooks_for_licence_styles", hooks_path)
        cls.hooks = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(cls.hooks)

    def test_a_stated_licence_that_is_neither_open_nor_restricted_is_custom(self):
        for licence in ("Llama 4 Community License", "lfm1.0", "Modified MIT"):
            self.assertEqual(self.hooks._map_licence_style(licence), "custom", licence)

    def test_a_missing_licence_is_unstated_and_known_licences_keep_their_styles(self):
        self.assertEqual(self.hooks._map_licence_style(None), "unstated")
        self.assertEqual(self.hooks._map_licence_style(""), "unstated")
        self.assertEqual(self.hooks._map_licence_style("Apache-2.0"), "open")

    def test_the_tile_label_names_a_custom_licence(self):
        self.assertEqual(self.hooks._map_licence_phrase("lfm1.0", "custom"), "custom licence: lfm1.0")

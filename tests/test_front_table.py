import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIRECTORY = REPOSITORY_ROOT / "web"
MAP_CONTENT_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "map-content"
MAP_KNOWLEDGE_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "map-knowledge"
PLAIN_CONTENT_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "content"
PLAIN_KNOWLEDGE_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "knowledge"


def _papyrus_executable():
    beside_interpreter = Path(sys.executable).parent / "papyrus"
    if beside_interpreter.exists():
        return str(beside_interpreter)
    return shutil.which("papyrus") or "papyrus"


def _project(content_directory, knowledge_directory):
    output_directory = Path(tempfile.mkdtemp(prefix="shipped-front-table-"))
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


def _load_hooks():
    specification = importlib.util.spec_from_file_location("shipped_hooks_for_front_table", STATIC_DIRECTORY / "hooks.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _model(slug, symbol, group, total, released, hosted=False):
    return {
        "slug": slug, "name": slug.title(), "symbol": symbol, "group": group, "total": total, "active": None,
        "range": None, "hosted": hosted, "sort_date": released, "url": f"/open-weights/{slug}/",
    }


class FrontTableMarkupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hooks = _load_hooks()
        cls.reference_date = date(2026, 10, 22)
        cls.models = [
            _model("fresh", "Fr", "decide", 8, "2026-10-20"),
            _model("edge", "Ed", "route", 8, "2026-10-16"),
            _model("stale", "St", "route", 8, "2026-10-15"),
            _model("future", "Fu", "code", 8, "2026-10-23"),
            _model("cloud", "Cl", "speak", None, "2026-10-22", hosted=True),
        ]
        cls.markup = cls.hooks._front_table_markup(cls.models, cls.reference_date)

    def test_header_counts_all_models_and_those_new_this_week(self):
        self.assertIn("<b>5</b> models on the table &middot; <b>3</b> new this week", self.markup)

    def test_a_model_is_new_for_seven_days_counting_the_release_day(self):
        self.assertIn("new this week", self.markup)
        new_symbols = re.findall(r'front-table-symbol front-table-symbol-new" href="[^"]*/([a-z]+)/"', self.markup)
        self.assertEqual(sorted(new_symbols), ["cloud", "edge", "fresh"])

    def test_a_release_dated_after_the_reference_date_is_not_new(self):
        self.assertNotIn("future/\" title=\"Future, symbol Fu, Code, new", self.markup)

    def test_new_is_marked_by_class_dot_and_words_never_colour_alone(self):
        self.assertIn("front-table-symbol-new", self.markup)
        self.assertIn(", new this week\"", self.markup)
        self.assertIn("Heavy border and dot: new this week", self.markup)

    def test_columns_are_the_seven_groups_and_rows_are_bands_then_hosted(self):
        heads = re.findall(r'<th scope="col" class="front-table-group">(.*?)</th>', self.markup)
        self.assertEqual(heads, ["Decide", "Route", "Guard", "Speak", "Lang", "Code", "See"])
        rows = re.findall(r'<th scope="row" class="front-table-band">(.*?)</th>', self.markup)
        self.assertEqual(rows, ["&lt;1B", "1–10B", "10–50B", "50–300B", "300B+", "Not stated", "Hosted"])

    def test_cells_show_only_symbols_and_empty_cells_are_blank(self):
        self.assertIn(">Fr</a>", self.markup)
        self.assertNotIn("Fresh</a>", self.markup)
        self.assertIn('<td class="front-table-cell"></td>', self.markup)

    def test_the_reference_date_defaults_to_today_and_can_be_set_by_attribute(self):
        self.assertEqual(self.hooks._front_table_reference_date({"today": "2026-10-22"}), date(2026, 10, 22))
        self.assertEqual(self.hooks._front_table_reference_date({}), date.today())


@unittest.skipUnless(
    (Path(sys.executable).parent / "papyrus").exists() or shutil.which("papyrus"),
    "the papyrus command from papyrus-newsroom is not installed",
)
class FrontPageProjectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map_output = _project(MAP_CONTENT_DIRECTORY, MAP_KNOWLEDGE_DIRECTORY)
        cls.plain_output = _project(PLAIN_CONTENT_DIRECTORY, PLAIN_KNOWLEDGE_DIRECTORY)
        cls.home = (cls.map_output / "index.html").read_text(encoding="utf-8")
        cls.plain_home = (cls.plain_output / "index.html").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.map_output, ignore_errors=True)
        shutil.rmtree(cls.plain_output, ignore_errors=True)

    def test_home_shows_the_compact_table_with_a_count_header_and_a_link_to_the_map(self):
        section = self.home.split('<section class="front-table-entry"')[1].split("</section>")[0]
        self.assertRegex(section, r"<b>15</b> models on the table &middot; <b>\d+</b> new this week")
        self.assertIn('<a class="front-link" href="/map/">Open the map &rarr;</a>', section)
        self.assertEqual(len(re.findall(r'<a class="front-table-symbol', section)), 15)

    def test_the_table_section_is_no_longer_a_placeholder(self):
        self.assertNotIn("front-table-entry is-placeholder", self.home)
        self.assertNotIn("Open the map</a>", self.home.split('id="front-table-h"')[1].split("</section>")[0])

    def test_without_model_details_the_table_says_how_it_fills_in(self):
        section = self.plain_home.split('<section class="front-table-entry"')[1].split("</section>")[0]
        self.assertIn("The table fills in as signals are tagged with their model details.", section)

    def test_home_shows_what_changed_in_the_clusters_since_the_previous_week(self):
        self.assertIn("Since the week of 19 Oct", self.home)
        panel = self.home.split("Since the week of 19 Oct")[1].split("</section>")[0]
        self.assertIn("Agent tooling from Agents and Code models", panel)
        self.assertIn("Voice into Voice cloning and Speech synthesis", panel)

    def test_home_without_cluster_history_has_no_changes_panel(self):
        self.assertNotIn("Since the week of", self.plain_home)

    def test_home_invitation_is_live_and_not_marked_as_a_placeholder(self):
        invitation = self.home.split('<div class="front-invite">')[1].split("</div>")[0]
        self.assertIn("Readers vote on what goes on this map. Sign in to vote, rate and say what you", invitation)
        self.assertIn("rate and say what you", invitation)
        self.assertNotIn("is-placeholder", invitation)
        self.assertNotIn("vote on drafts", invitation)
        self.assertIn("You are signed in. Vote, rate and say what you", invitation)
        self.assertIn('data-island="ReaderSignIn"', invitation)

    def test_concept_pages_carry_the_same_live_invitation_without_a_placeholder(self):
        for path in ("topics/decision-models", "topics/open-tts"):
            page = self.plain_output / path / "index.html"
            if not page.exists():
                continue
            text = page.read_text(encoding="utf-8")
            invitation = text.split('<div class="concept-invite')[1].split("</div>")[0]
            self.assertTrue(invitation.startswith('">'), path)
            self.assertIn("Sign in to vote, rate and say what you", invitation)
            self.assertNotIn("vote on drafts", invitation)

    def test_the_proposals_page_keeps_voting_on_drafts_wording(self):
        text = (self.plain_output / "proposals" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Sign in to vote on drafts.", text)


if __name__ == "__main__":
    unittest.main()

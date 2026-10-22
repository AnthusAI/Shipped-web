import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "content"
STATIC_DIRECTORY = REPOSITORY_ROOT / "web"


def _papyrus_executable():
    beside_interpreter = Path(sys.executable).parent / "papyrus"
    if beside_interpreter.exists():
        return str(beside_interpreter)
    return shutil.which("papyrus") or "papyrus"


@unittest.skipUnless(
    (Path(sys.executable).parent / "papyrus").exists() or shutil.which("papyrus"),
    "the papyrus command from papyrus-newsroom is not installed",
)
class HooksProjectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output_directory = Path(tempfile.mkdtemp(prefix="shipped-hooks-"))
        result = subprocess.run(
            [
                _papyrus_executable(), "ops", "content", "project", "--all",
                "--from-dir", str(FIXTURE_DIRECTORY),
                "--static-dir", str(STATIC_DIRECTORY),
                "--out", str(cls.output_directory),
            ],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise AssertionError(result.stdout + result.stderr)
        cls.projection_log = result.stdout + result.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.output_directory, ignore_errors=True)

    def _page(self, relative_path):
        return (self.output_directory / relative_path / "index.html").read_text(encoding="utf-8")

    def test_item_page_has_stamp_and_evidence_check_words(self):
        page = self._page("open-weights/fixture-full-contract")
        self.assertIn("status-stamp-verified", page)
        self.assertIn(">Verified<", page)
        self.assertIn("Checked by the fixture desk", page)
        self.assertIn("Partly", page)
        self.assertIn("Not checked", page)
        self.assertIn("Editor score", page)
        self.assertNotIn("scoring-provenance", page)
        self.assertIn("hype-gap", page)

    def test_item_page_renders_source_release_date_score_notes_and_topic_link(self):
        page = self._page("decisions/fixture-guard-one")
        self.assertIn('class="source-link" href="https://source.fixture.example/guard-one" rel="noopener"', page)
        self.assertIn("Source: source.fixture.example", page)
        self.assertIn("Released 18 Oct 2026", page)
        self.assertIn('<span class="score-note">Fixture note on novel.</span>', page)
        self.assertIn('href="/topics/decision-models/">Topic: Decision models', page)

    def test_item_page_without_notes_has_no_score_note_for_missing_dimensions(self):
        page = self._page("decisions/fixture-router-two")
        self.assertNotIn("score-note", page)

    def test_home_page_has_one_real_board_with_four_rows_and_no_sample_board(self):
        page = self._page(".")
        self.assertIn("Latest from the desk", page)
        self.assertNotIn("Shipped this week", page)
        self.assertEqual(len(re.findall(r'<li class="board-row">', page.split('class="board desk-board"')[1].split("</ol>")[0])), 4)
        self.assertIn("Ratings open with reader sign-in", page)
        self.assertIn('href="/topics/decision-models/">Decision models', page)
        self.assertIn('href="/topics/open-tts/">Open TTS', page)
        self.assertNotIn("Sample", page)
        self.assertIn("placeholder-tag", page)
        self.assertIn("Dimmed sections with a dashed outline are placeholders", page)
        self.assertIn('<a href="/topics/decision-models/">Decision models</a>', page)
        self.assertIn("Scores on seeded items are an AI-assisted first pass", page)

    def test_new_page_has_only_the_real_board_newest_first(self):
        page = self._page("new")
        self.assertNotIn("New this week", page)
        board = page.split('class="board desk-board"')[1].split("</ol>")[0]
        self.assertLess(board.index("fixture-full-contract"), board.index("fixture-router-two"))
        self.assertLess(board.index("fixture-router-two"), board.index("fixture-guard-one"))

    def test_vapor_and_rising_keep_their_placeholder_boards(self):
        self.assertIn("placeholder-tag", self._page("vapor"))
        self.assertIn('class="board is-placeholder"', self._page("vapor"))
        self.assertIn('class="board is-placeholder"', self._page("rising"))
        self.assertNotIn("sample-mark", self._page("rising"))

    def test_placeholder_pages_have_no_sample_marks(self):
        for relative_path in ("roundup", "submit", "sign-in", "sample/tern-3", "sample/voice-agents"):
            page = self._page(relative_path)
            self.assertNotIn("sample-mark", page)
            self.assertNotIn(">Sample<", page)
            self.assertIn("placeholder-tag", page)
            self.assertIn("is-placeholder", page)

    def test_agent_scored_item_page_shows_the_label_and_the_notice(self):
        page = self._page("decisions/fixture-guard-one")
        self.assertIn("Editor&#x27;s first pass (AI-assisted)", page)
        self.assertIn("Scored by an AI research pass from the linked sources; a human editor will re-score it.", page)

    def test_item_page_without_scoring_says_editor_score(self):
        page = self._page("decisions/fixture-router-two")
        self.assertIn('<p class="kicker">Editor score</p>', page)
        self.assertNotIn("scoring-provenance", page)
        self.assertNotIn("AI first pass", page)

    def test_board_rows_tag_only_agent_scored_items(self):
        page = self._page("topics/decision-models")
        self.assertEqual(page.count('<span class="ai-first-pass-tag">AI first pass</span>'), 1)
        self.assertEqual(self._page("topics/open-tts").count("ai-first-pass-tag"), 0)

    def test_maker_handle_is_shown_verbatim(self):
        with_both = self._page("decisions/fixture-router-two")
        self.assertIn('Other Fixture Lab (<span class="maker-handle">other-fixture-lab</span>)', with_both)
        handle_only = self._page("shipped/fixture-invalid-values")
        self.assertIn('<span class="kicker maker-display"><span class="maker-handle">handle-only-lab</span></span>', handle_only)

    def test_decision_models_topic_page_counts_and_profile(self):
        page = self._page("topics/decision-models")
        self.assertIn("<title>Decision models that actually shipped", page)
        self.assertNotIn("sample-mark", page)
        stats = re.findall(r"<dt>(\w+)</dt><dd>(\d+)</dd>", page)
        self.assertEqual(stats, [("Items", "2"), ("Makers", "2"), ("Shipped", "1"), ("Pending", "1")])
        self.assertIn("Editor scores (AI-assisted first pass), mean of 2 items", page)
        self.assertIn('<span class="profile-value">3.0</span>', page)
        self.assertIn("&#9650; +0.5 over", page)
        self.assertEqual(len(re.findall(r'<li class="board-row">', page)), 2)
        self.assertIn("Other Fixture Lab", page)
        self.assertNotIn("fixture-full-contract", page)

    def test_open_tts_topic_page_lists_only_its_own_tag(self):
        page = self._page("topics/open-tts")
        self.assertEqual(re.findall(r"<dt>(\w+)</dt><dd>(\d+)</dd>", page)[:2], [("Items", "1"), ("Makers", "1")])
        self.assertIn("Editor scores, mean of 1 items", page)
        self.assertIn("fixture-full-contract", page)
        self.assertNotIn("fixture-guard-one", page)

    def test_sitemap_and_markdown_twins_include_topic_pages(self):
        sitemap = (self.output_directory / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("/topics/decision-models/", sitemap)
        self.assertIn("/topics/open-tts/", sitemap)
        self.assertTrue((self.output_directory / "topics" / "decision-models" / "index.md").exists())
        self.assertTrue((self.output_directory / "topics" / "open-tts" / "index.md").exists())

    def test_invalid_values_are_not_rendered(self):
        page = self._page("shipped/fixture-invalid-values")
        self.assertNotIn("9.0", page)
        self.assertNotIn("bogus", page)
        self.assertNotIn("invalid.fixture.example", page)
        self.assertIn("status-stamp-pending", page)

    def test_invalid_values_log_a_warning_and_never_fail_the_build(self):
        self.assertIn("fixture-invalid-values", self.projection_log)


if __name__ == "__main__":
    unittest.main()

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
KNOWLEDGE_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "knowledge"
NEWEST_TITLE = "Fixture story: guard models now name their parents"
OLDER_TITLE = "Fixture story: open weights for fictional speech"
PENDING_MARKERS = ("PENDING-STORY-MUST-NOT-RENDER", "PENDING-STANDFIRST-MUST-NOT-RENDER", "PENDING-BODY-MUST-NOT-RENDER", "Pending Concept Name", "pending-proposal")
HOME_LEAD_PLACEHOLDER = "Decision models are starting to have family trees"
HOME_ALSO_PLACEHOLDER = "[Story headline]"
SECTION_LEAD_PLACEHOLDER = "The lead story for this section will appear here"


def _papyrus_executable():
    beside_interpreter = Path(sys.executable).parent / "papyrus"
    if beside_interpreter.exists():
        return str(beside_interpreter)
    return shutil.which("papyrus") or "papyrus"


def _project(content_directory):
    output_directory = Path(tempfile.mkdtemp(prefix="shipped-stories-"))
    result = subprocess.run(
        [
            _papyrus_executable(), "ops", "content", "project", "--all",
            "--from-dir", str(content_directory),
            "--static-dir", str(STATIC_DIRECTORY),
            "--knowledge-dir", str(KNOWLEDGE_DIRECTORY),
            "--out", str(output_directory),
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return output_directory


def _page(output_directory, relative_path):
    target = output_directory / relative_path / "index.html" if relative_path else output_directory / "index.html"
    return target.read_text(encoding="utf-8")


def _all_text(output_directory):
    return {
        path.relative_to(output_directory).as_posix(): path.read_text(encoding="utf-8")
        for path in output_directory.rglob("*")
        if path.is_file() and path.suffix in {".html", ".md", ".xml", ".txt", ".json"}
    }


@unittest.skipUnless(
    (Path(sys.executable).parent / "papyrus").exists() or shutil.which("papyrus"),
    "the papyrus command from papyrus-newsroom is not installed",
)
class StoriesProjectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output_directory = _project(FIXTURE_DIRECTORY)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.output_directory, ignore_errors=True)

    def test_a_pending_story_appears_on_no_page_listing_or_feed(self):
        self.assertFalse((self.output_directory / "stories" / "fixture-story-pending").exists())
        for path, text in _all_text(self.output_directory).items():
            for marker in PENDING_MARKERS:
                self.assertNotIn(marker, text, f"{marker!r} leaked into {path}")
            self.assertNotIn("fixture-story-pending", text, path)

    def test_approved_stories_have_pages_and_are_in_the_listing_and_the_feed(self):
        for slug in ("fixture-story-newest", "fixture-story-older"):
            self.assertTrue((self.output_directory / "stories" / slug / "index.html").exists())
        listing = _page(self.output_directory, "stories")
        feed = (self.output_directory / "feed.xml").read_text(encoding="utf-8")
        for title in (NEWEST_TITLE, OLDER_TITLE):
            self.assertIn(title, listing)
            self.assertIn(title, feed)

    def test_the_story_page_shows_headline_standfirst_and_provenance_from_real_data(self):
        page = _page(self.output_directory, "stories/fixture-story-newest")
        self.assertIn(f'<h1 id="story-h" class="story-title">{NEWEST_TITLE}</h1>', page)
        self.assertIn("Two fictional guard models say which weights they started from", page)
        self.assertIn("Drafted by AI", page)
        self.assertIn("Approved by <b>fixture-editor</b>", page)
        self.assertIn("22 Oct 2026", page)
        self.assertNotIn("readers steered it", page)

    def test_the_lineage_figure_is_drawn_from_the_pairs(self):
        page = _page(self.output_directory, "stories/fixture-story-newest")
        self.assertIn('class="story-figure"', page)
        self.assertEqual(page.count('class="story-lineage-row"'), 2)
        self.assertIn("<b>Fixture Guard One</b>", page)
        self.assertIn('story-node story-node-child"><b>Fixture Guard Two</b>', page)
        older = _page(self.output_directory, "stories/fixture-story-older")
        self.assertNotIn("story-figure", older)

    def test_citation_markers_link_to_the_signals_cited_list(self):
        page = _page(self.output_directory, "stories/fixture-story-newest")
        self.assertIn('<a href="#src-1" class="story-cite" aria-label="Source 1">1</a>', page)
        self.assertIn('<a href="#src-2" class="story-cite" aria-label="Source 2">2</a>', page)
        self.assertIn("plain text: [9]", page)
        self.assertIn('<li id="src-1">', page)
        self.assertIn('<li id="src-2">', page)
        self.assertIn("Signals cited", page)
        self.assertIn('href="https://source.fixture.example/guard-two"', page)

    def test_concept_chips_link_to_the_wiki_only_when_the_entity_resolves(self):
        page = _page(self.output_directory, "stories/fixture-story-newest")
        self.assertIn('<a class="entity-chip" href="/wiki/task-fixture-task/"><i>task</i>fixture task</a>', page)
        self.assertIn('<span class="entity-chip"><i>model</i>Fixture Guard Two</span>', page)

    def test_the_map_box_appears_only_when_the_story_proposes_something(self):
        page = _page(self.output_directory, "stories/fixture-story-newest")
        self.assertIn("What this changes on the map", page)
        self.assertIn("Proposal &middot; not yet approved", page)
        self.assertIn("guard-model lineage", page)
        older = _page(self.output_directory, "stories/fixture-story-older")
        self.assertNotIn("What this changes on the map", older)
        self.assertNotIn("not yet approved", older)

    def test_story_votes_are_the_real_vote_and_flag_islands_with_no_placeholder(self):
        page = _page(self.output_directory, "stories/fixture-story-newest")
        self.assertIn("Was this story right?", page)
        react = re.search(r'<section id="story-react".*?</section>', page, re.S).group(0)
        self.assertNotIn("is-placeholder", react)
        self.assertNotIn("placeholder-tag", react)
        self.assertNotIn("disabled", react)

    def test_the_home_lead_is_the_newest_approved_story_and_the_next_one_is_also_on_the_map(self):
        home = _page(self.output_directory, "")
        lead = re.search(r'<article class="front-lead".*?</article>', home, re.S).group(0)
        self.assertIn(NEWEST_TITLE, lead)
        self.assertNotIn(OLDER_TITLE, lead)
        self.assertIn("front-lead-figure", lead)
        self.assertIn("Fixture Guard One", lead)
        self.assertIn("Drafted by AI", lead)
        self.assertIn("Approved by <b>fixture-editor</b>", lead)
        self.assertIn('href="/wiki/task-fixture-task/"', lead)
        self.assertNotIn("is-placeholder", lead)
        also = re.search(r'<section class="front-stories".*?</section>', home, re.S).group(0)
        self.assertIn(OLDER_TITLE, also)
        self.assertNotIn(NEWEST_TITLE, also)
        self.assertNotIn("is-placeholder", also)
        self.assertNotIn(HOME_LEAD_PLACEHOLDER, home)
        self.assertNotIn(HOME_ALSO_PLACEHOLDER, home)

    def test_each_section_landing_leads_with_its_newest_approved_story_or_the_placeholder(self):
        decisions = _page(self.output_directory, "decisions")
        self.assertIn(NEWEST_TITLE, re.search(r'<article class="landing-lead".*?</article>', decisions, re.S).group(0))
        open_weights = _page(self.output_directory, "open-weights")
        self.assertIn(OLDER_TITLE, re.search(r'<article class="landing-lead".*?</article>', open_weights, re.S).group(0))
        shipped = _page(self.output_directory, "shipped")
        self.assertIn(SECTION_LEAD_PLACEHOLDER, shipped)
        self.assertIn("landing-lead is-placeholder", shipped)

    def test_stories_are_not_counted_as_signals_or_listed_on_the_signal_board(self):
        new_board = _page(self.output_directory, "new")
        self.assertNotIn(NEWEST_TITLE, new_board)
        self.assertNotIn(OLDER_TITLE, new_board)


@unittest.skipUnless(
    (Path(sys.executable).parent / "papyrus").exists() or shutil.which("papyrus"),
    "the papyrus command from papyrus-newsroom is not installed",
)
class StoriesFallbackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content_directory = Path(tempfile.mkdtemp(prefix="shipped-stories-content-"))
        shutil.copytree(FIXTURE_DIRECTORY, cls.content_directory, dirs_exist_ok=True)
        for approved in ("fixture-story-newest.md", "fixture-story-older.md"):
            (cls.content_directory / "stories" / approved).unlink()
        cls.output_directory = _project(cls.content_directory)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.output_directory, ignore_errors=True)
        shutil.rmtree(cls.content_directory, ignore_errors=True)

    def test_with_only_a_pending_story_the_home_placeholders_stay(self):
        home = _page(self.output_directory, "")
        self.assertIn('<article class="front-lead is-placeholder"', home)
        self.assertIn(HOME_LEAD_PLACEHOLDER, home)
        self.assertIn('<section class="front-stories is-placeholder"', home)
        self.assertIn(HOME_ALSO_PLACEHOLDER, home)

    def test_with_only_a_pending_story_every_section_landing_keeps_its_placeholder(self):
        for section in ("shipped", "open-weights", "decisions"):
            self.assertIn(SECTION_LEAD_PLACEHOLDER, _page(self.output_directory, section))

    def test_the_pending_story_still_appears_nowhere(self):
        for path, text in _all_text(self.output_directory).items():
            for marker in PENDING_MARKERS:
                self.assertNotIn(marker, text, f"{marker!r} leaked into {path}")


if __name__ == "__main__":
    unittest.main()


class StoryTimestampTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.util

        hooks_path = Path(__file__).resolve().parent.parent / "web" / "hooks.py"
        specification = importlib.util.spec_from_file_location("shipped_hooks_for_story_timestamps", hooks_path)
        cls.hooks = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(cls.hooks)

    def test_full_date_label_reads_dates_and_iso_datetimes(self):
        from datetime import datetime, timezone

        self.assertEqual(self.hooks._full_date_label("2026-10-22"), "22 Oct 2026")
        self.assertEqual(self.hooks._full_date_label("2026-10-22T23:50:00Z"), "22 Oct 2026")
        self.assertEqual(self.hooks._full_date_label("2026-10-22T23:50:00+00:00"), "22 Oct 2026")
        self.assertEqual(self.hooks._full_date_label(self.hooks._timestamp_text(datetime(2026, 10, 22, 23, 50, tzinfo=timezone.utc))), "22 Oct 2026")

    def test_approval_times_keep_second_precision_for_ordering(self):
        from datetime import datetime, timezone

        earlier = self.hooks._timestamp_text(datetime(2026, 10, 22, 23, 50, 0, tzinfo=timezone.utc))
        later = self.hooks._timestamp_text(datetime(2026, 10, 22, 23, 50, 1, tzinfo=timezone.utc))
        self.assertLess(earlier, later)
        self.assertEqual(self.hooks._timestamp_text("2026-10-22T23:50:01Z"), "2026-10-22T23:50:01Z")

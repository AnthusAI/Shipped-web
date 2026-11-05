import html
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "content"
STATIC_DIRECTORY = REPOSITORY_ROOT / "web"
KNOWLEDGE_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "knowledge"
NEWEST_TITLE = "Fixture story: guard models now name their parents"
OLDER_TITLE = "Fixture story: open weights for fictional speech"
PENDING_TITLE = "PENDING-STORY-MUST-NOT-RENDER"
GUARD_ONE_PATH = "/decisions/fixture-guard-one/"
FULL_CONTRACT_PATH = "/open-weights/fixture-full-contract/"


def _load_hooks():
    spec = importlib.util.spec_from_file_location("shipped_hooks_for_story_links", STATIC_DIRECTORY / "hooks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _papyrus_executable():
    beside_interpreter = Path(sys.executable).parent / "papyrus"
    if beside_interpreter.exists():
        return str(beside_interpreter)
    return shutil.which("papyrus") or "papyrus"


def _project():
    output_directory = Path(tempfile.mkdtemp(prefix="shipped-story-links-"))
    result = subprocess.run(
        [
            _papyrus_executable(), "ops", "content", "project", "--all",
            "--from-dir", str(FIXTURE_DIRECTORY),
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
    return (output_directory / relative_path / "index.html").read_text(encoding="utf-8")


def _section(page, heading_id):
    return re.search(rf'<section[^>]*aria-labelledby="{heading_id}".*?</section>', page, re.S)


def _fake_story_summary(slug, approved_at, cites, concepts, status="approved", approved_by="an-editor"):
    return SimpleNamespace(
        item_id=f"{slug}-id", type="article", section="stories", slug=slug, output_path=f"stories/{slug}/index.html",
        version_number=1, title=slug, page_title=slug, aliases=(), published_at=None,
        front_matter={
            "kind": "story", "title": slug, "concepts": concepts, "cites": cites,
            "approval": {"status": status, "by": approved_by, "at": approved_at},
        },
    )


def _fake_signal_summary(slug, tags):
    return SimpleNamespace(
        item_id=f"{slug}-id", type="article", section="decisions", slug=slug, output_path=f"decisions/{slug}/index.html",
        version_number=1, title=slug, page_title=slug, aliases=(), published_at=None,
        front_matter={"title": slug, "tags": tags, "verdict": "available"},
    )


class _FakeSite:
    def __init__(self, items):
        self.items = items
        self._memo = {}

    def memo(self, name, build):
        if name not in self._memo:
            self._memo[name] = build()
        return self._memo[name]


def _cite(number, url):
    return {"n": number, "title": f"Cite {number}", "url": url, "date": "2026-10-01"}


class CitationPathMatchingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hooks = _load_hooks()

    def test_an_absolute_page_url_becomes_the_signal_page_path(self):
        self.assertEqual(self.hooks._citation_page_path("https://shipped.anth.us/decisions/some-signal/"), "/decisions/some-signal/")

    def test_a_missing_trailing_slash_and_an_index_file_are_the_same_page(self):
        self.assertEqual(self.hooks._citation_page_path("https://shipped.anth.us/decisions/some-signal"), "/decisions/some-signal/")
        self.assertEqual(self.hooks._citation_page_path("https://shipped.anth.us/decisions/some-signal/index.html"), "/decisions/some-signal/")

    def test_the_query_and_fragment_do_not_change_the_path(self):
        self.assertEqual(self.hooks._citation_page_path("https://shipped.anth.us/decisions/some-signal/?ref=x#top"), "/decisions/some-signal/")

    def test_a_site_root_or_empty_url_matches_no_signal(self):
        self.assertIsNone(self.hooks._citation_page_path("https://shipped.anth.us/"))
        self.assertIsNone(self.hooks._citation_page_path(None))

    def test_a_signal_is_cited_only_by_the_approved_stories_whose_cite_path_equals_its_path(self):
        signal = _fake_signal_summary("target-signal", ["decision-models"])
        approved = _fake_story_summary("approved-story", "2026-10-22T09:00:00Z", [_cite(3, "https://shipped.anth.us/decisions/target-signal")], [])
        other_path = _fake_story_summary("other-path-story", "2026-10-21T09:00:00Z", [_cite(1, "https://shipped.anth.us/decisions/another-signal/")], [])
        pending = _fake_story_summary("pending-story", None, [_cite(1, "https://shipped.anth.us/decisions/target-signal/")], [], status="pending")
        site = _FakeSite([signal, approved, other_path, pending])
        html_text = self.hooks._stories_citing_signal_html(signal, site)
        self.assertIn('href="/stories/approved-story/"', html_text)
        self.assertIn("Cited as [3]", html_text)
        self.assertIn("Approved by <b>an-editor</b>", html_text)
        self.assertNotIn("other-path-story", html_text)
        self.assertNotIn("pending-story", html_text)

    def test_the_section_is_empty_when_no_approved_story_cites_the_signal(self):
        signal = _fake_signal_summary("lonely-signal", [])
        site = _FakeSite([signal, _fake_story_summary("story", "2026-10-22", [_cite(1, "https://example.org/elsewhere/")], [])])
        self.assertEqual(self.hooks._stories_citing_signal_html(signal, site), "")


class ConceptMatchingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hooks = _load_hooks()
        cls.signal = _fake_signal_summary("topic-signal", ["decision-models"])
        cls.by_name = _fake_story_summary("by-name", "2026-10-20", [], [{"kind": "topic", "name": "DECISION MODELS"}])
        cls.by_key = _fake_story_summary("by-key", "2026-10-19", [], [{"kind": "topic", "name": "decision-models"}])
        cls.by_cite = _fake_story_summary("by-cite", "2026-10-18", [_cite(1, "https://shipped.anth.us/decisions/topic-signal/")], [])
        cls.unrelated = _fake_story_summary("unrelated", "2026-10-17", [_cite(1, "https://shipped.anth.us/decisions/other/")], [{"kind": "model", "name": "Something Else"}])
        cls.pending = _fake_story_summary("pending", None, [], [{"kind": "topic", "name": "Decision models"}], status="pending")

    def _slugs(self, key="decision-models", label="Decision models", tag="decision-models"):
        site = _FakeSite([self.signal, self.by_name, self.by_key, self.by_cite, self.unrelated, self.pending])
        return [story["url"] for story in self.hooks._stories_for_topic(site, key, label, tag)]

    def test_a_story_matches_by_concept_name_ignoring_case_by_topic_key_or_by_citing_a_signal_in_the_topic(self):
        self.assertEqual(self._slugs(), ["/stories/by-name/", "/stories/by-key/", "/stories/by-cite/"])

    def test_a_pending_story_never_matches(self):
        self.assertNotIn("/stories/pending/", self._slugs())

    def test_a_topic_with_no_matching_story_renders_nothing(self):
        site = _FakeSite([self.signal, self.by_name])
        page = SimpleNamespace(site=site)
        self.assertEqual(self.hooks._concept_stories(page, {"key": "open-tts", "label": "Open TTS", "tag": "open-tts"}), "")


class StoryLinksProjectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output_directory = _project()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.output_directory, ignore_errors=True)

    def test_the_story_page_mounts_the_vote_and_flag_islands_for_the_story_subject(self):
        page = _page(self.output_directory, "stories/fixture-story-newest")
        react = _section(page, "story-react-h").group(0)
        islands = re.findall(r'data-island="(\w+)" data-props="([^"]*)"', react)
        self.assertEqual([name for name, _props in islands], ["Vote", "Flag"])
        subject_ids = set()
        for _name, props in islands:
            decoded = json.loads(html.unescape(props))
            self.assertEqual(decoded["type"], "story")
            self.assertEqual(set(decoded), {"type", "id"})
            subject_ids.add(decoded["id"])
        self.assertEqual(len(subject_ids), 1)
        self.assertEqual(subject_ids.pop(), "file:stories/fixture-story-newest.md")

    def test_each_story_votes_on_its_own_subject_id(self):
        def story_subject(slug):
            page = _page(self.output_directory, f"stories/{slug}")
            return json.loads(html.unescape(re.search(r'data-island="Vote" data-props="([^"]*)"', page).group(1)))["id"]

        self.assertNotEqual(story_subject("fixture-story-newest"), story_subject("fixture-story-older"))

    def test_a_cited_signal_page_lists_the_approved_story_with_its_citation_number_and_approval(self):
        page = _page(self.output_directory, GUARD_ONE_PATH.strip("/"))
        block = _section(page, "signal-stories-h").group(0)
        self.assertNotIn("is-placeholder", block)
        self.assertIn('<a class="signal-story-title" href="/stories/fixture-story-newest/">' + NEWEST_TITLE + "</a>", block)
        self.assertIn("Cited as [2]", block)
        self.assertIn("Approved by <b>fixture-editor</b>", block)
        self.assertIn("22 Oct 2026", block)
        self.assertNotIn(OLDER_TITLE, block)
        self.assertNotIn(PENDING_TITLE, page)

    def test_a_url_without_a_trailing_slash_still_finds_its_signal(self):
        block = _section(_page(self.output_directory, FULL_CONTRACT_PATH.strip("/")), "signal-stories-h").group(0)
        self.assertIn(OLDER_TITLE, block)
        self.assertIn("Cited as [2]", block)

    def test_a_signal_no_story_cites_has_no_stories_section_and_no_placeholder(self):
        page = _page(self.output_directory, "decisions/fixture-router-two")
        self.assertNotIn("signal-stories-h", page)
        self.assertNotIn("Appears in these stories", page)
        self.assertNotIn("Stories that cite this signal will be listed here", page)

    def test_a_topic_page_lists_its_approved_stories_by_citation_and_by_concept(self):
        decision_models = _section(_page(self.output_directory, "topics/decision-models"), "stories-h").group(0)
        self.assertIn("Stories that cite it", decision_models)
        self.assertIn(NEWEST_TITLE, decision_models)
        self.assertNotIn(OLDER_TITLE, decision_models)
        self.assertNotIn("is-placeholder", decision_models)
        open_tts = _section(_page(self.output_directory, "topics/open-tts"), "stories-h").group(0)
        self.assertIn(OLDER_TITLE, open_tts)
        self.assertNotIn(NEWEST_TITLE, open_tts)

    def test_the_pending_story_is_listed_nowhere(self):
        for path in (GUARD_ONE_PATH, FULL_CONTRACT_PATH, "/topics/decision-models/", "/topics/open-tts/", "/stories/fixture-story-newest/"):
            page = _page(self.output_directory, path.strip("/"))
            self.assertNotIn(PENDING_TITLE, page)
            self.assertNotIn("fixture-story-pending", page)


if __name__ == "__main__":
    unittest.main()

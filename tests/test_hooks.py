import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from reader_privacy import identity_leaks, reader_ids_in, scan_files  # noqa: E402

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "content"
STATIC_DIRECTORY = REPOSITORY_ROOT / "web"
KNOWLEDGE_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "knowledge"
READER_DATA_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "reader"
FIXTURE_SUBJECT = "file:open-weights/fixture-full-contract.md"


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
                "--knowledge-dir", str(KNOWLEDGE_DIRECTORY),
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
        self.assertIn("Checked by the fixture editor", page)
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
        self.assertIn('href="/topics/decision-models/">Beat: Decision models', page)

    def test_item_page_without_notes_has_no_score_note_for_missing_dimensions(self):
        page = self._page("decisions/fixture-router-two")
        self.assertNotIn("score-note", page)

    def test_home_page_has_one_real_board_with_four_rows_and_no_sample_board(self):
        page = self._page(".")
        self.assertIn("Latest", page)
        self.assertNotIn("Shipped this week", page)
        self.assertEqual(len(re.findall(r'<li class="board-row">', page.split('class="board desk-board"')[1].split("</ol>")[0])), 4)
        self.assertNotIn("Ratings open with reader sign-in", page)
        self.assertIn('href="/topics/decision-models/">Decision models', page)
        self.assertIn('href="/topics/open-tts/">Open TTS', page)
        self.assertNotIn("Sample", page)
        self.assertNotIn("placeholder-tag", page)
        self.assertIn("Dimmed sections with a dashed outline are placeholders", page)
        self.assertIn('<a href="/topics/decision-models/">Decision models</a>', page)
        self.assertIn("Scores on seeded items are an AI-assisted first pass", page)

    def test_new_page_has_only_the_real_board_newest_first(self):
        page = self._page("new")
        self.assertNotIn("New this week", page)
        board = page.split('class="board desk-board"')[1].split("</ol>")[0]
        self.assertLess(board.index("fixture-full-contract"), board.index("fixture-router-two"))
        self.assertLess(board.index("fixture-router-two"), board.index("fixture-guard-one"))

    def test_vapor_keeps_its_placeholder_board_and_rising_has_none(self):
        self.assertIn('class="board is-placeholder"', self._page("vapor"))
        rising = self._page("rising")
        self.assertNotIn("is-placeholder", rising.split('class="shipped-layout"')[1])
        self.assertNotIn("placeholder-tag", rising)
        self.assertNotIn("sample-mark", rising)

    def test_placeholder_pages_have_no_sample_marks(self):
        for relative_path in ("sample/roundup", "sample/tern-3", "sample/voice-agents"):
            page = self._page(relative_path)
            self.assertNotIn("sample-mark", page)
            self.assertNotIn(">Sample<", page)
            self.assertIn("placeholder-tag", page)
            self.assertIn("is-placeholder", page)

    def test_agent_scored_item_page_shows_the_label_and_the_notice(self):
        page = self._page("decisions/fixture-guard-one")
        self.assertIn("Editor&#x27;s first pass (AI-assisted)", page)
        self.assertIn("Scored by an AI research pass from the linked sources; a human editor will re-score it.", page)
        self.assertIn('href="/policies/#scores">How we score', page)

    def test_home_page_links_the_scoring_policy_and_the_footer_links_policies(self):
        page = self._page(".")
        self.assertIn('href="/policies/#scores">How we score', page)
        self.assertIn('href="/policies/">Policies', page)

    def test_footer_is_the_wordmark_links_and_the_plain_line(self):
        page = self._page(".")
        footer = page.split("<footer")[1].split("</footer>")[0]
        for href in ('href="/policies/#ranking">How ranking works', 'href="/policies/">Policies', 'href="/roundup/">Roundups', 'href="/feed.xml">RSS', 'href="/submit/">Submit'):
            self.assertIn(href, footer)
        self.assertIn("AI that shipped.", footer)
        self.assertNotIn("Anthus", page)
        self.assertNotIn("ranked by the", page)

    def test_theme_color_is_the_brand_fill_in_light_and_dark(self):
        page = self._page(".")
        self.assertIn('<meta name="theme-color" content="#C6F432">', page)
        self.assertIn('<meta name="theme-color" content="#C6F432" media="(prefers-color-scheme: dark)">', page)

    def test_no_visible_page_says_desk(self):
        for relative_path in (".", "new", "vapor", "roundup", "submit", "sign-in", "sample/tern-3", "sample/voice-agents", "topics/decision-models"):
            page = re.sub(r'<section class="clusters.*?</section>', "", self._page(relative_path), flags=re.S)
            visible = re.sub(r'class="[^"]*"|id="[^"]*"|aria-labelledby="[^"]*"|href="[^"]*"', "", page)
            self.assertNotRegex(visible.lower(), r"\bdesk\b", relative_path)

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



    # Reader steering (Papyrus 5.22.0 page components).

    def _island_props(self, page, name):
        return [json.loads(html.unescape(raw)) for raw in re.findall(rf'data-island="{name}" data-props="([^"]*)"', page)]

    def test_every_page_loads_the_reader_script_and_stylesheet(self):
        for relative_path in (".", "new", "rising", "vapor", "submit", "sign-in", "policies", "open-weights/fixture-full-contract", "topics/open-tts", "sample/tern-3"):
            page = self._page(relative_path)
            self.assertIn('<link rel="stylesheet" href="/_plugins/papyrus-reader@1.css">', page, relative_path)
            self.assertIn('<script src="/_plugins/papyrus-reader@1.js" defer></script>', page, relative_path)

    def test_reader_sign_in_replaces_the_static_link_in_the_header_and_keeps_it_as_a_fallback(self):
        for relative_path in (".", "submit", "sign-in", "open-weights/fixture-full-contract", "sample/tern-3"):
            header = self._page(relative_path).split("</header>")[0]
            self.assertEqual(len(re.findall(r'data-island="ReaderSignIn"', header)), 1, relative_path)
            self.assertIn('data-island="ReaderSignIn" data-props="{}"><a href="/sign-in/"', header, relative_path)
            self.assertEqual(header.count(">Sign in</a>"), 1, relative_path)

    def test_board_rows_carry_vote_and_used_it_for_the_lineage_subject_and_one_freshness_per_board(self):
        for relative_path in (".", "new", "topics/decision-models"):
            page = self._page(relative_path)
            rows = len(re.findall(r'<li class="board-row">', page))
            self.assertGreater(rows, 0, relative_path)
            self.assertEqual(len(self._island_props(page, "Vote")), rows, relative_path)
            self.assertEqual(len(self._island_props(page, "UsedIt")), rows, relative_path)
            board = "board" + page.split('class="board', 1)[1].split("</section>")[0] if relative_path != "topics/decision-models" else page.split('topic-block board desk-board')[1].split("</section>")[0]
            self.assertEqual(board.count('data-island="Freshness"'), 1, relative_path)
            self.assertNotIn("Ratings open with reader sign-in", page, relative_path)
        self.assertIn({"subject": FIXTURE_SUBJECT}, self._island_props(self._page("new"), "Vote"))

    def test_item_page_has_vote_used_it_rating_with_the_four_dimensions_and_comments_after_the_article(self):
        page = self._page("open-weights/fixture-full-contract")
        self.assertEqual(self._island_props(page, "Vote"), [{"subject": FIXTURE_SUBJECT}])
        self.assertEqual(self._island_props(page, "UsedIt"), [{"subject": FIXTURE_SUBJECT}])
        self.assertEqual(self._island_props(page, "Rating"), [{"subject": FIXTURE_SUBJECT, "dimensions": ["real", "useful", "notable", "novel"]}])
        self.assertEqual(self._island_props(page, "Comments"), [{"subject": FIXTURE_SUBJECT}])
        self.assertLess(page.index("</article>"), page.index('data-island="Comments"'))

    def test_subject_is_the_lineage_id_without_a_version_suffix(self):
        hooks = _load_hooks()
        for item_id, lineage in (("item-one", "item-one"), ("item-one-v2", "item-one"), ("a-v1-b", "a-v1-b"), ("1f3a-v12", "1f3a")):
            self.assertEqual(hooks._subject(type("Summary", (), {"item_id": item_id})()), lineage)

    def test_page_items_get_no_verdict_or_score_strip(self):
        page = self._page("policies")
        for text in ("Verdict", "status-stamp", "desk-strip", "Pending", "item-reader", "item-comments", "Primary evidence"):
            self.assertNotIn(text, page)
        self.assertIn("Fixture policies", page)
        self.assertNotIn('data-island="Vote"', page)

    def test_submit_page_mounts_the_submit_island_and_says_what_is_true_now(self):
        page = self._page("submit")
        self.assertEqual(self._island_props(page, "Submit"), [{}])
        for text in ("public as soon as you send it", "Editors will review submissions after the fact", "sign in"):
            self.assertIn(text, page)
        body = page.split("</header>")[1]
        self.assertLess(body.index("Submitting opens with reader sign-in, soon."), body.index("<h1"))
        self.assertIn('content="Submitting opens with reader sign-in, soon.', page)
        for text in ("is-placeholder", "placeholder-tag", "<fieldset disabled", "not open yet", "Preview", "preview-notice"):
            self.assertNotIn(text, page)

    def test_sign_in_page_explains_privacy_and_mounts_reader_sign_in(self):
        page = self._page("sign-in")
        body = page.split("</header>")[1]
        self.assertEqual(self._island_props(body, "ReaderSignIn"), [{}])
        self.assertIn("will never be published", page)
        self.assertIn("handle", page)
        self.assertLess(body.index("Reader sign-in opens soon."), body.index("<h1"))
        self.assertIn('<meta name="description" content="Reader sign-in for Shipped opens soon.">', page)
        self.assertIn("What signing in will give you", page)
        self.assertNotIn("What signing in gives you", page)
        for text in ("is-placeholder", "placeholder-tag", "coming later", "Sign in is coming", "preview-notice"):
            self.assertNotIn(text, page)

    def test_vapor_log_shows_the_real_empty_state_at_full_strength_above_the_dimmed_sample_rows(self):
        page = self._page("vapor")
        empty = page.index("No item has been stamped Vapor yet.")
        self.assertNotIn("is-placeholder", page[page.rindex("<section", 0, empty):empty])
        self.assertLess(empty, page.index('class="board is-placeholder"'))
        self.assertEqual(page.count("<h1"), 1)
        self.assertIn("Sample vapor rows", page)
        self.assertNotIn("No item has been stamped Vapor yet.", self._page("."))

    def test_vapor_log_lists_real_vapor_items_instead_of_the_empty_state(self):
        hooks = _load_hooks()
        self.assertEqual(hooks._empty_board({"verdict": "vapor", "heading": "Vapor log", "level": "1"}).count("No item has been stamped Vapor yet."), 1)
        shipped = self._page("topics/decision-models")
        self.assertNotIn("No item has been stamped", shipped)

    def test_rising_rail_and_page_use_the_ranked_list_island_with_a_real_empty_state(self):
        empty = "Rising starts counting once readers vote."
        for relative_path, limit in ((".", 5), ("new", 5), ("vapor", 5), ("rising", 5)):
            props = self._island_props(self._page(relative_path), "RankedList")
            self.assertIn({"list": "rising", "limit": limit, "empty": empty}, props, relative_path)
        self.assertIn({"list": "rising", "limit": 30, "empty": empty}, self._island_props(self._page("rising"), "RankedList"))
        for relative_path in (".", "new", "rising", "vapor"):
            page = self._page(relative_path)
            self.assertNotIn("Kiln-3B", page, relative_path)
            self.assertNotIn("rail is-placeholder", page, relative_path)

    def test_beat_chips_no_longer_point_at_sample_pages(self):
        for relative_path in (".", "new", "rising", "vapor"):
            beats = self._page(relative_path).split('aria-label="Editors’ beats"')[1].split("</nav>")[0]
            self.assertNotIn("/sample/", beats, relative_path)
            self.assertIn('href="/wiki/task-voice-agents/">Voice agents', beats, relative_path)

    def test_sample_voice_agents_page_says_ai_not_the_desk(self):
        page = self._page("sample/voice-agents")
        self.assertIn("FOLLOWED BY AI", page)
        self.assertIn("<b>AI</b>", page)
        self.assertNotIn("The desk", page)
        self.assertIn("is-placeholder", page)

    def test_projected_pages_and_reader_data_fixtures_hold_no_identity(self):
        data = {path.relative_to(READER_DATA_DIRECTORY).as_posix(): path.read_text(encoding="utf-8") for path in READER_DATA_DIRECTORY.rglob("*.json")}
        self.assertEqual(set(data), {"items.json", "board.json", "readers.json", "submissions.json", "comments/fixture-item.json"})
        published = reader_ids_in(data)
        self.assertEqual(published, {"6f1c2d3e-4a5b-4c6d-8e7f-0a1b2c3d4e5f"})
        self.assertEqual(scan_files(data, published), {})
        projected = {
            path.relative_to(self.output_directory).as_posix(): path.read_bytes()
            for path in self.output_directory.rglob("*")
            if path.is_file() and path.suffix in {".html", ".md", ".json", ".xml", ".txt", ".js", ".css"}
        }
        self.assertGreater(len(projected), 50)
        self.assertEqual(scan_files(projected), {})

    def test_the_privacy_scan_catches_what_it_is_for(self):
        reader_id = "6f1c2d3e-4a5b-4c6d-8e7f-0a1b2c3d4e5f"
        person = "0b9c7d1e-aaaa-4bbb-8ccc-123456789abc"
        self.assertEqual(identity_leaks("ss1_" + "A" * 43), ["ss1_" + "A" * 43])
        self.assertEqual(len(identity_leaks("ssdev_abcdefghij")), 1)
        self.assertEqual(identity_leaks("write to someone@example.com"), ["someone@example.com"])
        self.assertEqual(identity_leaks(f"personId {person}", [reader_id]), ["personId", person])
        self.assertEqual(identity_leaks(f"readerId {reader_id}", [reader_id]), [])
        self.assertEqual(identity_leaks(f"readerId {reader_id}"), [reader_id])

    def test_roundup_archive_has_the_signup_form_and_lists_issues(self):
        page = self._page("roundup")
        self.assertIn("<papyrus-newsletter", page)
        self.assertIn("/_plugins/papyrus-newsletter@1.js", page)
        self.assertIn("Email me the lists I ticked. I can unsubscribe in one click.", page)
        self.assertIn("fixture-issue-one", page)
        self.assertNotIn("coming later", page)

    def test_signup_form_appears_only_on_the_roundup_archive(self):
        self.assertNotIn("papyrus-newsletter", self._page("."))
        self.assertNotIn("papyrus-newsletter", self._page("sample/roundup"))

    def test_roundup_issues_stay_out_of_the_site_feed(self):
        self.assertNotIn("fixture-issue-one", (self.output_directory / "feed.xml").read_text(encoding="utf-8"))

    def test_resolved_entity_chips_link_to_the_wiki_and_unresolved_stay_plain(self):
        for path in ("open-weights/fixture-full-contract", "topics/open-tts", "new"):
            page = self._page(path)
            self.assertIn('<a class="entity-chip" href="/wiki/task-fixture-task/"><i>task</i>fixture task</a>', page, path)
            self.assertIn('<span class="entity-chip"><i>maker</i>Unlisted Fixture Lab</span>', page, path)
            self.assertNotIn("Unlisted Fixture Lab</a>", page, path)

    def test_concept_of_the_week_and_topic_count_replace_their_placeholders(self):
        for path in (".", "new", "rising"):
            page = self._page(path)
            self.assertIn("papyrus-knowledge-cotw", page, path)
            self.assertIn("Edited by AI on 2026-10-21", page, path)
            self.assertNotIn("Training-data manifest", page, path)
        for path in (".", "new", "rising", "vapor"):
            page = self._page(path)
            self.assertIn('class="papyrus-knowledge-count"', page, path)
            self.assertIn("Topic index · 1 topics", page, path)
            self.assertNotIn("214 TOPICS", page, path)
        self.assertIn('name="knowledge-topic-count"', (self.output_directory / "index.md").read_text(encoding="utf-8"))

    def test_home_clusters_show_five_terms(self):
        page = self._page(".")
        self.assertIn("Fixture theme", page)
        self.assertIn("five", page)
        self.assertNotIn("six", page)

    def test_topic_pages_carry_the_beat_parts(self):
        page = self._page("topics/decision-models")
        self.assertIn("papyrus-knowledge-beat-trend", page)
        self.assertIn("papyrus-knowledge-beat-entities", page)
        self.assertIn("Fixture theme", page)
        self.assertIn('name="knowledge-beat" key=decision-models part=trend', (self.output_directory / "topics" / "decision-models" / "index.md").read_text(encoding="utf-8"))

    def test_wiki_listing_page_size_is_fifty(self):
        projection = json.loads((STATIC_DIRECTORY / "projection.json").read_text(encoding="utf-8"))
        self.assertEqual(projection["urls"]["sections"]["wiki"]["pageSize"], 50)

    def test_boards_say_what_the_figures_are_and_link_how_ranking_works(self):
        for relative_path in (".", "new"):
            page = self._page(relative_path)
            self.assertIn("Newest first. Scores are the editor’s", page, relative_path)
            self.assertIn("upvotes and ratings from readers will be counted apart", page, relative_path)
            self.assertIn('href="/policies/#ranking">How ranking works', page, relative_path)

    def test_item_page_separates_upvotes_ratings_and_the_editor_score_and_states_the_floor(self):
        page = self._page("open-weights/fixture-full-contract")
        self.assertIn('class="reader-key"', page)
        self.assertIn("Upvotes count the readers who want this seen", page)
        self.assertIn("The editor’s score is shown on its own", page)
        self.assertIn("fewer than 5 ratings is too few to print", page)

    def test_rail_defines_shipped_by_the_v1_rule_and_the_rising_window_by_its_length(self):
        for relative_path in (".", "new", "rising", "vapor"):
            page = self._page(relative_path)
            self.assertIn("An editor confirmed it. Once reader sign-in opens, 3 signed-in readers reporting use will count too.", page, relative_path)
            self.assertNotIn("or 3 signed-in readers reported using it", page, relative_path)
            self.assertNotIn("Readers have used it.", page, relative_path)
        self.assertIn("Upvotes, last 6 hours", self._page("rising"))

    def test_sample_item_page_uses_evidence_link_and_item_text_sources_and_shows_the_minimum_n_state(self):
        page = self._page("sample/tern-3")
        self.assertNotIn("cmts", page)
        self.assertNotIn("corrections by readers", page)
        self.assertNotIn("41 comments &middot; confirmed", page)
        self.assertIn("evidence link", page)
        self.assertIn("item text", page)
        self.assertIn("n=3, too few", page)
        self.assertIn("188 rated it", page)

    def test_sample_roundup_has_table_rows_with_status_words_and_a_scores_as_of_line(self):
        page = self._page("sample/roundup")
        self.assertNotIn("item-card", page)
        self.assertIn("roundup-table-items", page)
        self.assertIn("Scores as of Fri 23 Oct 2026, frozen", page)
        self.assertIn(">Status<", page)

    def test_sign_in_page_defines_karma(self):
        page = self._page("sign-in")
        self.assertIn("Karma will be the number beside your handle", page)
        self.assertIn("plus 2 for each reader", page)


def _load_hooks():
    import importlib.util

    spec = importlib.util.spec_from_file_location("shipped_hooks_under_test", STATIC_DIRECTORY / "hooks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StampNoteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hooks = _load_hooks()

    def _note(self, verdict, by=None, at=None):
        return self.hooks._checked_note({"verdict": verdict, "by": by, "at": at})

    def test_a_stamp_names_who_and_when_in_the_words_of_its_verdict(self):
        self.assertEqual(self._note("shipped", "A. Editor", "2026-10-21"), "Confirmed by A. Editor, 21 Oct 2026")
        self.assertEqual(self._note("verified", "A. Editor", "2026-10-21"), "Checked by A. Editor, 21 Oct 2026")
        self.assertEqual(self._note("vapor", "A. Editor"), "Stamped by A. Editor")
        self.assertEqual(self._note("shipped", None, "2026-10-21"), "Confirmed on 21 Oct 2026")

    def test_without_the_data_or_for_pending_it_says_nothing(self):
        self.assertEqual(self._note("shipped"), "")
        self.assertEqual(self._note("pending", "A. Editor", "2026-10-21"), "")


class ReaderSteeringConfigurationTest(unittest.TestCase):
    def setUp(self):
        self.configuration = (REPOSITORY_ROOT / "papyrus.config.ts").read_text(encoding="utf-8")
        self.scoring = json.loads((STATIC_DIRECTORY / "scoring.json").read_text(encoding="utf-8"))

    def test_the_plugin_is_listed_with_the_dimensions_and_hype_gap_of_scoring_json(self):
        self.assertIn('name: "reader-steering"', self.configuration)
        keys = [dimension["key"] for dimension in self.scoring["dimensions"]]
        self.assertIn("dimensions: [" + ", ".join(f'"{key}"' for key in keys) + "]", self.configuration)
        rule = self.scoring["hypeGap"]
        plus = ", ".join(f'"{key}"' for key in rule["plus"])
        minus = ", ".join(f'"{key}"' for key in rule["minus"])
        self.assertIn(f"hypeGap: {{ plus: [{plus}], minus: [{minus}] }}", self.configuration)

    def test_the_snapshot_runs_every_six_hours_and_the_retirement_poll_has_its_secret(self):
        self.assertIn("snapshot: { schedule: true, intervalHours: 6 }", self.configuration)
        self.assertIn("retirementPoll: true", self.configuration)
        site = json.loads((REPOSITORY_ROOT / "infra" / "site.json").read_text(encoding="utf-8"))
        self.assertIs(site["cms"]["readerRetirementPoll"], True)
        self.assertIn("prospectusAccountsApiStageArn", site["cms"])

    def test_the_compute_role_is_the_same_one_the_newsletter_plugin_uses(self):
        roles = re.findall(r'computeRoleArn: "([^"]+)"', self.configuration)
        self.assertEqual(len(roles), 2)
        self.assertEqual(roles[0], roles[1])

    def test_moderation_is_human_and_the_site_origin_is_configured_for_the_reader_api(self):
        self.assertIn('moderation: { mode: "human" }', self.configuration)
        site = json.loads((REPOSITORY_ROOT / "infra" / "site.json").read_text(encoding="utf-8"))
        self.assertEqual(site["cms"]["siteOrigin"], "https://shipped.anth.us")


class NewsletterConfigurationTest(unittest.TestCase):
    def test_signup_form_lists_match_the_newsletter_plugin_configuration(self):
        configuration = (REPOSITORY_ROOT / "papyrus.config.ts").read_text(encoding="utf-8")
        configured = re.findall(r'id: "([a-z0-9-]+)",\s+name: "([^"]+)"', configuration)
        listed = [(entry["id"], entry["name"]) for entry in json.loads((STATIC_DIRECTORY / "newsletter-lists.json").read_text(encoding="utf-8"))]
        self.assertEqual(configured, listed)

    def test_alert_lists_follow_the_projection_sections(self):
        projection = json.loads((STATIC_DIRECTORY / "projection.json").read_text(encoding="utf-8"))
        configuration = (REPOSITORY_ROOT / "papyrus.config.ts").read_text(encoding="utf-8")
        alert_sections = set(re.findall(r'rule: \{ sections: \["([a-z0-9-]+)"\] \}', configuration))
        self.assertEqual(alert_sections, {"shipped", "open-weights", "decisions"})
        self.assertTrue(alert_sections <= set(projection["urls"]["sections"]))
        self.assertEqual(projection["urls"]["style"], "directory")
        self.assertIn("newsletter_issue", projection["listings"]["types"])


class PageVocabularyTest(unittest.TestCase):
    """The launch vocabulary (ship-14efe5 items 6, 9 and 13) holds in the page sources, text only."""

    def _text(self, name):
        source = (STATIC_DIRECTORY / "pages" / name).read_text(encoding="utf-8")
        source = re.sub(r"::include\{[^}]*\}", " ", source)
        return html.unescape(re.sub(r"<[^>]+>", " ", source))

    def test_no_signal_chip_and_no_off_vocabulary_kind_in_sample_rows(self):
        for page in STATIC_DIRECTORY.joinpath("pages").glob("*.md"):
            source = page.read_text(encoding="utf-8")
            kinds = set(re.findall(r'<a class="entity-chip"[^>]*><i>([a-z ]+)</i>', source))
            self.assertLessEqual(kinds, {"maker", "model", "model family", "task", "technique", "licence", "concept", "platform", "dataset"}, page.name)

    def test_no_reader_votes_authors_or_desk_in_the_insights(self):
        for page in STATIC_DIRECTORY.joinpath("pages").glob("*.md"):
            text = self._text(page.name)
            for word in ("Agree", "Disagree", "signal"):
                self.assertNotIn(word, text, page.name)
            if page.name == "topic-voice-agents.md":
                self.assertNotIn("dsp_nadia", text)
            self.assertIsNone(re.search(r"(?i)\bdesk\b|anthus", text), page.name)

    def test_beats_are_beats_and_the_index_counts_topics(self):
        for name in ("topic-open-tts.md", "topic-decision-models.md"):
            text = self._text(name)
            self.assertIn("Beats", text)
            self.assertIn("Topics in this beat", text)
            self.assertNotIn("Concepts in this topic", text)
        for name in ("home.md", "new.md", "rising.md", "vapor.md"):
            self.assertNotIn("All {n} topics", (STATIC_DIRECTORY / "pages" / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

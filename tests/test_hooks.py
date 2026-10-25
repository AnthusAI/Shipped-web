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


def _load_hooks():
    import importlib.util

    spec = importlib.util.spec_from_file_location("shipped_hooks_under_test", STATIC_DIRECTORY / "hooks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        self.assertIn("Verified by the fixture editor", page)
        self.assertIn("Partly", page)
        self.assertIn("Not checked", page)
        self.assertIn("Editor score", page)
        self.assertNotIn("scoring-provenance", page)
        self.assertNotIn("hype", page.lower())

    def test_item_page_renders_source_release_date_score_notes_and_topic_link(self):
        page = self._page("decisions/fixture-guard-one")
        self.assertIn('class="source-link" href="https://source.fixture.example/guard-one" rel="noopener"', page)
        self.assertIn("Source: source.fixture.example", page)
        self.assertIn("Released 18 Oct 2026", page)
        self.assertIn('<span class="score-note">Fixture note on advances.</span>', page)
        self.assertIn('href="/topics/decision-models/">Beat: Decision models', page)

    def test_item_page_without_notes_has_no_score_note_for_missing_dimensions(self):
        page = self._page("decisions/fixture-router-two")
        self.assertNotIn("score-note", page)

    def test_home_page_has_one_real_board_with_four_rows_and_no_sample_board(self):
        page = self._page(".")
        self.assertNotIn("Shipped this week", page)
        self.assertEqual(len(re.findall(r'<li class="board-row">', page.split('class="board desk-board"')[1].split("</ol>")[0])), 4)
        self.assertNotIn("Ratings open with reader sign-in", page)
        self.assertNotIn("Sample", page)
        self.assertIn("Latest signals", page)

    def test_new_page_has_only_the_real_board_newest_first(self):
        page = self._page("new")
        self.assertNotIn("New this week", page)
        board = page.split('class="board desk-board"')[1].split("</ol>")[0]
        self.assertLess(board.index("fixture-full-contract"), board.index("fixture-router-two"))
        self.assertLess(board.index("fixture-router-two"), board.index("fixture-guard-one"))

    def test_rising_has_no_placeholder_board(self):
        rising = self._page("rising")
        self.assertNotIn("is-placeholder", rising.split('class="shipped-layout"')[1])
        self.assertNotIn("placeholder-tag", rising)
        self.assertNotIn("sample-mark", rising)

    def test_placeholder_pages_have_no_sample_marks(self):
        for relative_path in ("sample/roundup", "sample/story", "sample/tern-3", "sample/voice-agents"):
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
        for href in ('href="/map/">How the map works', 'href="/policies/#steering">How steering works', 'href="/policies/">Policies', 'href="/roundup/">All issues', 'href="/feed.xml">RSS', 'href="/policies/#privacy">Privacy', 'href="#cookie-settings">Cookie settings'):
            self.assertIn(href, footer)
        self.assertIn("Published by Anthus AI Solutions, which also sponsors it.", footer)
        self.assertIn('href="/policies/#sponsorship">Sponsorship and independence', footer)
        self.assertNotIn("ranked by the", page)

    def test_theme_color_is_the_brand_fill_in_light_and_dark(self):
        page = self._page(".")
        self.assertIn('<meta name="theme-color" content="#C6F432">', page)
        self.assertIn('<meta name="theme-color" content="#C6F432" media="(prefers-color-scheme: dark)">', page)

    def test_no_visible_page_says_desk(self):
        for relative_path in (".", "new", "roundup", "submit", "sign-in", "sample/tern-3", "sample/voice-agents", "topics/decision-models"):
            page = re.sub(r'<section class="clusters.*?</section>', "", self._page(relative_path), flags=re.S)
            visible = re.sub(r'class="[^"]*"|id="[^"]*"|aria-labelledby="[^"]*"|href="[^"]*"', "", page)
            self.assertNotRegex(visible.lower(), r"\bdesk\b", relative_path)

    def test_item_page_without_scoring_says_editor_score(self):
        page = self._page("decisions/fixture-router-two")
        self.assertIn('<p class="kicker">Editor score</p>', page)
        self.assertNotIn("scoring-provenance", page)
        self.assertNotIn("AI first pass", page)

    def test_concept_pages_list_latest_signals_instead_of_a_scored_board(self):
        for path in ("topics/decision-models", "topics/open-tts"):
            page = self._page(path)
            self.assertNotIn("board-row", page, path)
            self.assertIn('class="signal-row"', page, path)

    def test_board_rows_have_status_title_section_and_date_and_no_score_columns(self):
        for relative_path in (".", "new"):
            page = self._page(relative_path)
            rows = re.findall(r'<li class="board-row">.*?</li>', page, flags=re.S)
            self.assertGreater(len(rows), 0, relative_path)
            for row in rows:
                for part in ("board-status", "board-title", "board-section", "board-date", 'data-island="Vote"', 'data-island="UsedIt"'):
                    self.assertIn(part, row, relative_path)
                for gone in ("board-dimensions", "score-dimension", "board-rank", "ai-first-pass-tag"):
                    self.assertNotIn(gone, row, relative_path)
            self.assertNotIn('class="board-head kicker', page, relative_path)

    def test_old_score_keys_are_never_shown_and_warn_once_per_item(self):
        page = self._page("decisions/fixture-router-two")
        self.assertIn("Not yet rated", page)
        self.assertEqual(page.count('class="score-dimension-value">3.0<'), 1)
        for retired in ("Real", "Notable", "Novel"):
            self.assertNotIn(f"<b>{retired}</b>", page)
        warnings = [line for line in self.projection_log.splitlines() if "fixture-router-two" in line and "retired dimensions" in line]
        self.assertEqual(len(warnings), 1)

    def test_signal_page_follows_the_design_order(self):
        page = self._page("open-weights/fixture-full-contract")
        order = [
            'class="signal-meta"', 'class="status-stamp status-stamp-verified status-stamp-lg"', "signal-status-provenance",
            'id="signal-summary-h"', 'id="desk-evidence-h"', 'id="signal-map-h"', 'id="signal-ratings-h"',
            'id="signal-stories-h"', 'id="item-comments-h"',
        ]
        positions = [page.index(marker) for marker in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("built on", page)
        self.assertIn('<i>task</i>fixture task', page)
        self.assertNotIn("this week", page)
        self.assertEqual(page.count('class="placeholder-tag"'), 0)
        self.assertNotIn("signal-underrated", page)
        self.assertNotIn("signal-nearby-h", page)
        head = re.search(r'<div class="signal-dimension-head.*?</div>', page, flags=re.S).group(0)
        self.assertEqual(re.findall(r"<span>(.*?)</span>", head), ["Dimension", "Readers", "Editors", "Your rating"])
        self.assertEqual(page.count("Not yet rated"), 1)

    def test_an_agent_scored_item_says_who_stamped_it_and_when(self):
        page = self._page("decisions/fixture-guard-one")
        self.assertIn("Stamped by AI, first pass on 21 Oct 2026 &middot; awaiting an editor check", page)

    def test_maker_handle_is_shown_verbatim(self):
        with_both = self._page("decisions/fixture-router-two")
        self.assertIn('Other Fixture Lab (<span class="maker-handle">other-fixture-lab</span>)', with_both)
        handle_only = self._page("shipped/fixture-invalid-values")
        self.assertIn('<span class="kicker maker-display"><span class="maker-handle">handle-only-lab</span></span>', handle_only)

    def test_decision_models_topic_page_lists_its_own_signals(self):
        page = self._page("topics/decision-models")
        self.assertIn("<title>Decision models in the wild", page)
        self.assertNotIn("sample-mark", page)
        self.assertEqual(len(re.findall(r'class="signal-row"', page)), 2)
        self.assertIn("Other Fixture Lab", page)
        self.assertNotIn("fixture-full-contract", page)

    def test_open_tts_topic_page_lists_only_its_own_tag(self):
        page = self._page("topics/open-tts")
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
        self.assertIn("status-stamp-announced", page)

    def test_invalid_values_log_a_warning_and_never_fail_the_build(self):
        self.assertIn("fixture-invalid-values", self.projection_log)



    # Reader steering (Papyrus 5.22.0 page components).

    def _island_props(self, page, name):
        return [json.loads(html.unescape(raw)) for raw in re.findall(rf'data-island="{name}" data-props="([^"]*)"', page)]

    def test_every_page_loads_the_reader_script_and_stylesheet(self):
        for relative_path in (".", "new", "rising", "submit", "sign-in", "policies", "open-weights/fixture-full-contract", "topics/open-tts", "sample/tern-3"):
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
        for relative_path in (".", "new"):
            page = self._page(relative_path)
            rows = len(re.findall(r'<li class="board-row">', page))
            self.assertGreater(rows, 0, relative_path)
            self.assertEqual(len(self._island_props(page, "Vote")), rows, relative_path)
            self.assertEqual(len(self._island_props(page, "UsedIt")), rows, relative_path)
            board = "board" + page.split('class="board', 1)[1].split("</section>")[0]
            self.assertEqual(board.count('data-island="Freshness"'), 1, relative_path)
            self.assertNotIn("Ratings open with reader sign-in", page, relative_path)
        self.assertIn({"subject": FIXTURE_SUBJECT}, self._island_props(self._page("new"), "Vote"))

    def test_item_page_has_vote_used_it_rating_with_the_four_dimensions_and_comments_after_the_article(self):
        page = self._page("open-weights/fixture-full-contract")
        self.assertEqual(self._island_props(page, "Vote"), [{"subject": FIXTURE_SUBJECT}])
        self.assertEqual(self._island_props(page, "UsedIt"), [{"subject": FIXTURE_SUBJECT}])
        self.assertEqual(
            self._island_props(page, "Rating"),
            [{"subject": FIXTURE_SUBJECT, "dimensions": [key]} for key in ("useful", "ready", "advances", "open")],
        )
        self.assertEqual(self._island_props(page, "Comments"), [{"subject": FIXTURE_SUBJECT}])
        self.assertLess(page.index("</article>"), page.index('data-island="Comments"'))

    def test_subject_is_the_lineage_id_without_a_version_suffix(self):
        hooks = _load_hooks()
        for item_id, lineage in (("item-one", "item-one"), ("item-one-v2", "item-one"), ("a-v1-b", "a-v1-b"), ("1f3a-v12", "1f3a")):
            self.assertEqual(hooks._subject(type("Summary", (), {"item_id": item_id})()), lineage)

    def test_no_projected_page_mentions_vapor_or_the_hype_gap(self):
        offenders = [
            path.relative_to(self.output_directory).as_posix()
            for path in self.output_directory.rglob("*")
            if path.is_file() and path.suffix in {".html", ".md", ".xml", ".txt"}
            and re.search(r"vapor|hype gap|hype-gap", path.read_text(encoding="utf-8"), re.I)
        ]
        self.assertEqual(offenders, [])
        self.assertFalse((self.output_directory / "vapor").exists())

    def test_the_vapor_log_url_redirects_to_new(self):
        projection = json.loads((STATIC_DIRECTORY / "projection.json").read_text(encoding="utf-8"))
        self.assertEqual(projection["redirects"]["exact"], {"/vapor/": "/new/"})
        self.assertNotIn("/vapor/", [link["href"] for link in projection["nav"]["links"]])
        self.assertFalse((STATIC_DIRECTORY / "pages" / "vapor.md").exists())

    def test_page_items_get_no_verdict_or_score_strip(self):
        page = self._page("policies")
        for text in ("Verdict", "status-stamp", "desk-strip", "Pending", "item-reader", "item-comments", "Primary evidence"):
            self.assertNotIn(text, page)
        self.assertIn("Fixture policies", page)
        self.assertNotIn('data-island="Vote"', page)

    def test_submit_page_mounts_the_submit_island_and_says_what_is_true_now(self):
        page = self._page("submit")
        self.assertEqual(self._island_props(page, "Submit"), [{}])
        for text in ("public as soon as you send it", "Editors review submissions after the fact", "sign in"):
            self.assertIn(text, page)
        self.assertIn("Add something in the wild", page)
        self.assertIn("New signals start as Announced", page)
        self.assertIn("Not a release?</b> Propose a concept or a correction to the map.", page)
        self.assertIn('href="/proposals/"', page)
        on_the_map = page.split('class="on-the-map is-placeholder"')[1].split("</section>")[0]
        self.assertEqual(on_the_map.count("placeholder-tag"), 1)
        self.assertLess(page.index('data-island="Submit"'), page.index("on-the-map"))
        for text in ("<fieldset disabled", "not open yet", "preview-notice", "soon."):
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

    def test_rising_rail_and_page_use_the_ranked_list_island_with_a_real_empty_state(self):
        empty = "Rising starts counting once readers vote."
        for relative_path, limit in (("new", 5), ("rising", 5)):
            props = self._island_props(self._page(relative_path), "RankedList")
            self.assertIn({"list": "rising", "limit": limit, "empty": empty}, props, relative_path)
        self.assertIn({"list": "rising", "limit": 30, "empty": empty}, self._island_props(self._page("rising"), "RankedList"))
        for relative_path in ("new", "rising"):
            page = self._page(relative_path)
            self.assertNotIn("Kiln-3B", page, relative_path)
            self.assertNotIn("rail is-placeholder", page, relative_path)

    def test_beat_chips_no_longer_point_at_sample_pages(self):
        for relative_path in ("new", "rising"):
            beats = self._page(relative_path).split('aria-label="Editors’ beats"')[1].split("</nav>")[0]
            self.assertNotIn("/sample/", beats, relative_path)
            self.assertIn('href="/wiki/task-voice-agents/">Voice agents', beats, relative_path)

    def test_sample_voice_agents_page_says_ai_not_the_desk(self):
        page = self._page("sample/voice-agents")
        self.assertIn("Edited by AI on [date]", page)
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

    def test_signup_form_appears_on_the_front_page_and_the_roundup_archive_only(self):
        self.assertIn("<papyrus-newsletter", self._page("."))
        self.assertNotIn("papyrus-newsletter", self._page("new"))
        self.assertNotIn("papyrus-newsletter", self._page("sample/roundup"))

    def test_front_page_follows_the_design_in_order_with_real_and_placeholder_parts(self):
        page = self._page(".")
        order = ["front-stats", "front-invite", "front-lead-h", "front-map-h", "front-table-h", "front-stories-h",
                 "front-rising-h", "front-proposals-h", "desk-board-h", "front-weekly-heading"]
        positions = [page.index(f'id="{name}"') if f'id="{name}"' in page else page.index(name) for name in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("<b>4</b> signals", page)
        self.assertIn("1 entities on the map", page)
        self.assertNotIn("weeks of map history", page)
        self.assertEqual(page.count('class="placeholder-tag"'), 1)
        self.assertNotIn("front-underrated", page)
        self.assertIn("Draft · not yet approved", page)
        self.assertIn("Approved by <b>fixture-editor</b>", page)
        self.assertIn("Fixture theme", page.split('id="front-map-h"')[1].split("</aside>")[0])
        self.assertIn("The Weekly", page)
        self.assertIn("New arrivals in machine learning. One email on Fridays.", page)
        self.assertNotIn("How to read a row", page)
        self.assertNotIn("vapor", page.lower())

    def test_roundup_issues_stay_out_of_the_site_feed(self):
        self.assertNotIn("fixture-issue-one", (self.output_directory / "feed.xml").read_text(encoding="utf-8"))

    def test_resolved_entity_chips_link_to_the_wiki_and_unresolved_stay_plain(self):
        for path in ("open-weights/fixture-full-contract",):
            page = self._page(path)
            self.assertIn('<a class="entity-chip" href="/wiki/task-fixture-task/"><i>task</i>fixture task</a>', page, path)
            self.assertIn('<span class="entity-chip"><i>maker</i>Unlisted Fixture Lab</span>', page, path)
            self.assertNotIn("Unlisted Fixture Lab</a>", page, path)

    def test_concept_of_the_week_and_topic_count_replace_their_placeholders(self):
        for path in ("new", "rising"):
            page = self._page(path)
            self.assertIn("papyrus-knowledge-cotw", page, path)
            self.assertIn("Edited by AI on 2026-10-21", page, path)
            self.assertNotIn("Training-data manifest", page, path)
        for path in ("new", "rising"):
            page = self._page(path)
            self.assertIn('class="papyrus-knowledge-count"', page, path)
            self.assertIn("Topic index · 1 topics", page, path)
            self.assertNotIn("214 TOPICS", page, path)
        self.assertIn('name="knowledge-topic-count"', (self.output_directory / "index.md").read_text(encoding="utf-8"))

    def test_home_clusters_show_three_terms(self):
        page = self._page(".")
        self.assertIn("Fixture theme", page)
        map_panel = page.split('id="front-map-h"')[1].split("</aside>")[0]
        self.assertIn("three", map_panel)
        self.assertNotIn("four", map_panel)

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
            self.assertIn("Newest first. Each signal is Available, Verified or Announced.", page, relative_path)
            self.assertIn("Upvotes and ratings from readers are counted apart", page, relative_path)
            self.assertIn('href="/policies/#ranking">How ranking works', page, relative_path)

    def test_item_page_separates_upvotes_ratings_and_the_editor_score_and_states_the_floor(self):
        page = self._page("open-weights/fixture-full-contract")
        self.assertIn('class="reader-key"', page)
        self.assertIn("Upvotes count the readers who want this seen", page)
        self.assertIn("Readers and editors are shown separately", page)
        self.assertIn("fewer than 5 ratings is too few to print", page)

    def test_rail_key_defines_the_three_statuses_and_the_rising_window_by_its_length(self):
        for relative_path in ("new", "rising"):
            key = self._page(relative_path).split('class="rail-key"')[1].split("</dl>")[0]
            self.assertEqual(re.findall(r'status-stamp-label">(\w+)<', key), ["Available", "Verified", "Announced"], relative_path)
            self.assertIn("Anyone can use it today.", key, relative_path)
            self.assertIn("Available, and an editor checked the evidence.", key, relative_path)
            self.assertIn("Claimed, not yet usable or not yet confirmed.", key, relative_path)
        self.assertIn("Upvotes, last 6 hours", self._page("rising"))

    def test_retired_status_words_stay_out_of_every_page(self):
        for path in self.output_directory.rglob("index.html"):
            page = path.read_text(encoding="utf-8")
            for retired in ("status-stamp-shipped", "status-stamp-pending", "status-stamp-vapor", 'status-stamp-label">Shipped<', 'status-stamp-label">Pending<', 'status-stamp-label">Vapor<'):
                self.assertNotIn(retired, page, path.as_posix())

    def test_a_retired_verdict_word_in_front_matter_reads_as_its_new_status(self):
        page = self._page("decisions/fixture-router-two")
        self.assertIn("status-stamp-announced", page)
        self.assertIn(">Announced<", page)

    def test_sample_item_page_uses_evidence_link_and_item_text_sources_and_shows_the_minimum_n_state(self):
        page = self._page("sample/tern-3")
        self.assertNotIn("cmts", page)
        self.assertNotIn("corrections by readers", page)
        self.assertNotIn("41 comments", page)
        self.assertIn("evidence link", page)
        self.assertIn("item text", page)
        self.assertIn("n=3, too few", page)
        self.assertIn("188 rated it", page)

    def test_sample_roundup_is_the_weekly_with_every_part_as_a_placeholder(self):
        page = self._page("sample/roundup")
        self.assertIn("New arrivals in machine learning.", page)
        self.assertIn("Drafted by AI", page)
        self.assertIn("Approved by <b>[editor]</b>", page)
        for heading in ("What moved on the map", "Concepts born this week", "The community’s top proposal", "Underrated this week", "Also out this week"):
            self.assertIn(heading, page)
        self.assertEqual(page.count("placeholder-tag"), 6)
        for old in ("Weekly roundup", ">Real<", ">Notable<", ">Novel<"):
            self.assertNotIn(old, page)

    def test_roundup_archive_has_the_weekly_strap_and_links_the_sample_issue(self):
        page = self._page("roundup")
        self.assertIn("<h1>The Weekly</h1>", page)
        self.assertIn("New arrivals in machine learning.", page)
        self.assertIn('href="/sample/roundup/"', page)

    def test_proposals_page_explains_steering_and_keeps_the_queue_as_a_placeholder(self):
        page = self._page("proposals")
        for text in ("AI proposes. You steer. Editors decide.", "Draft · not yet approved", "How steering works", "Karma is shown but never gates voting", "both results stay visible, with a reason", "Sign in with Google", "Two tiers", "When editors overrule the community", "data-proposals-tiers-list"):
            self.assertIn(text, page)
        for text in ("Stories", "Concepts", "Map changes", "Top", "New", "Controversial", "Overridden by editor", "Editor review", "In steering"):
            self.assertIn(text, page)
        self.assertEqual(self._island_props(page, "ReaderSignIn")[-1], {})
        queue = page.split('class="proposals-queue is-placeholder"')[1].split("</section>")[0]
        self.assertEqual(queue.count("placeholder-tag"), 1)
        self.assertEqual(queue.count('class="proposals-row"'), 4)
        self.assertNotRegex(queue, r"▲ \d")
        self.assertNotIn("<button type=\"button\" aria-pressed", queue)
        self.assertNotRegex((STATIC_DIRECTORY / "pages" / "proposals.md").read_text(encoding="utf-8").lower(), r"\bdesk\b")

    def test_sample_story_is_a_placeholder_with_citations_lineage_and_a_draft_box(self):
        page = self._page("sample/story")
        self.assertIn("Decision models are starting to have family trees", page)
        self.assertIn("Figure: Shipped map · Edited by AI", page)
        self.assertIn("Draft · not yet approved", page)
        self.assertIn("Signals cited", page)
        self.assertIn("Was this story right?", page)
        self.assertIn("This is wrong", page)
        self.assertIn("Sample lineage · not yet verified", page)
        for number in range(1, 6):
            self.assertIn(f'href="#src-{number}"', page)
            self.assertIn(f'id="src-{number}"', page)
        self.assertIn("<b>[n]</b> readers steered it", page)
        self.assertIn("Approved by <b>[editor]</b>", page)
        self.assertNotIn("sample-mark", page)

    def test_sign_in_page_defines_karma(self):
        page = self._page("sign-in")
        self.assertIn("Karma will be the number beside your handle", page)
        self.assertIn("plus 2 for each reader", page)

    def test_masthead_carries_the_tagline_and_the_new_navigation(self):
        page = self._page(".")
        header = page.split("<header")[1].split("</header>")[0]
        self.assertIn("New arrivals in machine learning.", header)
        for label in ("Front", "Map", "Proposals", "New", "Wiki", "The Weekly", "Submit"):
            self.assertIn(f">{label}</a>", header)
        for label in ("Rising", "Vapor"):
            self.assertNotIn(f">{label}</a>", header)

    def test_masthead_is_the_shipping_label_lockup_with_a_dated_barcode(self):
        page = self._page(".")
        header = page.split("<header")[1].split("</header>")[0]
        self.assertIn('<span class="brand-word">Shipped</span>', header)
        self.assertIn('class="brand-divider"', header)
        self.assertIn('role="img"', header)
        self.assertRegex(header, r'aria-label="Barcode for SHP \d{4}-\d{2}-\d{2}, today&#x27;s date"')
        self.assertRegex(header, r'data-brand-barcode-text aria-hidden="true">SHP \d{4}-\d{2}-\d{2}<')
        self.assertIn('<script src="/assets/shipped-barcode.js" defer></script>', header)
        self.assertEqual(header.count("data-brand-barcode>"), 1)

    def test_masthead_carries_the_tagline_and_the_descriptor(self):
        page = self._page(".")
        header = page.split("<header")[1].split("</header>")[0]
        self.assertIn('<p class="markus-site-tagline">New arrivals in machine learning.</p>', header)
        self.assertIn(
            '<p class="markus-site-descriptor">Open weights, decision models, real products. Mapped as they land.</p>',
            header,
        )

    def test_footer_wordmark_is_plain_without_a_barcode(self):
        page = self._page(".")
        footer = page.split("<footer")[1].split("</footer>")[0]
        self.assertIn('<span class="brand-word">Shipped</span>', footer)
        self.assertNotIn("brand-barcode", footer)

    def test_home_title_and_description_use_the_new_copy(self):
        page = self._page(".")
        self.assertIn("<title>Shipped: new arrivals in machine learning", page)
        self.assertIn("Mapped as they land.", page)
        self.assertNotIn("In the wild", page)

    def test_pages_link_the_icon_the_apple_touch_icon_and_the_manifest(self):
        page = self._page(".")
        self.assertIn('<link rel="icon" href="/assets/icons/shipped-icon.svg" type="image/svg+xml">', page)
        self.assertIn('<link rel="apple-touch-icon" href="/assets/icons/shipped-icon-180.png">', page)
        self.assertIn('<link rel="manifest" href="/assets/icons/shipped.webmanifest">', page)
        for published in ("shipped-icon.svg", "shipped-icon-32.png", "shipped-icon-180.png", "shipped-icon-512.png", "shipped.webmanifest"):
            self.assertTrue((self.output_directory / "assets" / "icons" / published).exists(), published)

    def test_markdown_and_llms_text_carry_no_barcode_markup(self):
        for relative_path in ("index.md", "llms.txt"):
            text = (self.output_directory / relative_path).read_text(encoding="utf-8")
            self.assertNotIn("<svg", text)
            self.assertNotIn("brand-barcode", text)

    def test_every_page_carries_the_default_social_card(self):
        page = self._page(".")
        self.assertIn('<meta property="og:image" content="https://shipped.anth.us/assets/social/shipped-default.png">', page)
        self.assertIn('<meta name="twitter:image" content="https://shipped.anth.us/assets/social/shipped-default.png">', page)

    def test_concept_page_has_the_design_sections_and_no_wiki_chrome(self):
        page = self._page("topics/decision-models")
        for heading in ("Where it came from", "Signals per week", "Neighbourhood", "Sub-concepts", "Clusters it touches", "Latest signals", "Stories that cite it"):
            self.assertIn(heading, page)
        self.assertIn("Edited by AI on 21 Oct 2026", page)
        self.assertIn("Graph JSON", page)
        self.assertIn("Suggest an edit", page)
        for removed in ("Edit wiki", "Discuss", "contributors"):
            self.assertNotIn(removed, page)
        self.assertEqual(page.count('class="placeholder-tag"'), 1)

    def test_concept_stats_come_from_the_knowledge_snapshot_and_items(self):
        page = self._page("topics/decision-models")
        stats = re.search(r'<dl class="concept-stats">(.*?)</dl>', page, re.S).group(1)
        values = dict(re.findall(r"<dt>([^<]+)</dt><dd>(\d+)</dd>", stats))
        self.assertEqual(values, {"Signals, 8 wks": "13", "This week": "2", "Makers": "2", "Clusters": "1"})

    def test_section_landing_lists_only_that_sections_items_newest_first(self):
        page = self._page("decisions")
        self.assertIn("Latest signals in Decisions in the wild", page)
        self.assertIn('aria-current="page">Decisions in the wild', page)
        self.assertNotIn("Concepts bubbling up", page)
        self.assertIn("Clusters across Shipped", page)
        self.assertIn("CLUSTERS ARE NOT SPLIT BY SECTION YET", page)
        self.assertEqual(page.count('class="placeholder-tag"'), 0)
        self.assertNotIn("fixture-full-contract", page)
        self.assertLess(page.index("fixture-router-two"), page.index("fixture-guard-one"))
        weights = self._page("open-weights")
        self.assertIn("Concepts bubbling up", weights)
        self.assertIn("1 in section", weights)


EXPECTED_BARCODE_MODULES_FOR_2026_10_22 = (
    "110100100001101110100011000101000111011101101101100110011001110010100111011001100111001011001110"
    "100100110111001001110011010011101100100110111001100111001011001110010101110011001100011101011"
)


class LogotypeBarcodeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hooks = _load_hooks()

    def test_code_128_set_b_modules_match_the_reference_encoder_for_the_build_date_text(self):
        self.assertEqual(self.hooks._code128_set_b_modules("SHP 2026-10-22"), EXPECTED_BARCODE_MODULES_FOR_2026_10_22)

    def test_barcode_has_start_symbol_checksum_stop_and_termination_bar(self):
        modules = self.hooks._code128_set_b_modules("SHP 2026-10-22")
        self.assertEqual(len(modules), 11 * (1 + 14 + 1) + 13)
        self.assertTrue(modules.startswith("11010010000"))
        self.assertTrue(modules.endswith("1100011101011"))

    def test_text_outside_code_set_b_is_refused(self):
        with self.assertRaises(ValueError):
            self.hooks._code128_set_b_modules("SHP \u00e9")

    def test_barcode_text_is_the_prefix_and_the_iso_date(self):
        from datetime import date

        self.assertEqual(self.hooks._logotype_barcode_text(date(2026, 10, 22)), "SHP 2026-10-22")

    def test_barcode_markup_is_an_inline_image_with_a_label_and_the_text_line(self):
        from datetime import date

        markup = self.hooks._logotype_barcode_html(date(2026, 10, 22))
        self.assertIn('role="img"', markup)
        self.assertIn("Barcode for SHP 2026-10-22, today&#x27;s date", markup)
        self.assertIn(">SHP 2026-10-22</span>", markup)

    def test_static_script_carries_the_same_pattern_table(self):
        script = (STATIC_DIRECTORY / "assets" / "shipped-barcode.js").read_text(encoding="utf-8")
        for pattern in self.hooks.CODE128_PATTERNS:
            self.assertIn(pattern, script)


class StampNoteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hooks = _load_hooks()

    def _note(self, verdict, by=None, at=None):
        return self.hooks._checked_note({"verdict": verdict, "by": by, "at": at})

    def test_a_stamp_names_who_and_when_in_the_words_of_its_verdict(self):
        self.assertEqual(self._note("available", "A. Editor", "2026-10-21"), "Confirmed by A. Editor, 21 Oct 2026")
        self.assertEqual(self._note("verified", "A. Editor", "2026-10-21"), "Verified by A. Editor, 21 Oct 2026")
        self.assertEqual(self._note("available", None, "2026-10-21"), "Confirmed on 21 Oct 2026")

    def test_the_old_verdict_words_read_as_the_new_statuses(self):
        summary = type("Summary", (), {"item_id": "x", "output_path": "x", "slug": "x"})()
        for old, new in (("shipped", "available"), ("pending", "announced"), ("vapor", "announced"), ("verified", "verified"), ("available", "available"), ("bogus", "announced")):
            self.assertEqual(self.hooks._read_verdict(summary, {"verdict": old}), new)
        self.assertEqual(self.hooks._read_verdict(summary, {}), "announced")

    def test_without_the_data_or_for_pending_it_says_nothing(self):
        self.assertEqual(self._note("available"), "")
        self.assertEqual(self._note("announced", "A. Editor", "2026-10-21"), "")


class ReaderSteeringConfigurationTest(unittest.TestCase):
    def setUp(self):
        self.configuration = (REPOSITORY_ROOT / "papyrus.config.ts").read_text(encoding="utf-8")
        self.scoring = json.loads((STATIC_DIRECTORY / "scoring.json").read_text(encoding="utf-8"))

    def test_the_plugin_is_listed_with_the_dimensions_of_scoring_json(self):
        self.assertIn('name: "reader-steering"', self.configuration)
        keys = [dimension["key"] for dimension in self.scoring["dimensions"]]
        self.assertIn("dimensions: [" + ", ".join(f'"{key}"' for key in keys) + "]", self.configuration)
        self.assertNotIn("hypeGap", self.configuration)
        self.assertNotIn("hypeGap", self.scoring)

    def test_the_vote_subjects_of_scoring_json_match_the_plugin_subject_types(self):
        types = self.scoring["voteSubjects"]
        self.assertIn("subjects: { types: [" + ", ".join(f'"{name}"' for name in types) + "] }", self.configuration)
        self.assertIn("proposal", types)

    def test_proposals_are_published_so_the_public_queue_has_data(self):
        self.assertIn("proposals: { publish: true }", self.configuration)

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
            for word in ("Agree", "Disagree"):
                self.assertNotIn(word, text, page.name)
            if page.name == "topic-voice-agents.md":
                self.assertNotIn("dsp_nadia", text)
            self.assertIsNone(re.search(r"(?i)\bdesk\b|anthus", text), page.name)

    def test_beats_are_beats_and_the_index_counts_topics(self):
        for name in ("topic-open-tts.md", "topic-decision-models.md"):
            text = self._text(name)
            self.assertIn("Sub-concepts", text)
            self.assertIn("FOLLOWED AS A BEAT", text)
            self.assertNotIn("Concepts in this topic", text)
        for name in ("home.md", "new.md", "rising.md"):
            self.assertNotIn("All {n} topics", (STATIC_DIRECTORY / "pages" / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

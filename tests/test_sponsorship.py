import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

import reader_privacy  # noqa: E402
from sponsorship_content import write_extended_content  # noqa: E402

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIRECTORY = REPOSITORY_ROOT / "web"
KNOWLEDGE_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "knowledge"
BASE_CONTENT_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "content"
PAPYRUS_AVAILABLE = (Path(sys.executable).parent / "papyrus").exists() or shutil.which("papyrus")
BANNED_WORDS = ("desk", "vapor", "hype gap")
SOLUTION_KEYS = ("cyclotron", "auritus", "chatticus", "biblicus", "papyrus", "generic")
UNIT_TYPES = ("bar", "banner", "card", "note", "row")
BAR_ONLY_PAGES = ("proposals", "submit", "sign-in", "policies", "rising", "stories", "wiki", "roundup")
BEYOND_THE_BAR_LIMITS = {"front": 3, "signal": 3, "story": 3, "concept": 3, "list": 3, "new": 3, "map": 1, "weekly": 1}
NO_GO_CLASSES = (
    "signal-ratings", "signal-dimension", "desk-evidence", "story-map-box", "story-react", "story-sources", "story-figure",
    "map-graph-main", "map-panel-river", "map-panel-graph-main", "front-proposals", "concept-proposals", "item-comments", "board-reader",
    "papyrus-reader-rating-row", "signal-actions", "story-vote-island", "story-lineage",
)
ALLOWED_UNIT_ATTRIBUTES = {"unit", "id", "name", "slot", "page-type", "topic", "match"}
ENGAGE_URL_PREFIX = "https://anth.us/engage/?solution="

VOID_ELEMENTS = {"br", "img", "hr", "input", "meta", "link", "path", "circle", "rect", "line", "polyline", "polygon", "source", "wbr", "stop", "use"}


class Node:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.parent = parent
        self.children = []

    @property
    def classes(self):
        return (self.attributes.get("class") or "").split()

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def descendants(self):
        for child in self.children:
            yield child
            yield from child.descendants()

    def find(self, tag=None, css_class=None):
        return [
            node for node in self.descendants()
            if (tag is None or node.tag == tag) and (css_class is None or css_class in node.classes)
        ]


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root", {}, None)
        self.current = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs), self.current)
        self.current.children.append(node)
        if tag not in VOID_ELEMENTS:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        self.current.children.append(Node(tag, dict(attrs), self.current))

    def handle_endtag(self, tag):
        node = self.current
        while node is not None and node.tag != tag:
            node = node.parent
        if node is not None and node.parent is not None:
            self.current = node.parent


def parse(page):
    builder = TreeBuilder()
    builder.feed(page)
    return builder.root


def units_of(root, unit_type=None):
    return [
        node for node in root.descendants()
        if "data-sponsor-unit" in node.attributes and (unit_type is None or node.attributes["data-sponsor-unit"] == unit_type)
    ]


def beyond_the_bar(root):
    return [node for node in units_of(root) if node.attributes["data-sponsor-unit"] != "bar"]


def _papyrus_executable():
    beside_interpreter = Path(sys.executable).parent / "papyrus"
    return str(beside_interpreter) if beside_interpreter.exists() else (shutil.which("papyrus") or "papyrus")


def _load_hooks():
    spec = importlib.util.spec_from_file_location("shipped_hooks_sponsorship_under_test", STATIC_DIRECTORY / "hooks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _project(content_directory, static_directory):
    output_directory = Path(tempfile.mkdtemp(prefix="shipped-sponsorship-"))
    result = subprocess.run(
        [
            _papyrus_executable(), "ops", "content", "project", "--all",
            "--from-dir", str(content_directory),
            "--static-dir", str(static_directory),
            "--knowledge-dir", str(KNOWLEDGE_DIRECTORY),
            "--out", str(output_directory),
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return output_directory


def _static_directory_with_sponsorship(enabled):
    directory = Path(tempfile.mkdtemp(prefix="shipped-sponsorship-static-")) / "web"
    shutil.copytree(STATIC_DIRECTORY, directory)
    configuration = json.loads((directory / "sponsorship.json").read_text(encoding="utf-8"))
    configuration["enabled"] = enabled
    (directory / "sponsorship.json").write_text(json.dumps(configuration), encoding="utf-8")
    return directory


def _page_path(output_directory, path):
    relative = path.parent.relative_to(output_directory).as_posix()
    return "/" if relative == "." else f"/{relative}/"


def _read_pages(output_directory):
    return {_page_path(output_directory, path): path.read_text(encoding="utf-8") for path in output_directory.rglob("index.html")}


def unit_at_edge(node, edge):
    while node is not None:
        if "data-sponsor-unit" in node.attributes:
            return True
        node = (node.children[edge] if node.children else None)
    return False


class SponsorshipConfigurationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.configuration = json.loads((STATIC_DIRECTORY / "sponsorship.json").read_text(encoding="utf-8"))

    def test_the_committed_configuration_is_switched_on(self):
        self.assertIs(self.configuration["enabled"], True)

    def test_the_two_disclosure_strings_are_the_designed_copy(self):
        disclosure = self.configuration["disclosure"]
        self.assertEqual(
            disclosure["short"],
            "Sponsored by Anthus, which publishes Shipped. Sponsorship never affects rankings, statuses or scores.",
        )
        self.assertEqual(
            disclosure["long"],
            "Sponsored by Anthus AI Solutions, which publishes Shipped. Anthus writes this unit; editors and AI do not. "
            "Sponsorship never affects rankings, statuses, scores, map changes or which proposals editors approve.",
        )
        self.assertEqual(disclosure["path"], "/policies/#sponsorship")

    def test_the_six_solutions_carry_the_designed_copy_and_landing_urls(self):
        solutions = self.configuration["solutions"]
        self.assertEqual(tuple(solutions), SOLUTION_KEYS)
        expected = {
            "cyclotron": ("https://cyclotron.anth.us", "Cyclotron"),
            "auritus": ("https://aurit.us", "Auritus"),
            "chatticus": ("https://chattic.us", "Chatticus"),
            "biblicus": ("https://anth.us/platform/biblicus/", "Biblicus"),
            "papyrus": ("https://p.apyr.us", "Papyrus"),
        }
        for key, (primary, name) in expected.items():
            with self.subTest(solution=key):
                self.assertEqual(solutions[key]["primary"]["url"], primary)
                self.assertEqual(solutions[key]["secondary"]["url"], f"{ENGAGE_URL_PREFIX}{name}")
                self.assertEqual(solutions[key]["secondary"]["label"], "Talk to Anthus")
        generic = solutions["generic"]
        self.assertEqual((generic["primary"]["label"], generic["primary"]["url"]), ("Talk to Anthus", "https://anth.us/engage/"))
        self.assertEqual((generic["secondary"]["label"], generic["secondary"]["url"]), ("See all solutions", "https://anth.us/ai-solutions/"))
        self.assertEqual(solutions["cyclotron"]["note"], "Working with decision models? Anthus built Cyclotron for that")
        self.assertEqual(solutions["papyrus"]["cardPitch"], "Automated publishing and insight feeds. Shipped runs on it.")

    def test_every_solution_has_every_copy_field_and_matching_keywords_live_in_the_file(self):
        fields = {"topic", "name", "mark", "pitch", "description", "cardPitch", "rowPitch", "note", "primary", "secondary", "rowAction", "match"}
        for key, solution in self.configuration["solutions"].items():
            with self.subTest(solution=key):
                self.assertLessEqual(fields, set(solution))
                self.assertIn("topics", solution["match"])
                self.assertIn("keywords", solution["match"])
                if key != "generic":
                    self.assertTrue(solution["match"]["topics"] and solution["match"]["keywords"])

    def test_the_bar_is_meet_anthus_to_the_solutions_page(self):
        bar = self.configuration["bar"]
        self.assertEqual((bar["actionLabel"], bar["actionUrl"]), ("Meet Anthus", "https://anth.us/ai-solutions/"))
        self.assertEqual(bar["presenter"], "Presented by Anthus AI Solutions")
        self.assertEqual(bar["presenterShort"], "Presented by Anthus")

    def test_the_footer_names_the_publisher_and_links_the_sponsorship_policy(self):
        footer = self.configuration["footer"]
        self.assertEqual(footer["line"], "Published by Anthus AI Solutions, which also sponsors it.")
        self.assertEqual((footer["linkLabel"], footer["linkPath"]), ("Sponsorship and independence", "/policies/#sponsorship"))

    def test_the_configuration_style_and_script_files_avoid_the_banned_words(self):
        for name in ("sponsorship.json", "assets/shipped-sponsorship.css", "assets/shipped-sponsorship.js"):
            text = (STATIC_DIRECTORY / name).read_text(encoding="utf-8").lower()
            for word in BANNED_WORDS:
                with self.subTest(file=name, word=word):
                    self.assertNotIn(word, text)


class SponsorshipLogicTest(unittest.TestCase):
    def setUp(self):
        self.hooks = _load_hooks()
        self.directory = Path(tempfile.mkdtemp(prefix="shipped-sponsorship-config-"))
        self.addCleanup(shutil.rmtree, self.directory, ignore_errors=True)

    def _enable(self, enabled=True):
        configuration = json.loads((STATIC_DIRECTORY / "sponsorship.json").read_text(encoding="utf-8"))
        configuration["enabled"] = enabled
        path = self.directory / "sponsorship.json"
        path.write_text(json.dumps(configuration), encoding="utf-8")
        self.hooks.SPONSORSHIP_PATH = path
        self.hooks._sponsorship.cache_clear()
        self.hooks._sponsorship_rules.cache_clear()

    def _best(self, profile):
        return self.hooks._sponsorship_candidates(profile)[0]["key"]

    def test_decision_models_match_cyclotron(self):
        self.assertEqual(self._best([("topic", "decision-models"), ("name", "guardrail model")]), "cyclotron")
        self.assertEqual(self._best([("topic", "decisions")]), "cyclotron")

    def test_speech_and_tts_match_auritus(self):
        self.assertEqual(self._best([("topic", "open-tts"), ("name", "text to speech")]), "auritus")
        self.assertEqual(self._best([("title", "A 99M on-device TTS in 31 languages")]), "auritus")

    def test_chat_and_agents_match_chatticus(self):
        self.assertEqual(self._best([("name", "voice agents"), ("title", "A new chat assistant")]), "chatticus")
        self.assertEqual(self._best([("topic", "agents")]), "chatticus")

    def test_topic_modelling_and_knowledge_bases_match_biblicus(self):
        self.assertEqual(self._best([("name", "knowledge graph"), ("cluster", "topic model of a corpus")]), "biblicus")
        self.assertEqual(self._best([("topic", "map")]), "biblicus")

    def test_automated_publishing_and_insight_feeds_match_papyrus(self):
        self.assertEqual(self._best([("topic", "weekly")]), "papyrus")
        self.assertEqual(self._best([("title", "An automated publishing engine")]), "papyrus")

    def test_a_page_with_no_match_falls_back_to_the_generic_unit_only(self):
        candidates = self.hooks._sponsorship_candidates([("topic", "fixture-misc"), ("name", "fixture thing")])
        self.assertEqual([candidate["key"] for candidate in candidates], ["generic"])
        self.assertEqual(candidates[0]["match"], "fallback")
        self.assertEqual(candidates[0]["topic"], "none")

    def test_a_matched_solution_reports_its_topic_and_the_generic_unit_always_comes_last(self):
        candidates = self.hooks._sponsorship_candidates([("topic", "open-tts"), ("name", "chat assistant")])
        self.assertEqual([candidate["key"] for candidate in candidates], ["auritus", "chatticus", "generic"])
        self.assertEqual((candidates[0]["match"], candidates[0]["topic"]), ("topic", "open-tts"))
        self.assertEqual(candidates[1]["match"], "topic")

    def test_a_stronger_source_outranks_a_weaker_one(self):
        profile = [("topic", "decision-models"), ("title", "a text to speech model"), ("title", "tts voices")]
        self.assertEqual(self._best(profile), "cyclotron")

    def test_keywords_match_whole_words_only(self):
        self.assertEqual([c["key"] for c in self.hooks._sponsorship_candidates([("title", "Strategist outlines assassin ragged arcs")])], ["generic"])

    def test_claiming_never_hands_out_a_solution_twice_and_runs_dry_after_the_generic_unit(self):
        candidates = self.hooks._sponsorship_candidates([("topic", "decision-models")])
        taken = set()
        claimed = [self.hooks._sponsorship_claim(candidates, taken) for _ in range(3)]
        self.assertEqual([candidate["key"] if candidate else None for candidate in claimed], ["cyclotron", "generic", None])

    def test_urls_gain_the_utm_parameters_and_keep_an_existing_query(self):
        url = self.hooks._sponsorship_url("https://anth.us/engage/?solution=Cyclotron", "cyclotron", "banner", "signal", "decision-models")
        query = parse_qs(urlsplit(url).query)
        self.assertEqual(
            query,
            {
                "solution": ["Cyclotron"], "utm_source": ["shipped"], "utm_medium": ["sponsored"], "utm_campaign": ["cyclotron"],
                "utm_content": ["banner-signal"], "utm_term": ["decision-models"],
            },
        )
        self.assertEqual(url.count("?"), 1)
        self.assertTrue(url.startswith("https://anth.us/engage/?solution=Cyclotron&utm_source=shipped"))

    def test_urls_without_a_path_or_a_topic_get_a_root_path_and_a_none_term(self):
        url = self.hooks._sponsorship_url("https://cyclotron.anth.us", "generic", "row", "new", "none")
        self.assertTrue(url.startswith("https://cyclotron.anth.us/?utm_source=shipped&utm_medium=sponsored&utm_campaign=generic&utm_content=row-new&utm_term=none"))

    def test_row_positions_follow_one_per_ten_with_a_cap_and_never_in_the_first_three(self):
        positions = self.hooks._sponsorship_row_positions
        self.assertEqual(positions(5, "list"), [])
        self.assertEqual(positions(10, "list"), [10])
        self.assertEqual(positions(45, "list"), [10, 20, 30])
        self.assertEqual(positions(200, "new"), [10, 20, 30])
        self.assertEqual(positions(30, "front"), [10, 20])
        self.assertEqual(positions(10, "concept"), [5])
        for page_type in ("front", "new", "list", "concept"):
            self.assertTrue(all(position >= 3 for position in positions(500, page_type)))

    def test_the_element_scanner_finds_the_close_of_nested_elements(self):
        html = '<div class="a"><div class="b"></div><p>x</p></div><div class="c"></div>'
        self.assertEqual(html[: self.hooks._sponsorship_element_end(html, 0)], '<div class="a"><div class="b"></div><p>x</p></div>')

    def test_nothing_changes_when_sponsorship_is_switched_off(self):
        self._enable(False)
        html = '<body><header class="markus-site-masthead"></header></body>'
        self.assertEqual(self.hooks._sponsorship_finish(html, object()), html)
        self.assertEqual(self.hooks.head_extra(None).count("sponsorship"), 0)
        self.assertEqual(self.hooks._footer_links(), self.hooks.FOOTER_LINKS)
        self.assertEqual(self.hooks._footer_text_html(), "Published by Anthus AI Solutions.")

    def test_the_footer_links_and_text_follow_the_switch(self):
        self._enable(True)
        self.assertIn("/assets/shipped-sponsorship.css", self.hooks.head_extra(None))
        self.assertIn("/assets/shipped-sponsorship.js", self.hooks.head_extra(None))
        footer = self.hooks.footer(None)
        self.assertIn("Published by Anthus AI Solutions, which also sponsors it.", footer)
        self.assertIn('<a href="/policies/#sponsorship">Sponsorship and independence</a>', footer)
        self.assertIn('<li><a href="/policies/#sponsorship">Sponsorship</a></li>', footer)
        for label, href in self.hooks.FOOTER_LINKS:
            self.assertIn(f'<li><a href="{href}">{label}</a></li>', footer)

    def test_every_unit_builder_shows_the_word_the_diamond_and_the_anthus_name(self):
        self._enable(True)
        candidate = {"key": "cyclotron", "topic": "decision-models", "match": "topic"}
        builders = (
            self.hooks._sponsorship_banner_html, self.hooks._sponsorship_card_html, self.hooks._sponsorship_note_html, self.hooks._sponsorship_row_html,
        )
        for builder in builders:
            with self.subTest(builder=builder.__name__):
                html = builder(candidate, "signal", "slot")
                self.assertIn("Sponsored", html)
                self.assertIn("M5 0.5L9.5 5L5 9.5L0.5 5z", html)
                self.assertRegex(html, r"Anthus")
                self.assertIn('rel="sponsored noopener"', html)
                self.assertNotIn("<script", html)
        bar = self.hooks._sponsorship_bar_html("signal")
        self.assertIn("Sponsored", bar)
        self.assertIn("M5 0.5L9.5 5L5 9.5L0.5 5z", bar)
        self.assertIn("Presented by Anthus AI Solutions", bar)

    def test_unit_markup_escapes_configuration_text(self):
        self._enable(True)
        configuration = json.loads(self.hooks.SPONSORSHIP_PATH.read_text(encoding="utf-8"))
        configuration["solutions"]["cyclotron"]["pitch"] = '<img src=x onerror="alert(1)">'
        self.hooks.SPONSORSHIP_PATH.write_text(json.dumps(configuration), encoding="utf-8")
        self.hooks._sponsorship.cache_clear()
        html = self.hooks._sponsorship_banner_html({"key": "cyclotron", "topic": "none", "match": "fallback"}, "signal", "slot")
        self.assertNotIn("<img", html)
        self.assertIn("&lt;img", html)


@unittest.skipUnless(PAPYRUS_AVAILABLE, "the papyrus command from papyrus-newsroom is not installed")
class SponsorshipSwitchedOffTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.static_directory = _static_directory_with_sponsorship(False)
        cls.output_directory = _project(BASE_CONTENT_DIRECTORY, cls.static_directory)
        cls.pages = _read_pages(cls.output_directory)

    @classmethod
    def tearDownClass(cls):
        for directory in (cls.output_directory, cls.static_directory.parent):
            shutil.rmtree(directory, ignore_errors=True)

    def test_no_page_carries_a_unit_a_sponsorship_style_or_a_sponsorship_script(self):
        self.assertTrue(self.pages)
        for name, page in self.pages.items():
            with self.subTest(page=name):
                for needle in ("data-sponsor", "sp-bar", "sp-card", "sp-pill", "shipped-sponsorship", "Sponsored"):
                    self.assertNotIn(needle, page)

    def test_the_footer_is_exactly_what_it_was(self):
        for name, page in self.pages.items():
            with self.subTest(page=name):
                self.assertIn('<p class="markus-footer-text">Published by Anthus AI Solutions.</p>', page)
                self.assertNotIn("sponsors it", page)
                self.assertNotIn("policies/#sponsorship", page)
                self.assertIn('<li><a href="/policies/">Policies</a></li><li><a href="/roundup/">All issues</a></li>', page)

    def test_the_projection_stylesheet_list_does_not_name_the_sponsorship_style(self):
        settings = (STATIC_DIRECTORY / "projection.json").read_text(encoding="utf-8")
        self.assertNotIn("sponsorship", settings)


@unittest.skipUnless(PAPYRUS_AVAILABLE, "the papyrus command from papyrus-newsroom is not installed")
class SponsorshipSwitchedOnTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.static_directory = _static_directory_with_sponsorship(True)
        cls.content_directory = write_extended_content(Path(tempfile.mkdtemp(prefix="shipped-sponsorship-content-")) / "content")
        cls.output_directory = _project(cls.content_directory, cls.static_directory)
        cls.pages = _read_pages(cls.output_directory)
        cls.trees = {name: parse(page) for name, page in cls.pages.items()}

    @classmethod
    def tearDownClass(cls):
        for directory in (cls.output_directory, cls.static_directory.parent, cls.content_directory.parent):
            shutil.rmtree(directory, ignore_errors=True)

    def _units(self, name, unit_type=None):
        return units_of(self.trees[name], unit_type)

    def _beyond(self, name):
        return beyond_the_bar(self.trees[name])

    def _solutions(self, name):
        return [unit.attributes["data-sponsor-id"] for unit in self._beyond(name)]

    def test_every_page_carries_exactly_one_bar_before_the_masthead_and_loads_the_style_and_script(self):
        for name, page in self.pages.items():
            with self.subTest(page=name):
                self.assertEqual(len(self._units(name, "bar")), 1)
                self.assertLess(page.index('data-sponsor-unit="bar"'), page.index('<header class="markus-site-masthead"'))
                self.assertIn('<link rel="stylesheet" href="/assets/shipped-sponsorship.css">', page)
                self.assertIn('<script src="/assets/shipped-sponsorship.js" defer></script>', page)

    def test_the_bar_is_never_sticky_and_drops_its_line_on_phones_while_keeping_the_action(self):
        stylesheet = (STATIC_DIRECTORY / "assets" / "shipped-sponsorship.css").read_text(encoding="utf-8")
        self.assertNotRegex(stylesheet, r"position:\s*(sticky|fixed)")
        self.assertRegex(stylesheet, r"@media \(max-width:720px\)\{\s*\.sp-bar-line\{display:none\}")
        self.assertNotRegex(stylesheet, r"\.sp-bar-action\{[^}]*display:none")

    def test_proposals_submit_sign_in_and_policies_carry_the_bar_only(self):
        for name in ("/proposals/", "/submit/", "/sign-in/", "/policies/", "/rising/", "/stories/", "/wiki/", "/roundup/", "/roundup/fixture-issue-one/"):
            with self.subTest(page=name):
                self.assertEqual(self._beyond(name), [])

    def test_the_bar_says_sponsored_with_a_diamond_and_names_anthus_in_full_and_short_form(self):
        bar = self._units("/submit/", "bar")[0]
        text = " ".join(self.pages["/submit/"].split('data-sponsor-unit="bar"')[1].split("</aside>")[0].split())
        self.assertIn("Sponsored", text)
        self.assertIn("Presented by Anthus AI Solutions", text)
        self.assertIn("Presented by Anthus<", text)
        self.assertIn("Meet Anthus", text)
        self.assertEqual(bar.attributes["data-sponsor-id"], "anthus")
        self.assertIn("M5 0.5L9.5 5L5 9.5L0.5 5z", self.pages["/submit/"])

    def test_no_page_exceeds_its_density_cap_beyond_the_bar(self):
        for name, tree in self.trees.items():
            beyond = beyond_the_bar(tree)
            page_types = {unit.attributes["data-sponsor-page-type"] for unit in beyond}
            for page_type in page_types:
                with self.subTest(page=name, page_type=page_type):
                    self.assertLessEqual(len(beyond), BEYOND_THE_BAR_LIMITS[page_type])
            self.assertLessEqual(len(beyond), 3, name)

    def test_no_solution_appears_in_two_units_on_one_page(self):
        for name in self.pages:
            with self.subTest(page=name):
                solutions = self._solutions(name)
                self.assertEqual(len(solutions), len(set(solutions)), solutions)

    def test_no_unit_sits_next_to_another_unit(self):
        for name, tree in self.trees.items():
            for unit in beyond_the_bar(tree):
                anchor = unit.parent if "sp-item" in unit.parent.classes else unit
                siblings = anchor.parent.children
                position = siblings.index(anchor)
                before = siblings[position - 1] if position > 0 else None
                after = siblings[position + 1] if position + 1 < len(siblings) else None
                with self.subTest(page=name, unit=unit.attributes["data-sponsor-unit"]):
                    self.assertFalse(unit_at_edge(before, -1))
                    self.assertFalse(unit_at_edge(after, 0))

    def test_no_unit_sits_inside_a_no_go_zone(self):
        for name, tree in self.trees.items():
            for unit in beyond_the_bar(tree):
                with self.subTest(page=name, unit=unit.attributes["data-sponsor-unit"]):
                    forbidden = [ancestor for ancestor in unit.ancestors() if set(ancestor.classes) & set(NO_GO_CLASSES)]
                    self.assertEqual(forbidden, [])
                    self.assertEqual([node for node in unit.descendants() if node.attributes.get("data-island")], [])

    def test_a_unit_carries_the_four_cues_in_its_own_markup(self):
        for name, tree in self.trees.items():
            for unit in beyond_the_bar(tree):
                with self.subTest(page=name, unit=unit.attributes["data-sponsor-unit"]):
                    self.assertTrue(unit.find(css_class="sp-pill"))
                    self.assertTrue(unit.find("svg"))
                    self.assertIn("sp-card", unit.classes)
                    self.assertTrue(unit.attributes["aria-label"].startswith("Sponsored: "))

    def test_a_signal_page_gets_a_note_after_on_the_map_a_banner_at_the_end_of_the_main_column_and_a_card_last_in_the_rail(self):
        name = "/open-weights/fixture-full-contract/"
        tree = self.trees[name]
        main = tree.find(css_class="signal-main")[0]
        sections = [child for child in main.children if child.tag in ("section", "aside", "article")]
        labels = [child.attributes.get("data-sponsor-unit") or child.attributes.get("aria-labelledby") for child in sections]
        self.assertEqual(labels[labels.index("signal-map-h") + 1], "note")
        self.assertEqual(labels[-1], "banner")
        self.assertEqual(self._solutions(name), ["auritus", "generic"])
        card = self._units("/decisions/extra-decision-00/", "card")
        self.assertEqual(card, [])
        rail_card = [unit for unit in self._units("/decisions/fixture-guard-one/", "card")]
        self.assertEqual(len(rail_card), 1)
        rail = rail_card[0].parent
        self.assertIn("signal-rail", rail.classes)
        self.assertIs(rail.children[-1], rail_card[0])
        self.assertTrue(any(child.tag == "section" for child in rail.children))

    def test_a_signal_page_without_an_on_the_map_section_gets_no_note(self):
        self.assertEqual(self._units("/decisions/fixture-guard-one/", "note"), [])

    def test_a_story_gets_its_note_after_paragraph_two_its_banner_after_the_body_and_its_card_after_the_sources(self):
        name = "/stories/extra-long-story/"
        tree = self.trees[name]
        body = tree.find(css_class="story-body")[0]
        self.assertEqual([child.tag for child in body.children], ["p", "p", "aside", "p", "p", "p"])
        article = tree.find(css_class="story-article")[0]
        order = [child.attributes.get("data-sponsor-unit") or (child.classes[0] if child.classes else child.tag) for child in article.children]
        self.assertEqual(order[order.index("story-body") + 1], "banner")
        self.assertEqual(order[-1], "card")
        self.assertEqual(self._solutions(name), ["cyclotron", "auritus", "generic"])

    def test_a_story_too_short_for_a_note_or_without_a_rail_carries_what_fits(self):
        name = "/stories/fixture-story-newest/"
        self.assertEqual(self._units(name, "note"), [])
        self.assertEqual([unit.attributes["data-sponsor-unit"] for unit in self._beyond(name)], ["banner", "card"])

    def test_a_story_that_spans_two_topics_may_feature_two_solutions(self):
        solutions = self._solutions("/stories/extra-long-story/")
        self.assertIn("cyclotron", solutions)
        self.assertIn("auritus", solutions)

    def test_a_topic_page_gets_a_banner_between_sections_and_a_card_in_its_rail(self):
        for name, solution in (("/topics/decision-models/", "cyclotron"), ("/topics/open-tts/", "auritus")):
            with self.subTest(page=name):
                tree = self.trees[name]
                rows = tree.find(css_class="concept-row")
                banner = self._units(name, "banner")[0]
                self.assertEqual(banner.attributes["data-sponsor-id"], solution)
                self.assertIs(banner.parent.children[banner.parent.children.index(rows[0]) + 1], banner)
                card = self._units(name, "card")[0]
                self.assertIn("sp-rail", card.parent.classes)
                self.assertIs(card.parent.children[-1], card)

    def test_the_front_page_puts_its_card_last_in_the_rising_rail_and_at_most_two_rows_in_the_latest_list(self):
        name = "/"
        card = self._units(name, "card")[0]
        self.assertIn("front-rising-rail", card.parent.classes)
        self.assertIs(card.parent.children[-1], card)
        self.assertIn("front-rising", card.parent.children[0].classes)
        self.assertLessEqual(len(self._units(name, "row")), 2)
        row_slots = [unit.attributes["data-sponsor-slot"] for unit in self._units(name, "row")]
        self.assertEqual(row_slots, ["after-signal-10"])

    def test_the_new_page_gets_rows_after_every_tenth_signal_capped_at_three_never_in_the_first_three_and_never_two_in_a_row(self):
        name = "/new/"
        tree = self.trees[name]
        board = tree.find(css_class="board-list")[0]
        kinds = ["row" if "sp-item" in child.classes else "signal" for child in board.children]
        self.assertEqual(kinds.count("row"), 3)
        rows_at = [index for index, kind in enumerate(kinds) if kind == "row"]
        self.assertTrue(all(index >= 3 for index in rows_at))
        self.assertTrue(all(second - first > 1 for first, second in zip(rows_at, rows_at[1:])))
        self.assertEqual(rows_at, [10, 21, 32])
        solutions = self._solutions(name)
        self.assertEqual(len(set(solutions)), 3)

    def test_a_section_list_gets_a_row_matched_to_the_signals_around_it(self):
        self.assertEqual([unit.attributes["data-sponsor-id"] for unit in self._beyond("/decisions/")], ["cyclotron"])
        self.assertEqual([unit.attributes["data-sponsor-id"] for unit in self._beyond("/open-weights/")], ["auritus"])
        self.assertEqual(self._beyond("/shipped/"), [])

    def test_the_map_carries_one_card_below_new_on_the_map(self):
        name = "/map/"
        self.assertEqual([unit.attributes["data-sponsor-unit"] for unit in self._beyond(name)], ["card"])
        card = self._units(name, "card")[0]
        self.assertEqual(card.attributes["data-sponsor-id"], "biblicus")
        self.assertIn("map-new", card.parent.children[0].classes)
        self.assertIs(card.parent.children[1], card)

    def test_the_weekly_web_issue_gets_one_banner_after_part_three(self):
        name = "/sample/roundup/"
        banner = self._units(name, "banner")[0]
        self.assertEqual(banner.attributes["data-sponsor-id"], "papyrus")
        parts = [child for child in banner.parent.children if "weekly-part" in child.classes]
        siblings = banner.parent.children
        self.assertIs(siblings[siblings.index(parts[2]) + 1], banner)
        self.assertEqual(len(self._beyond(name)), 1)

    def test_a_page_with_no_topic_match_gets_the_generic_unit_marked_as_a_fallback(self):
        note = self._units("/stories/extra-plain-story/", "note")[0]
        self.assertEqual(note.attributes["data-sponsor-id"], "generic")
        self.assertEqual(note.attributes["data-sponsor-match"], "fallback")
        self.assertEqual(note.attributes["data-sponsor-topic"], "none")
        self.assertEqual(note.attributes["data-sponsor-name"], "Anthus AI Solutions")

    def test_a_matched_unit_reports_the_topic_that_matched(self):
        banner = self._units("/topics/decision-models/", "banner")[0]
        self.assertEqual(banner.attributes["data-sponsor-match"], "topic")
        self.assertEqual(banner.attributes["data-sponsor-topic"], "decision-models")
        self.assertEqual(banner.attributes["data-sponsor-slot"], "between-sections")

    def test_a_unit_carries_only_the_allowed_data_attributes(self):
        for name, tree in self.trees.items():
            for unit in units_of(tree):
                with self.subTest(page=name):
                    fields = {key[len("data-sponsor-"):] for key in unit.attributes if key.startswith("data-sponsor-")}
                    self.assertLessEqual(fields, ALLOWED_UNIT_ATTRIBUTES)
                    self.assertEqual(fields, ALLOWED_UNIT_ATTRIBUTES)

    def test_every_sponsored_link_is_marked_sponsored_noopener_and_carries_the_utm_parameters(self):
        checked = 0
        for name, tree in self.trees.items():
            for unit in units_of(tree):
                for link in unit.find("a"):
                    href = link.attributes["href"]
                    if href.startswith("/"):
                        self.assertNotIn("data-sponsor-action", link.attributes)
                        continue
                    checked += 1
                    with self.subTest(page=name, href=href):
                        self.assertEqual(link.attributes["rel"], "sponsored noopener")
                        self.assertIn(link.attributes["data-sponsor-action"], ("primary", "secondary"))
                        query = parse_qs(urlsplit(href).query)
                        self.assertEqual(query["utm_source"], ["shipped"])
                        self.assertEqual(query["utm_medium"], ["sponsored"])
                        self.assertEqual(query["utm_campaign"], [unit.attributes["data-sponsor-id"]])
                        self.assertEqual(query["utm_content"], [f'{unit.attributes["data-sponsor-unit"]}-{unit.attributes["data-sponsor-page-type"]}'])
                        self.assertEqual(query["utm_term"], [unit.attributes["data-sponsor-topic"]])
                        self.assertEqual(href.count("?"), 1)
        self.assertGreater(checked, 40)

    def test_the_engage_links_keep_their_solution_query_beside_the_utm_parameters(self):
        banner = self._units("/topics/decision-models/", "banner")[0]
        secondary = [link for link in banner.find("a") if link.attributes.get("data-sponsor-action") == "secondary"][0]
        self.assertTrue(secondary.attributes["href"].startswith("https://anth.us/engage/?solution=Cyclotron&utm_source=shipped&utm_medium=sponsored&utm_campaign=cyclotron&utm_content=banner-concept&utm_term=decision-models"))

    def test_the_bar_links_to_the_solutions_page_with_a_bar_campaign(self):
        link = self._units("/map/", "bar")[0].find("a")[0]
        query = parse_qs(urlsplit(link.attributes["href"]).query)
        self.assertTrue(link.attributes["href"].startswith("https://anth.us/ai-solutions/?utm_source=shipped"))
        self.assertEqual(query["utm_content"], ["bar-map"])
        self.assertEqual(query["utm_campaign"], ["anthus"])
        self.assertEqual(query["utm_term"], ["none"])
        self.assertEqual(link.attributes["rel"], "sponsored noopener")

    def test_the_disclosure_lines_link_to_the_sponsorship_policy(self):
        for name in ("/topics/decision-models/", "/stories/extra-long-story/", "/new/"):
            for unit in self._beyond(name):
                with self.subTest(page=name, unit=unit.attributes["data-sponsor-unit"]):
                    self.assertIn("/policies/#sponsorship", [link.attributes["href"] for link in unit.find("a")])
        banner = self._units("/topics/decision-models/", "banner")[0]
        self.assertIn("Sponsored by Anthus AI Solutions, which publishes Shipped.", self.pages["/topics/decision-models/"])
        self.assertTrue(banner.find(css_class="sp-disc-long"))
        self.assertTrue(banner.find(css_class="sp-disc-short"))

    def test_the_footer_names_the_publisher_and_links_the_sponsorship_policy_and_keeps_the_other_links(self):
        for name, page in self.pages.items():
            with self.subTest(page=name):
                self.assertIn('<p class="markus-footer-text">Published by Anthus AI Solutions, which also sponsors it. <a href="/policies/#sponsorship">Sponsorship and independence</a></p>', page)
                self.assertIn('<li><a href="/policies/#sponsorship">Sponsorship</a></li>', page)
                for href in ("/map/", "/policies/#steering", "/policies/", "/roundup/", "/feed.xml", "/policies/#privacy", "#cookie-settings"):
                    self.assertIn(f'<li><a href="{href}">', page)
                footer = page.split('<footer class="markus-site-footer">')[1]
                self.assertNotIn("sp-pill", footer)

    def test_the_sponsorship_script_and_style_are_published_and_the_script_reads_data_attributes_only(self):
        script = (self.output_directory / "assets" / "shipped-sponsorship.js").read_text(encoding="utf-8")
        for needle in ("view_promotion", "select_promotion", "IntersectionObserver", "typeof window.gtag === 'function'", "VISIBLE_RATIO = 0.5", "VISIBLE_MILLISECONDS = 1000"):
            self.assertIn(needle, script)
        self.assertTrue((self.output_directory / "assets" / "shipped-sponsorship.css").is_file())

    def test_the_whole_switched_on_site_and_its_script_pass_the_reader_privacy_scan(self):
        files = dict(self.pages)
        files["assets/shipped-sponsorship.js"] = (self.output_directory / "assets" / "shipped-sponsorship.js").read_text(encoding="utf-8")
        self.assertEqual(reader_privacy.scan_files(files), {})


if __name__ == "__main__":
    unittest.main()

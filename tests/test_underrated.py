import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIRECTORY = REPOSITORY_ROOT / "web"
UNDERRATED_CONTENT_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "underrated-content"
UNDERRATED_KNOWLEDGE_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "underrated-knowledge"
PLAIN_CONTENT_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "content"
PLAIN_KNOWLEDGE_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "knowledge"


def _papyrus_executable():
    beside_interpreter = Path(sys.executable).parent / "papyrus"
    if beside_interpreter.exists():
        return str(beside_interpreter)
    return shutil.which("papyrus") or "papyrus"


def _load_hooks():
    spec = importlib.util.spec_from_file_location("shipped_hooks_for_underrated", STATIC_DIRECTORY / "hooks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _project(content_directory, knowledge_directory):
    output_directory = Path(tempfile.mkdtemp(prefix="shipped-underrated-"))
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


def _record(item_id, useful, ready, entity_keys=(), beat_key=None, sort_date="2026-10-10", title=None):
    return {
        "item_id": item_id,
        "title": title or item_id,
        "url": f"/decisions/{item_id}/",
        "useful": useful,
        "ready": ready,
        "agent_scored": True,
        "scoring_label": None,
        "entities": {key: ("task", key) for key in entity_keys},
        "beat_key": beat_key,
        "beat_label": "Decision models" if beat_key else None,
        "sort_date": sort_date,
    }


class UnderratedRuleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hooks = _load_hooks()
        cls.rule = cls.hooks._underrated_rule()

    def _underrated_ids(self, records):
        counts = self.hooks._mention_counts(records)
        return [record["item_id"] for record in self.hooks._underrated_signals(records, counts, self.rule)]

    def test_a_strong_signal_with_few_mentions_is_underrated(self):
        records = [_record("quiet", 4.5, 4.0, ["alone"]), _record("other", 2.0, 2.0, ["elsewhere"])]
        self.assertEqual(self._underrated_ids(records), ["quiet"])

    def test_a_strong_signal_with_many_mentions_is_not_underrated(self):
        crowd = [_record(f"crowd-{number}", 2.0, 2.0, ["busy"]) for number in range(8)]
        records = [_record("popular", 5.0, 5.0, ["busy"]), _record("quiet", 4.0, 4.0, ["alone"])] + crowd
        self.assertEqual(self._underrated_ids(records), ["quiet"])

    def test_the_mention_ceiling_applies_even_when_every_qualifier_is_busy(self):
        crowd = [_record(f"crowd-{number}", 2.0, 2.0, ["busy"]) for number in range(8)]
        records = [_record("popular", 5.0, 5.0, ["busy"])] + crowd
        self.assertEqual(self._underrated_ids(records), [])

    def test_low_ready_is_not_underrated_however_quiet(self):
        records = [_record("hard-to-adopt", 4.5, 3.5, ["alone"]), _record("other", 2.0, 2.0, ["elsewhere"])]
        self.assertEqual(self._underrated_ids(records), [])

    def test_low_useful_is_not_underrated_however_quiet(self):
        self.assertEqual(self._underrated_ids([_record("minor", 3.5, 4.5, ["alone"])]), [])

    def test_an_item_without_scores_is_never_underrated(self):
        self.assertEqual(self._underrated_ids([_record("unrated", None, None, ["alone"])]), [])

    def test_the_quiet_share_keeps_only_the_quietest_third_of_qualifiers(self):
        shared_by_three = [f"group-{number}" for number in range(3)]
        records = [_record(f"quiet-{number}", 4.0, 4.0, [f"solo-{number}"]) for number in range(3)]
        for count, key in enumerate(shared_by_three, start=1):
            records += [_record(f"{key}-{member}", 4.0, 4.0, [key]) for member in range(count + 1)]
        counts = self.hooks._mention_counts(records)
        qualifying_counts = sorted(counts[record["item_id"]] for record in records)
        self.assertEqual(self.hooks._quiet_mention_limit(qualifying_counts, self.rule), 1)
        quiet = self._underrated_ids(records)
        self.assertTrue(all(counts[item_id] <= 1 for item_id in quiet))
        self.assertIn("quiet-0", quiet)
        self.assertNotIn("group-2-0", quiet)

    def test_mentions_count_other_signals_sharing_any_entity_once(self):
        records = [
            _record("a", 4.0, 4.0, ["x", "y"]),
            _record("b", 1.0, 1.0, ["x", "y"]),
            _record("c", 1.0, 1.0, ["y"]),
            _record("d", 1.0, 1.0, ["z"]),
        ]
        counts = self.hooks._mention_counts(records)
        self.assertEqual(counts, {"a": 2, "b": 2, "c": 2, "d": 0})

    def test_the_threshold_numbers_come_from_the_publication_data(self):
        self.assertEqual(
            sorted(self.rule), ["homeLimit", "mentionCeiling", "minimumReady", "minimumUseful", "quietestShare"]
        )
        self.assertEqual((self.rule["minimumUseful"], self.rule["minimumReady"]), (4, 4))

    def test_the_figures_read_useful_ready_and_mentions(self):
        record = _record("quiet", 4.5, 4.0)
        self.assertEqual(self.hooks._underrated_figures_text(record, 3), "Useful 4.5 · Ready 4.0 · 3 mentions")
        self.assertEqual(self.hooks._underrated_figures_text(record, 1), "Useful 4.5 · Ready 4.0 · 1 mention")


class NearbyOrderingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hooks = _load_hooks()

    def _nearby(self, record, records, limit=5):
        return [(entry["record"]["item_id"], entry["why"]) for entry in self.hooks._nearby_signals(record, records, limit)]

    def test_more_shared_entities_rank_first_then_the_same_beat_then_newest(self):
        subject = _record("subject", 3, 3, ["maker", "task"], beat_key="decision-models")
        records = [
            subject,
            _record("shares-one-old", 3, 3, ["maker"], sort_date="2026-10-01"),
            _record("shares-one-new", 3, 3, ["task"], sort_date="2026-10-09"),
            _record("shares-both", 3, 3, ["maker", "task"], sort_date="2026-10-02"),
            _record("same-beat-only", 3, 3, [], beat_key="decision-models", sort_date="2026-10-05"),
            _record("unrelated", 3, 3, ["elsewhere"], beat_key="open-tts"),
        ]
        self.assertEqual(
            [item_id for item_id, _why in self._nearby(subject, records)],
            ["shares-both", "shares-one-new", "shares-one-old", "same-beat-only"],
        )

    def test_a_shared_entity_in_the_same_beat_outranks_one_in_another_beat(self):
        subject = _record("subject", 3, 3, ["task"], beat_key="decision-models")
        records = [
            subject,
            _record("other-beat", 3, 3, ["task"], beat_key="open-tts", sort_date="2026-10-09"),
            _record("same-beat", 3, 3, ["task"], beat_key="decision-models", sort_date="2026-10-01"),
        ]
        self.assertEqual([item_id for item_id, _why in self._nearby(subject, records)], ["same-beat", "other-beat"])

    def test_the_limit_is_respected_and_the_signal_is_never_its_own_neighbour(self):
        subject = _record("subject", 3, 3, ["task"])
        records = [subject] + [_record(f"other-{number}", 3, 3, ["task"]) for number in range(9)]
        found = self._nearby(subject, records, limit=5)
        self.assertEqual(len(found), 5)
        self.assertNotIn("subject", [item_id for item_id, _why in found])

    def test_nothing_in_common_means_no_neighbours(self):
        subject = _record("subject", 3, 3, ["task"], beat_key="decision-models")
        self.assertEqual(self._nearby(subject, [subject, _record("far", 3, 3, ["elsewhere"], beat_key="open-tts")]), [])

    def test_the_reason_names_shared_entities_or_the_beat(self):
        subject = _record("subject", 3, 3, ["maker", "task"], beat_key="decision-models")
        subject["entities"] = {"maker": ("maker", "Perplexity"), "task": ("task", "typed decisions")}
        shares_both = _record("both", 3, 3, ["maker", "task"])
        shares_both["entities"] = dict(subject["entities"])
        beat_only = _record("beat", 3, 3, [], beat_key="decision-models")
        reasons = dict(self._nearby(subject, [subject, shares_both, beat_only]))
        self.assertEqual(reasons["both"], "Shares maker Perplexity and task typed decisions")
        self.assertEqual(reasons["beat"], "Same beat: Decision models")


@unittest.skipUnless(
    (Path(sys.executable).parent / "papyrus").exists() or shutil.which("papyrus"),
    "the papyrus command from papyrus-newsroom is not installed",
)
class UnderratedProjectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output_directory = _project(UNDERRATED_CONTENT_DIRECTORY, UNDERRATED_KNOWLEDGE_DIRECTORY)
        cls.plain_directory = _project(PLAIN_CONTENT_DIRECTORY, PLAIN_KNOWLEDGE_DIRECTORY)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.output_directory, ignore_errors=True)
        shutil.rmtree(cls.plain_directory, ignore_errors=True)

    def _page(self, relative_path, directory=None):
        return ((directory or self.output_directory) / relative_path / "index.html").read_text(encoding="utf-8")

    def test_an_underrated_signal_page_carries_the_mark_and_the_labelled_figures(self):
        page = self._page("decisions/quiet-pair-one")
        self.assertIn('class="signal-underrated"', page)
        self.assertIn("Works better than it’s talked about.", page)
        self.assertIn("Useful 4.0 · Ready 4.5 · 1 mention", page)
        self.assertIn("first pass", page)
        self.assertNotIn('class="signal-underrated is-placeholder"', page)

    def test_signals_that_fail_the_rule_show_no_mark_and_no_empty_placeholder(self):
        for slug in ("popular-strong", "low-ready", "busy-1", "voice-one"):
            section = "open-weights" if slug == "voice-one" else "decisions"
            page = self._page(f"{section}/{slug}")
            self.assertNotIn("signal-underrated", page, slug)
            self.assertNotIn("Works better than it", page, slug)

    def test_the_home_panel_lists_only_the_underrated_signals_with_figures(self):
        page = self._page(".")
        panel = page.split('class="front-underrated"')[1].split("</section>")[0]
        self.assertEqual(re.findall(r'<li><a href="([^"]*)">', panel), ["/decisions/quiet-strong/", "/decisions/quiet-pair-one/"])
        self.assertIn("Useful 4.5 · Ready 4.0 · 0 mentions", panel)
        self.assertIn("Useful 4.0 · Ready 4.5 · 1 mention<", panel)
        self.assertIn("first pass", panel)
        self.assertNotIn("is-placeholder", panel)
        self.assertNotIn("[n]", panel)

    def test_the_home_panel_is_hidden_when_no_signal_is_underrated(self):
        page = self._page(".", self.plain_directory)
        self.assertNotIn("front-underrated", page)
        self.assertNotIn("Works better than it", page)

    def test_nearby_lists_titles_linked_with_a_reason_and_leads_with_shared_entities(self):
        page = self._page("decisions/quiet-pair-one")
        rail = page.split('id="signal-nearby-h"')[1].split("</section>")[0]
        links = re.findall(r'<li><a href="([^"]*)">([^<]*)</a><span class="signal-nearby-why">([^<]*)</span>', rail)
        self.assertEqual(links[0], ("/decisions/quiet-pair-two/", "Fixture: the neighbour of the pair", "Shares maker Pairwise Fixture Lab and task fixture pairing"))
        self.assertTrue(all(why.startswith("Same beat: Decision models") for _href, _title, why in links[1:]))
        self.assertLessEqual(len(links), 5)
        self.assertNotIn("is-placeholder", page.split('id="signal-nearby-h"')[0].rsplit("<section", 1)[1])

    def test_nearby_is_hidden_when_nothing_is_near(self):
        page = self._page("open-weights/voice-one")
        self.assertNotIn("signal-nearby-h", page)
        self.assertNotIn("Nearby on the map", page)

    def test_a_signal_page_no_story_cites_has_no_placeholder_and_no_stories_block(self):
        page = self._page("decisions/quiet-pair-one")
        self.assertEqual(page.count('class="placeholder-tag"'), 0)
        self.assertNotIn("Appears in these stories", page)


if __name__ == "__main__":
    unittest.main()

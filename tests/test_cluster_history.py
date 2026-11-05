import importlib.util
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

HOOKS_PATH = Path(__file__).resolve().parent.parent / "web" / "hooks.py"


def _load_hooks():
    specification = importlib.util.spec_from_file_location("shipped_hooks_for_cluster_history", HOOKS_PATH)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class _Knowledge:
    def __init__(self, history):
        self._history = history
        self._source = SimpleNamespace(clusters=lambda: {"clusters": []}, index=lambda: {})

    def history(self):
        return self._history


def _page(history):
    return SimpleNamespace(site=SimpleNamespace(knowledge=_Knowledge(history)))


TWO_WEEK_HISTORY = {
    "schemaVersion": 1,
    "asOf": "2026-10-26",
    "weeks": [
        {
            "asOf": "2026-10-19", "runId": "run-a",
            "clusters": [
                {"uid": "tc-agents", "label": "Agents", "itemCount": 5},
                {"uid": "tc-code", "label": "Code models", "itemCount": 4},
                {"uid": "tc-voice", "label": "Voice", "itemCount": 6},
            ],
            "events": [{"event": "born", "uid": "tc-agents"}, {"event": "born", "uid": "tc-code"}, {"event": "born", "uid": "tc-voice"}],
        },
        {
            "asOf": "2026-10-26", "runId": "run-b",
            "clusters": [
                {"uid": "tc-cloning", "label": "Voice cloning", "itemCount": 3},
                {"uid": "tc-evals", "label": None, "itemCount": 2},
                {"uid": "tc-synthesis", "label": "Speech synthesis", "itemCount": 4},
                {"uid": "tc-tooling", "label": "Agent tooling", "itemCount": 11},
            ],
            "events": [
                {"event": "born", "uid": "tc-evals"},
                {"event": "merged_from", "uid": "tc-tooling", "sources": ["tc-agents", "tc-code"]},
                {"event": "split_into", "uid": "tc-voice", "into": ["tc-cloning", "tc-synthesis"]},
            ],
        },
    ],
}


class KnowledgeHistoryAccessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hooks = _load_hooks()

    def test_a_site_without_history_or_with_an_unknown_schema_has_none(self):
        self.assertIsNone(self.hooks._knowledge_history(_page(None)))
        self.assertIsNone(self.hooks._knowledge_history(_page({"schemaVersion": 2, "weeks": TWO_WEEK_HISTORY["weeks"]})))
        self.assertIsNone(self.hooks._knowledge_history(_page({"schemaVersion": 1, "weeks": []})))
        self.assertIsNone(self.hooks._knowledge_history(SimpleNamespace(site=SimpleNamespace(knowledge=SimpleNamespace()))))

    def test_a_site_with_history_returns_its_weeks_oldest_first(self):
        history = self.hooks._knowledge_history(_page(TWO_WEEK_HISTORY))
        self.assertEqual([week["asOf"] for week in history["weeks"]], ["2026-10-19", "2026-10-26"])


class ClusterRiverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hooks = _load_hooks()
        cls.river = cls.hooks._map_river(_page(TWO_WEEK_HISTORY), {})
        cls.placeholder = cls.hooks._map_river(_page(None), {})

    def test_without_history_the_river_stays_the_dimmed_sample_with_one_placeholder_tag(self):
        self.assertIn('class="map-river-sample is-placeholder"', self.placeholder)
        self.assertEqual(self.placeholder.count('class="placeholder-tag"'), 1)
        self.assertIn("not real data", self.placeholder)

    def test_with_history_the_river_is_real_and_carries_no_placeholder_or_sample_copy(self):
        self.assertIn('<section class="map-river" aria-labelledby="map-river-h">', self.river)
        self.assertNotIn("is-placeholder", self.river.split("map-river-h")[1])
        self.assertNotIn("Sample", self.river.split("map-river-h")[1])
        self.assertIn("2 weeks of history", self.river)
        self.assertIn("from the week of 19 Oct. The river fills in as each weekly run adds a week.", self.river)

    def test_the_five_largest_named_clusters_are_streams_and_the_rest_fall_into_other(self):
        labels = re.findall(r'<ul class="map-river-labels">(.*?)</ul>', self.river)[0]
        names = re.findall(r"</svg>([^<]+)</li>", labels)
        self.assertEqual(names, ["Other clusters", "Speech synthesis", "Code models", "Agents", "Voice", "Agent tooling"])

    def test_every_stream_has_a_pattern_and_a_label_never_colour_alone(self):
        self.assertIn('fill="url(#map-pattern-0)"', self.river)
        self.assertIn("Each stream is named in the key and filled with its own pattern.", self.river)

    def test_the_weeks_sit_at_the_right_of_the_twenty_six_week_frame(self):
        xs = sorted({int(x) for x in re.findall(r'<rect x="(\d+)" y="\d+" width="38"', self.river)})
        self.assertEqual(xs, [24 * 40 + 1, 25 * 40 + 1])
        self.assertIn("<span>Week of 4 May</span><span>Week of 26 Oct</span>", self.river)

    def test_lineage_events_are_marked_with_shapes_and_words_but_the_first_week_is_not(self):
        self.assertIn('aria-label="Cluster born: 1 in the week of 26 Oct"', self.river)
        self.assertIn('aria-label="Cluster split: 1 in the week of 26 Oct"', self.river)
        self.assertIn('aria-label="Clusters merged: 1 in the week of 26 Oct"', self.river)
        self.assertNotIn("in the week of 19 Oct", self.river)

    def test_the_numbers_are_available_as_a_table(self):
        numbers = self.river.split('class="map-river-numbers"')[1]
        self.assertIn('<th scope="col">19 Oct</th><th scope="col">26 Oct</th>', numbers)
        self.assertIn('<tr><th scope="row">Agent tooling</th><td>0</td><td>11</td></tr>', numbers)
        self.assertIn('<tr><th scope="row">Other clusters</th><td>0</td><td>5</td></tr>', numbers)

    def test_only_the_last_twenty_six_weeks_are_drawn(self):
        weeks = [
            {"asOf": f"2026-{1 + index // 4:02d}-{1 + (index % 4) * 7:02d}", "clusters": [{"uid": "tc-a", "label": "A", "itemCount": 1 + index}], "events": []}
            for index in range(30)
        ]
        river = self.hooks._map_river(_page({"schemaVersion": 1, "weeks": weeks}), {})
        self.assertIn("over the last 26 weeks", river)
        self.assertEqual(river.split('class="map-river-numbers"')[1].count("<td>"), 26)


class FrontChangesPanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hooks = _load_hooks()
        cls.panel = cls.hooks.block("map-changes", {}, _page(TWO_WEEK_HISTORY))

    def test_the_panel_names_the_week_it_compares_with(self):
        self.assertIn('<h3 id="front-changes-h" class="kicker">Since the week of 19 Oct</h3>', self.panel)

    def test_born_merged_and_split_name_the_clusters_with_a_mark_and_a_word(self):
        rows = re.findall(r"<li><svg[^>]*aria-hidden=\"true\">.*?</svg><b>(\w+)</b> <span>(.*?)</span></li>", self.panel)
        self.assertEqual(rows, [
            ("Born", "1 unnamed"),
            ("Merged", "Agent tooling from Agents and Code models"),
            ("Split", "Voice into Voice cloning and Speech synthesis"),
        ])

    def test_continued_clusters_are_counted(self):
        week = {"asOf": "2026-11-02", "clusters": [], "events": [{"event": "continued", "uid": "a", "from": "a"}, {"event": "continued", "uid": "b", "from": "b"}]}
        history = {**TWO_WEEK_HISTORY, "weeks": TWO_WEEK_HISTORY["weeks"] + [week]}
        panel = self.hooks.block("map-changes", {}, _page(history))
        self.assertIn("<b>Continued</b> <span>2 clusters</span>", panel)
        self.assertIn("Since the week of 26 Oct", panel)

    def test_without_history_or_with_a_single_week_the_panel_is_left_out(self):
        self.assertEqual(self.hooks.block("map-changes", {}, _page(None)), "")
        single = {**TWO_WEEK_HISTORY, "weeks": TWO_WEEK_HISTORY["weeks"][:1]}
        self.assertEqual(self.hooks.block("map-changes", {}, _page(single)), "")


if __name__ == "__main__":
    unittest.main()

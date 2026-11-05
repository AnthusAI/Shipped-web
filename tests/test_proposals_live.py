import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIRECTORY = REPOSITORY_ROOT / "web"
FIXTURE_INDEX = REPOSITORY_ROOT / "tests" / "fixtures" / "proposals" / "_data" / "proposals" / "index.json"
VALID_STATES = {"draft", "in_steering", "editor_review", "approved", "declined", "overridden_by_editor"}


class ProposalsLiveTest(unittest.TestCase):
    def test_fixture_covers_every_state_group_and_an_override(self):
        entries = json.loads(FIXTURE_INDEX.read_text(encoding="utf-8"))
        self.assertEqual({entry["state"] for entry in entries}, VALID_STATES)
        self.assertEqual({entry["group"] for entry in entries}, {"stories", "concepts", "map_changes"})
        overridden = [entry for entry in entries if entry["state"] == "overridden_by_editor"][0]
        self.assertTrue(overridden["decision"]["reason"])
        self.assertTrue(overridden["communityResult"])

    def test_mounts_keep_the_placeholder_as_the_no_script_fallback(self):
        expectations = {
            "proposals.md": ('class="proposals-queue is-placeholder"', 'data-proposals-live="queue"'),
            "home.md": ('class="front-proposals is-placeholder"', 'data-proposals-live="home"'),
            "topic-open-tts.md": ('class="concept-proposals is-placeholder"', 'data-proposals-live="concept"'),
            "topic-decision-models.md": ('class="concept-proposals is-placeholder"', 'data-proposals-live="concept"'),
        }
        for name, needles in expectations.items():
            text = (STATIC_DIRECTORY / "pages" / name).read_text(encoding="utf-8")
            for needle in needles:
                self.assertIn(needle, text, name)
            self.assertIn("placeholder-tag", text, name)

    def test_script_is_loaded_by_head_extra_and_posts_the_documented_vote_body(self):
        hooks = (STATIC_DIRECTORY / "hooks.py").read_text(encoding="utf-8")
        self.assertIn("/assets/shipped-proposals.js", hooks)
        script = (STATIC_DIRECTORY / "assets" / "shipped-proposals.js").read_text(encoding="utf-8")
        self.assertIn('type: "proposal"', script)
        self.assertIn("/vote", script)
        self.assertIn("Proposal voting opens soon", script)
        self.assertIsNone(re.search(r"^\s*//", script, re.MULTILINE))

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_script_behaviour_checks_pass_under_node(self):
        result = subprocess.run(["node", str(REPOSITORY_ROOT / "tests" / "proposals_script_check.cjs")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

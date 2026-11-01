import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIRECTORY = REPOSITORY_ROOT / "web"
SCRIPT_PATH = STATIC_DIRECTORY / "assets" / "shipped-extraction.js"


def _papyrus_executable():
    beside_interpreter = Path(sys.executable).parent / "papyrus"
    return str(beside_interpreter) if beside_interpreter.exists() else (shutil.which("papyrus") or "papyrus")


class SubmitExtractionScriptTest(unittest.TestCase):
    def test_the_script_reads_and_confirms_through_the_documented_reader_routes(self):
        script = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn('"/extraction?subject="', script)
        self.assertIn('"/extraction/confirm"', script)
        self.assertIn('decision: "confirm"', script)
        self.assertIn('decision: "correct"', script)
        self.assertIn('"content-type": "application/json"', script)
        self.assertIn('cache: "no-store"', script)

    def test_the_script_stores_only_submission_ids_and_titles_in_this_browser(self):
        script = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("subject: submission.subject, title: String(submission.title", script)
        for word in ("readerId", "handle", "siteSubject", "localStorage.setItem(STORAGE_KEY, JSON.stringify(entries)"):
            self.assertNotIn(word, script)

    def test_the_script_has_no_line_comments(self):
        self.assertIsNone(re.search(r"^\s*//", SCRIPT_PATH.read_text(encoding="utf-8"), re.MULTILINE))

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_script_behaviour_checks_pass_under_node(self):
        result = subprocess.run(["node", str(REPOSITORY_ROOT / "tests" / "extraction_script_check.cjs")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(
    (Path(sys.executable).parent / "papyrus").exists() or shutil.which("papyrus"),
    "the papyrus command from papyrus-newsroom is not installed",
)
class SubmitExtractionPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output_directory = Path(tempfile.mkdtemp(prefix="shipped-submit-"))
        result = subprocess.run(
            [
                _papyrus_executable(), "ops", "content", "project", "--all",
                "--from-dir", str(REPOSITORY_ROOT / "tests" / "fixtures" / "content"),
                "--static-dir", str(STATIC_DIRECTORY),
                "--knowledge-dir", str(REPOSITORY_ROOT / "tests" / "fixtures" / "knowledge"),
                "--out", str(cls.output_directory),
            ],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise AssertionError(result.stdout + result.stderr)
        cls.submit = (cls.output_directory / "submit" / "index.html").read_text(encoding="utf-8")
        cls.home = (cls.output_directory / "index.html").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.output_directory, ignore_errors=True)

    def test_the_section_stays_a_placeholder_with_one_tag_until_a_submission_exists(self):
        section = self.submit.split('<section class="on-the-map is-placeholder"')[1].split("</section>")[0]
        self.assertIn("data-extraction-live", section)
        self.assertEqual(section.count('class="placeholder-tag"'), 1)
        self.assertEqual(section.count("data-extraction-sample"), 2)
        self.assertIn('<div class="extraction-records" data-extraction-records></div>', section)

    def test_only_the_submit_page_loads_the_script(self):
        self.assertIn('<script src="/assets/shipped-extraction.js" defer></script>', self.submit)
        self.assertNotIn("shipped-extraction.js", self.home)


if __name__ == "__main__":
    unittest.main()

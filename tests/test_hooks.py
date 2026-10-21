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
        self.assertIn("hype-gap", page)

    def test_home_page_has_two_desk_board_rows(self):
        page = self._page(".")
        self.assertIn("From the desk", page)
        self.assertEqual(len(re.findall(r'<li class="board-row">', page.split('class="board desk-board"')[1].split("</ol>")[0])), 2)
        self.assertIn("Ratings open with reader sign-in", page)

    def test_new_page_has_desk_board_and_sample_board_stays_marked(self):
        page = self._page("new")
        self.assertIn("From the desk", page)
        self.assertIn("sample-mark", page)

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

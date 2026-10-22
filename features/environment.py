import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "content"
STATIC_DIRECTORY = REPOSITORY_ROOT / "web"
KNOWLEDGE_DIRECTORY = REPOSITORY_ROOT / "tests" / "fixtures" / "knowledge"


def _papyrus_executable():
    beside_interpreter = Path(sys.executable).parent / "papyrus"
    return str(beside_interpreter) if beside_interpreter.exists() else (shutil.which("papyrus") or "papyrus")


def before_all(context):
    context.output_directory = Path(tempfile.mkdtemp(prefix="shipped-features-"))
    result = subprocess.run(
        [
            _papyrus_executable(), "ops", "content", "project", "--all",
            "--from-dir", str(FIXTURE_DIRECTORY),
            "--static-dir", str(STATIC_DIRECTORY),
            "--knowledge-dir", str(KNOWLEDGE_DIRECTORY),
            "--out", str(context.output_directory),
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    context.static_directory = STATIC_DIRECTORY
    context.projection_settings = json.loads((STATIC_DIRECTORY / "projection.json").read_text(encoding="utf-8"))
    context.scoring = json.loads((STATIC_DIRECTORY / "scoring.json").read_text(encoding="utf-8"))


def after_all(context):
    shutil.rmtree(context.output_directory, ignore_errors=True)

import re
from pathlib import Path

from behave import given, then, when


def _page_text(context, path):
    relative = path.strip("/")
    target = context.output_directory / relative / "index.html" if relative else context.output_directory / "index.html"
    assert target.exists(), f"{path} was not projected"
    return target.read_text(encoding="utf-8")


@given("the Shipped site is built from the fixture content")
def step_site_built(context):
    assert (context.output_directory / "index.html").exists()


@when('I open the page "{path}"')
def step_open_page(context, path):
    context.current_path = path
    context.current_page = _page_text(context, path)


@then('the page "{path}" does not exist')
def step_page_absent(context, path):
    relative = path.strip("/")
    assert not (context.output_directory / relative / "index.html").exists(), f"{path} should not be projected"


@then('the page contains "{text}"')
def step_page_contains(context, text):
    assert text in context.current_page, f"{context.current_path} does not contain {text!r}"


@then('the page does not contain "{text}"')
def step_page_lacks(context, text):
    assert text.lower() not in context.current_page.lower(), f"{context.current_path} contains {text!r}"


@then('no projected page contains "{text}"')
def step_no_page_contains(context, text):
    needle = text.lower()
    offenders = [
        path.relative_to(context.output_directory).as_posix()
        for path in context.output_directory.rglob("*")
        if path.is_file() and path.suffix in {".html", ".md", ".xml", ".txt", ".json"} and needle in path.read_text(encoding="utf-8").lower()
    ]
    assert not offenders, f"{text!r} found in {offenders}"


@then('the projection settings redirect "{source}" to "{target}"')
def step_redirect(context, source, target):
    assert context.projection_settings["redirects"]["exact"].get(source) == target


@then('the navigation does not link to "{href}"')
def step_nav_lacks(context, href):
    assert href not in [link["href"] for link in context.projection_settings["nav"]["links"]]


STATUS_MARK_SHAPES = {
    "Available": 'M2.5 2.5h11v11h-11z',
    "Verified": 'circle cx="8" cy="8" r="5.8"',
    "Announced": 'circle cx="8" cy="8" r="1.6"',
}


def _stamp_for(page, word):
    match = re.search(
        rf'<span class="status-stamp status-stamp-{word.lower()}[^"]*">(<svg.*?</svg>)<span class="status-stamp-label">{word}</span></span>',
        page,
        re.S,
    )
    assert match, f"no {word} stamp with a mark on the page"
    return match.group(1)


@then('the page shows the status "{word}" as a mark with its word')
def step_status_mark(context, word):
    mark = _stamp_for(context.current_page, word)
    assert STATUS_MARK_SHAPES[word] in mark, f"the {word} mark does not use its own shape"


@then("the three status marks use three different shapes")
def step_marks_differ(context):
    shapes = {re.sub(r"\s+", "", _stamp_for(context.current_page, word)) for word in STATUS_MARK_SHAPES}
    assert len(shapes) == 3


@then("the rail key lists Available, Verified and Announced in that order")
def step_rail_key(context):
    key = context.current_page.split('class="rail-key"')[1].split("</dl>")[0]
    assert re.findall(r'status-stamp-label">(\w+)<', key) == ["Available", "Verified", "Announced"]


@then("the scoring data names the verdicts {verdicts}")
def step_scoring_verdicts(context, verdicts):
    wanted = [word.strip().strip('"') for word in verdicts.split(",")]
    assert context.scoring["verdicts"] == wanted, context.scoring["verdicts"]


@then('no page uses "{word}" as a status')
def step_no_status_word(context, word):
    needle = f'status-stamp-label">{word}<'
    offenders = [
        path.relative_to(context.output_directory).as_posix()
        for path in context.output_directory.rglob("*.html")
        if needle in path.read_text(encoding="utf-8") or f"status-stamp-{word.lower()}" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"{word!r} is still a status on {offenders}"

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

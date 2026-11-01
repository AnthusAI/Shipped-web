import importlib.util
import json
from types import SimpleNamespace

from behave import given, then, when


def _hooks(context):
    specification = importlib.util.spec_from_file_location("shipped_hooks_for_cluster_history_features", context.static_directory / "hooks.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _page_with_history(history):
    knowledge = SimpleNamespace(history=lambda: history, _source=SimpleNamespace(clusters=lambda: {"clusters": []}, index=lambda: {}))
    return SimpleNamespace(site=SimpleNamespace(knowledge=knowledge))


@given('the cluster history "{name}"')
def step_cluster_history(context, name):
    fixture = context.static_directory.parent / "tests" / "fixtures" / "cluster-history" / f"{name}.json"
    context.cluster_history_page = _page_with_history(json.loads(fixture.read_text(encoding="utf-8")))


@when("the Map river is rendered")
def step_render_river(context):
    context.rendering = _hooks(context).block("map-river", {}, context.cluster_history_page)


@when("the Front changes panel is rendered")
def step_render_changes(context):
    context.rendering = _hooks(context).block("map-changes", {}, context.cluster_history_page)


@then('the rendering contains "{text}"')
def step_rendering_contains(context, text):
    assert text in context.rendering, text


@then('the rendering does not contain "{text}"')
def step_rendering_lacks(context, text):
    assert text not in context.rendering, text

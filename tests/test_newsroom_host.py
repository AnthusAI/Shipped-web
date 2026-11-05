import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
EDGE_TEMPLATE = REPOSITORY_ROOT / "infra" / "edge" / "shipped.yaml"
NEWSROOM_HOST = "newsroom.shipped.anth.us"


def newsroom_redirect_function_code():
    template = EDGE_TEMPLATE.read_text()
    resource = template.split("  NewsroomRedirectFunction:\n", 1)[1].split("\n  NotFoundPageRole:\n", 1)[0]
    code = resource.split("FunctionCode: !Sub |\n", 1)[1]
    lines = [line[8:] if line.startswith("        ") else line for line in code.splitlines()]
    return "\n".join(lines).replace("${NewsroomHost}", NEWSROOM_HOST)


def redirect_for(uri, querystring):
    script = newsroom_redirect_function_code() + "\nprocess.stdout.write(JSON.stringify(handler(" + json.dumps(
        {"request": {"uri": uri, "querystring": querystring}}
    ) + ")));"
    completed = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    return json.loads(completed.stdout)


@unittest.skipUnless(shutil.which("node"), "node is needed to run the CloudFront function")
class NewsroomRedirectFunction(unittest.TestCase):
    def test_the_bare_newsroom_path_goes_to_the_root_of_the_newsroom_host(self):
        response = redirect_for("/newsroom", {})
        self.assertEqual(response["statusCode"], 301)
        self.assertEqual(response["headers"]["location"]["value"], "https://newsroom.shipped.anth.us/")

    def test_a_deep_link_keeps_its_path_and_query_string(self):
        response = redirect_for(
            "/newsroom/articles/abc",
            {"code": {"value": "x1"}, "state": {"value": "y2"}},
        )
        self.assertEqual(response["headers"]["location"]["value"], "https://newsroom.shipped.anth.us/articles/abc?code=x1&state=y2")

    def test_repeated_query_values_are_all_kept(self):
        response = redirect_for(
            "/newsroom/",
            {"tag": {"value": "a", "multiValue": [{"value": "a"}, {"value": "b"}]}},
        )
        self.assertEqual(response["headers"]["location"]["value"], "https://newsroom.shipped.anth.us/?tag=a&tag=b")

    def test_a_path_that_only_starts_with_the_word_keeps_its_whole_path(self):
        response = redirect_for("/newsroomish", {})
        self.assertEqual(response["headers"]["location"]["value"], "https://newsroom.shipped.anth.us/newsroomish")


class NewsroomOnItsOwnHost(unittest.TestCase):
    def test_the_edge_sends_newsroom_paths_to_the_redirect_function(self):
        template = EDGE_TEMPLATE.read_text()
        behaviour = template.split("- PathPattern: '/newsroom*'", 1)[1].split("- PathPattern:", 1)[0]
        self.assertIn("NewsroomRedirectFunction.FunctionARN", behaviour)
        self.assertIn("Default: " + NEWSROOM_HOST, template)

    def test_the_brand_serves_the_newsroom_at_the_root(self):
        brand = (REPOSITORY_ROOT / "publication" / "brand.ts").read_text()
        self.assertIn('rootRoute: { kind: "newsroom" }', brand)
        self.assertRegex(brand, r'newsroomBasePath: ""')

    def test_sign_in_returns_to_the_newsroom_host_and_still_to_the_apex(self):
        site = json.loads((REPOSITORY_ROOT / "infra" / "site.json").read_text())
        origins = site["cms"]["environment"]["PAPYRUS_OAUTH_REDIRECT_URLS"].split(",")
        self.assertIn("https://" + NEWSROOM_HOST + "/", origins)
        self.assertIn("https://shipped.anth.us/", origins)
        configuration = (REPOSITORY_ROOT / "papyrus.config.ts").read_text()
        default_list = re.search(r"const defaultRedirectUrls = \[(.*?)\];", configuration).group(1)
        self.assertIn('"https://' + NEWSROOM_HOST + '/"', default_list)


if __name__ == "__main__":
    unittest.main()

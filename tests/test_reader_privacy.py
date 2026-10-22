import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "tests"))

import reader_privacy  # noqa: E402
from test_map import PLAIN_CONTENT_DIRECTORY, PLAIN_KNOWLEDGE_DIRECTORY, _project  # noqa: E402

MEASUREMENT_ID = "G-31SC26SDGX"
PAPYRUS_AVAILABLE = (Path(sys.executable).parent / "papyrus").exists() or shutil.which("papyrus")


class AnalyticsLeakScanTest(unittest.TestCase):
    def test_a_clean_configuration_and_event_have_no_leaks(self):
        page = (
            "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}"
            "gtag('config', \"G-31SC26SDGX\");"
            "gtag('event','sign_up',{method:'newsletter'});"
            "gtag('event','cta_click',{cta_text:'Subscribe',cta_location:'hero',link_url:'shipped.anth.us/subscribe/'});</script>"
        )
        self.assertEqual(reader_privacy.analytics_leaks(page), [])

    def test_a_user_id_a_subject_an_email_and_an_identity_query_are_leaks(self):
        for call in (
            "gtag('config','G-1',{user_id:'abc'})",
            "gtag('set','user_properties',{a:1})",
            "gtag('event','sign_up',{method:'ss1_abcdefgh12'})",
            "gtag('event','sign_up',{method:'reader@example.org'})",
            "gtag('event','cta_click',{link_url:'shipped.anth.us/x?token=1'})",
            f"papyrusAnalytics.track('sign_up',{{method:'{'-'.join(['a' * 8, 'b' * 4, 'c' * 4, 'd' * 4, 'e' * 12])}'}})",
        ):
            with self.subTest(call=call):
                self.assertTrue(reader_privacy.analytics_leaks(f"<script>{call}</script>"), call)

    def test_scan_files_reports_analytics_leaks_per_page(self):
        found = reader_privacy.scan_files({"/": "<script>gtag('set','user_id','x')</script>", "/data.json": "{}"})
        self.assertEqual(list(found), ["/"])


@unittest.skipUnless(PAPYRUS_AVAILABLE, "the papyrus command from papyrus-newsroom is not installed")
class BuiltPagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output_directory = _project(PLAIN_CONTENT_DIRECTORY, PLAIN_KNOWLEDGE_DIRECTORY)
        cls.pages = {str(path.relative_to(cls.output_directory)): path.read_text(encoding="utf-8") for path in cls.output_directory.rglob("*.html")}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.output_directory, ignore_errors=True)

    def test_every_built_page_has_the_gtag_config_after_consent_defaults_and_no_identity(self):
        self.assertTrue(self.pages)
        for name, page in self.pages.items():
            if name == "404.html" or name.startswith("assets/"):
                continue
            with self.subTest(page=name):
                self.assertIn(f'gtag(\'config\', "{MEASUREMENT_ID}")', page)
                self.assertLess(page.index("consent','default'"), page.index("googletagmanager.com/gtag/js"))
                self.assertLess(page.index("page_location"), page.index("googletagmanager.com/gtag/js"))
                self.assertEqual(reader_privacy.analytics_leaks(page), [])

    def test_the_banner_links_to_the_policies_page_and_the_footer_offers_cookie_settings(self):
        page = self.pages["index.html"]
        self.assertIn('href="/policies/#privacy"', page)
        self.assertIn('href="#cookie-settings"', page)

    def test_the_whole_built_site_passes_the_reader_privacy_scan(self):
        self.assertEqual(reader_privacy.scan_files(self.pages), {})


class EngineScriptTest(unittest.TestCase):
    def test_the_engine_scripts_do_not_count_as_identity_but_a_site_user_id_still_does(self):
        engine = "<script>(function(){var IDENTITY_NAME=/^(personid|person_id|user_id)$/i;})();</script>"
        self.assertEqual(reader_privacy.scan_files({"/": engine}), {})
        found = reader_privacy.scan_files({"/": engine + "<script>gtag('set','user_id','x')</script>"})
        self.assertIn("/", found)

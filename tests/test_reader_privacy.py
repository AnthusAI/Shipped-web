import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "tests"))

import reader_privacy  # noqa: E402
from test_map import PLAIN_CONTENT_DIRECTORY, PLAIN_KNOWLEDGE_DIRECTORY, _project  # noqa: E402
from test_sponsorship import _project as _project_with_static, _read_pages, _static_directory_with_sponsorship  # noqa: E402
from sponsorship_content import write_extended_content  # noqa: E402

MEASUREMENT_ID = "G-31SC26SDGX"
SPONSORSHIP_SCRIPT = Path(__file__).resolve().parent.parent / "web" / "assets" / "shipped-sponsorship.js"
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

    def test_consent_follows_the_anthus_standard_with_advertising_only_after_accept(self):
        page = self.pages["index.html"]
        self.assertIn("ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied',analytics_storage:'denied',wait_for_update:500,region:[", page)
        self.assertIn("ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied',analytics_storage:'granted'", page)
        self.assertIn("ad_storage:v,ad_user_data:v,ad_personalization:v,analytics_storage:v", page)
        self.assertIn("if you agree, for advertising", page)
        self.assertNotIn("We do not use them for advertising.", page)

    def test_the_whole_built_site_passes_the_reader_privacy_scan(self):
        self.assertEqual(reader_privacy.scan_files(self.pages), {})


class SponsorshipScanTest(unittest.TestCase):
    def test_the_shipped_sponsorship_script_sends_only_the_allowed_fields_and_reads_no_reader_state(self):
        script = SPONSORSHIP_SCRIPT.read_text(encoding="utf-8")
        self.assertEqual(reader_privacy.sponsorship_script_leaks(script), [])
        for field in reader_privacy.SPONSORSHIP_EVENT_FIELDS | reader_privacy.SPONSORSHIP_EVENT_NAMES:
            self.assertIn(field, script)

    def test_a_script_with_an_identity_field_an_extra_field_or_reader_state_is_a_leak(self):
        for fragment in (
            "gtag('event','view_promotion',{user_id:'abc'})",
            "fields.reader_id = 'abc';",
            "fields.client_id = 'abc';",
            "fields.email_address = 'abc';",
            "var stored = document.cookie;",
            "var stored = window.localStorage.getItem('x');",
            "var reader = window.papyrusReader.readerId;",
            "window.gtag('event','select_promotion',{method:'ss1_abcdefgh12'});",
        ):
            with self.subTest(fragment=fragment):
                self.assertTrue(reader_privacy.sponsorship_script_leaks(fragment), fragment)

    def test_unit_attributes_with_an_unknown_name_or_an_identity_value_are_leaks(self):
        clean = '<aside data-sponsor-unit="card" data-sponsor-id="cyclotron" data-sponsor-page-type="signal" data-sponsor-topic="decision-models"></aside>'
        self.assertEqual(reader_privacy.sponsorship_attribute_leaks(clean), [])
        self.assertTrue(reader_privacy.sponsorship_attribute_leaks('<aside data-sponsor-reader="abc"></aside>'))
        self.assertTrue(reader_privacy.sponsorship_attribute_leaks('<aside data-sponsor-topic="reader@example.org"></aside>'))
        self.assertTrue(reader_privacy.sponsorship_attribute_leaks('<aside data-sponsor-slot="ss1_abcdefgh12"></aside>'))
        self.assertTrue(reader_privacy.sponsorship_attribute_leaks(f"<aside data-sponsor-name=\"{'-'.join(['a' * 8, 'b' * 4, 'c' * 4, 'd' * 4, 'e' * 12])}\"></aside>"))

    def test_scan_files_scans_pages_for_unit_attributes_and_the_script_by_its_path(self):
        found = reader_privacy.scan_files({"/": '<aside data-sponsor-user="abc"></aside>', "assets/shipped-sponsorship.js": "fields.user_id = 1;"})
        self.assertEqual(sorted(found), ["/", "assets/shipped-sponsorship.js"])
        self.assertEqual(reader_privacy.scan_files({"assets/shipped-sponsorship.js": SPONSORSHIP_SCRIPT.read_text(encoding="utf-8")}), {})


@unittest.skipUnless(PAPYRUS_AVAILABLE, "the papyrus command from papyrus-newsroom is not installed")
class SponsorshipBuiltPagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.static_directory = _static_directory_with_sponsorship(True)
        cls.content_directory = write_extended_content(Path(tempfile.mkdtemp(prefix="shipped-privacy-content-")) / "content")
        cls.output_directory = _project_with_static(cls.content_directory, cls.static_directory)
        cls.files = _read_pages(cls.output_directory)
        cls.files["assets/shipped-sponsorship.js"] = SPONSORSHIP_SCRIPT.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        for directory in (cls.output_directory, cls.static_directory.parent, cls.content_directory.parent):
            shutil.rmtree(directory, ignore_errors=True)

    def test_every_page_with_sponsorship_units_and_the_script_pass_the_reader_privacy_scan(self):
        self.assertTrue(any('data-sponsor-unit="card"' in page for page in self.files.values()))
        self.assertEqual(reader_privacy.scan_files(self.files), {})

    def test_no_unit_attribute_or_sponsored_link_carries_a_reader_id_handle_email_sub_or_user_id(self):
        for name, page in self.files.items():
            if not name.endswith("/"):
                continue
            for unit in re.findall(r"<aside[^>]*data-sponsor-unit[^>]*>", page):
                with self.subTest(page=name):
                    self.assertNotRegex(unit, r"(?i)reader|handle|email|\bsub\b|user[_-]?id|person")
            for href in re.findall(r'href="(https://[^"]*utm_source=shipped[^"]*)"', page):
                with self.subTest(page=name, href=href):
                    self.assertEqual(reader_privacy.identity_leaks(href), [])
                    self.assertNotRegex(href, r"(?i)[?&](reader|handle|email|sub|user_id|user|person)[^=&]*=")


class EngineScriptTest(unittest.TestCase):
    def test_the_engine_scripts_do_not_count_as_identity_but_a_site_user_id_still_does(self):
        engine = "<script>(function(){var IDENTITY_NAME=/^(personid|person_id|user_id)$/i;})();</script>"
        self.assertEqual(reader_privacy.scan_files({"/": engine}), {})
        found = reader_privacy.scan_files({"/": engine + "<script>gtag('set','user_id','x')</script>"})
        self.assertIn("/", found)

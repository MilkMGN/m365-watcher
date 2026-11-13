import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from unittest.mock import patch

import watcher


class FormatDescriptionTests(unittest.TestCase):
    def test_formats_html_as_readable_text(self):
        description = (
            "<div>User impact: Users cannot sign in.</div>"
            "<div>More info:<br/>- First service<br/>- Second service</div>"
        )
        self.assertEqual(
            watcher.format_description(description),
            "User impact: Users cannot sign in.\nMore info:\n- First service\n- Second service",
        )

    def test_decodes_html_entities(self):
        self.assertEqual(watcher.format_description("Service&nbsp;is&nbsp;restored"), "Service is restored")


class FeedParsingTests(unittest.TestCase):
    def test_fetch_incidents_parses_rss_fields(self):
        feed = b"""<rss version="2.0"><channel><item>
            <guid>incident-1</guid>
            <title>Example incident</title>
            <link>https://status.cloud.microsoft/</link>
            <pubDate>Tue, 16 Dec 2026 10:00:00 Z</pubDate>
            <status>ServiceDegradation</status>
            <description>&lt;div&gt;Users are affected.&lt;/div&gt;</description>
        </item></channel></rss>"""

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self):
                return feed

        with patch.object(watcher.urllib.request, "urlopen", return_value=Response()):
            incidents = watcher.fetch_incidents()

        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0].key, "incident-1")
        self.assertEqual(incidents[0].status, "ServiceDegradation")
        self.assertEqual(incidents[0].description, "Users are affected.")


class PollTests(unittest.TestCase):
    def test_prints_only_new_or_changed_incidents(self):
        initial = watcher.Incident("one", "Incident", "date", "Active", "link", "Initial")
        updated = initial._replace(description="Updated")
        with patch.object(watcher, "fetch_incidents", side_effect=[[initial], [updated]]):
            with patch("builtins.print") as print_mock:
                state = watcher.poll(None)
                watcher.poll(state)

        outputs = [call.args[0] for call in print_mock.call_args_list if call.args]
        self.assertEqual(sum(output.startswith("\nIncident") for output in outputs), 2)
        self.assertTrue(any("Updated" in output for output in outputs))

    def test_prints_current_utc_time_at_bottom(self):
        fixed_time = datetime(2026, 11, 13, 1, 6, 17, tzinfo=timezone.utc)
        with patch.object(watcher, "fetch_incidents", return_value=[]):
            with patch.object(watcher, "datetime") as datetime_mock:
                datetime_mock.now.return_value = fixed_time
                with patch("builtins.print") as print_mock:
                    watcher.poll(None)

        outputs = [call.args[0] for call in print_mock.call_args_list if call.args]
        self.assertEqual(outputs[-1], "\nCurrent time (UTC): 2026-11-13 01:06:17")
        datetime_mock.now.assert_called_once_with(timezone.utc)


if __name__ == "__main__":
    unittest.main()

import mimetypes

from django.test import SimpleTestCase


class StaticFileMimeTypeTests(SimpleTestCase):
    def test_javascript_files_use_module_compatible_mime_type(self):
        content_type, _ = mimetypes.guess_type("app.js")

        self.assertEqual(content_type, "application/javascript")

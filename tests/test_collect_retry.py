"""Regression checks for transient Crossref HTTP responses."""
import io
import pathlib
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import collect


class CrossrefRetryTests(unittest.TestCase):
    def test_transient_404_retries_then_succeeds(self):
        error = HTTPError("https://api.crossref.org/works", 404, "Not Found", {}, None)
        response = io.BytesIO(b'{"message":{"items":[]}}')
        with patch.object(collect.urllib.request, "urlopen", side_effect=[error, response]) as request, patch.object(collect.time, "sleep"):
            self.assertEqual(collect.get("https://api.crossref.org/works"), {"items": []})
            self.assertEqual(request.call_count, 2)

    def test_persistent_404_is_not_silently_accepted(self):
        error = HTTPError("https://api.crossref.org/works", 404, "Not Found", {}, None)
        with patch.object(collect.urllib.request, "urlopen", side_effect=[error] * 4) as request, patch.object(collect.time, "sleep"):
            with self.assertRaises(HTTPError):
                collect.get("https://api.crossref.org/works")
            self.assertEqual(request.call_count, 4)


if __name__ == "__main__":
    unittest.main()

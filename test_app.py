import unittest

from app import app, analyze_error


class AnalyzerTests(unittest.TestCase):
    def test_python_name_error_extracts_name(self):
        result = analyze_error("NameError: name 'total' is not defined", "Python")
        self.assertEqual(result["category"], "NameError")
        self.assertIn("total", result["title"])

    def test_javascript_undefined_property_is_explained(self):
        result = analyze_error(
            "TypeError: Cannot read properties of undefined (reading 'id')",
            "JavaScript",
        )
        self.assertEqual(result["category"], "TypeError")
        self.assertIn("id", result["title"])

    def test_unknown_error_returns_general_guidance(self):
        result = analyze_error("Build stopped near line 8", "Rust")
        self.assertEqual(result["confidence"], "General guidance")

    def test_python_index_error_returns_specific_fix(self):
        result = analyze_error("IndexError: list index out of range", "Python")
        self.assertEqual(result["category"], "IndexError")
        self.assertIn("len(items)", result["example"])

    def test_general_mode_skips_pattern_matching(self):
        result = analyze_error("NameError: name 'x' is not defined", "Python", "general")
        self.assertEqual(result["confidence"], "General guidance")
        self.assertEqual(len(result["followups"]), 2)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_analyze_returns_json(self):
        response = self.client.post(
            "/api/analyze",
            json={"error": "NameError: name 'x' is not defined", "language": "Python"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["category"], "NameError")

    def test_empty_error_is_rejected(self):
        response = self.client.post("/api/analyze", json={"error": "  ", "language": "Python"})
        self.assertEqual(response.status_code, 400)

    def test_invalid_language_is_rejected(self):
        response = self.client.post(
            "/api/analyze", json={"error": "Unknown error", "language": "Cobol"}
        )
        self.assertEqual(response.status_code, 400)

    def test_general_mode_is_available_for_extended_languages(self):
        response = self.client.post(
            "/api/analyze",
            json={"error": "A compiler error", "language": "Swift", "mode": "general"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["confidence"], "General guidance")

if __name__ == "__main__":
    unittest.main()

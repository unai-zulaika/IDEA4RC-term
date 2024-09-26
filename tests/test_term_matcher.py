import unittest
from term_matcher.term_matcher import load_term_to_code, match_terms

class TestTermMatcher(unittest.TestCase):
    
    def setUp(self):
        self.term_to_code = {
            "angiomyxoma": "C01",
            "carcinoma": "C02",
            "high blood pressure": "HBP01",
            "heart disease": "HD01"
        }
        self.text = "The patient with angiomyxoma and carcinoma had high blood pressure."

    def test_match_terms(self):
        result = match_terms(self.text, self.term_to_code)
        expected = ["C01", "C02", "HBP01"]
        self.assertEqual(result[0], expected)

if __name__ == "__main__":
    unittest.main()

from term_matcher import load_term_to_code, match_terms

# Load term-to-code mappings
term_to_code = load_term_to_code("dictionaries/term_to_code.json")

# Input text
text = "The patient with angiomyxoma and carcinoma was diagnosed."

# Match terms to codes
matched_codes, matched_terms = match_terms(text, term_to_code, threshold=50)

# Output matched codes
print("Matched Codes:", matched_codes)
# Optionally, output matched terms for debugging
print("Matched Terms:", matched_terms)
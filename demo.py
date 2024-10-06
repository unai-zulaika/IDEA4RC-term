from term_matcher import load_term_to_code, match_terms, match_terms_variable_names

# Load term-to-code mappings
term_to_code = load_term_to_code("dictionaries/term_to_code.json")

# Input text
text = "Patients diagnosed with solitary fibrous tumour."

# Match terms to codes
matched_codes, matched_terms = match_terms(text, term_to_code, threshold=45)

# Output matched codes
print("Matched Codes:", matched_codes)
# Optionally, output matched terms for debugging
print("Matched Terms:", matched_terms)

print("#" * 25)
print("\n")

# Load term-to-code mappings
term_to_code = load_term_to_code("dictionaries/code_to_term_variable.json")

maps = match_terms_variable_names(text, term_to_code, threshold=60)

print(maps)

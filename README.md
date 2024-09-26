
# Text-to-AthenaCode 

This library simply receives a input text and matches possible terms against a dictionary of terms that contain their associated Athena codes. For instance:

For the terms to code dictionary:

```json
"Male": 8507,
"Female": 8532,
"Angiomyxoma": 4239956,
```
and input text,
- "Query for all female patients diagnosed with angiomyxoma"


the library returns:

- "Query for all 8532 patients diagnosed with 4239956"


Consider that the dictionary terms can be obtained from anywhere, in this case we are using it for the IDEA4RC project's datamodel. 

## Methods

Fuzy string matching.

## How to use it

- Just install requirements (check end of file)
- Run `DM_codes_extraction` for obtaining the term_to_code.json. This step can be replaced for any other dictionaries.
- Run `demo.py` for a demo

```python
from term_matcher import load_term_to_code, match_terms

# Load term-to-code mappings
term_to_code = load_term_to_code("dictionaries/term_to_code.json") # if working with term to code

# Input text
text = "The patient with angiomyxoma and carcinoma was diagnosed."

# Match terms to codes
matched_codes, matched_terms = match_terms(text, term_to_code, threshold=50)

# Output matched codes
print("Matched Codes:", matched_codes)
# Optionally, output matched terms for debugging
print("Matched Terms:", matched_terms)
```

Output:

```
Matched Codes: [4239956, 4233949, 4175678, 4164740, 4206785, 4224593, 37156145, 4241843, 4029680, 4022895]
Matched Terms: ['Angiomyxoma', 'Verrucous carcinoma', 'Giant cell carcinoma', 'Acinar cell carcinoma', 'Schneiderian carcinoma', 'Juvenile carcinoma of the breast', 'Squamous cell carcinoma', 'Adenosquamous carcinoma', 'Myoepithelial carcinoma', 'Adenoid cystic carcinoma']
```

## Improvements

1. Synonyms
2. Multi-term matching
3. ElasticSearch for bigger size dictionaries (basically full Athena Concepts).

## Installation as package

```
pip install -e .
```

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

## Diagnosis Code Search Web UI

A standalone web service for searching IDEA4RC diagnosis codes by name and filtering by topography.

### Requirements

```
pip install flask rapidfuzz
```

The following CSV files must be present in the project root:
- `IDEA4RC - Diagnosis codes - diagnosis-codes-list.csv`
- `Topography site ICD-O_October_2025_OMOP.xlsx - Topography.csv`

### Run the service

```bash
python diagnosis_search.py
```

Then open **http://localhost:5001** in your browser.

### Features

- **Name search** — fuzzy match against diagnosis names (handles typos, hyphens, caps).
  Example: `"well differenciated"` matches `"well-differentiated"`.
- **Topography filters** — cascading dropdowns for Macrogrouping → Group → Site
  (e.g. *Soft tissue* → *Lower limbs* → *Foot*).
- **Filter-only mode** — leave the search box empty and apply a topography filter
  to retrieve all IDs for that anatomical region.
- **Copy IDs** — all matching IDs are shown comma-separated and can be copied with one click.
- **Fuzzy threshold** — adjustable slider (50–100, default 80).

### Run Playwright UI tests

```bash
npm install playwright
node test_ui.mjs
```

## Improvements

1. Synonyms
2. Multi-term matching
3. ElasticSearch for bigger size dictionaries (basically full Athena Concepts).

## Installation as package

```
pip install -e .
```
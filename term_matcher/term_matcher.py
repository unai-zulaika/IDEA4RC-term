import json
from rapidfuzz import process, fuzz, utils
from typing import List, Dict, Union
from tqdm import tqdm


def load_term_to_code(file_path: str) -> Dict[str, Union[str, List[str]]]:
    """
    Load the term-to-code mappings from a JSON file.

    Args:
        file_path (str): Path to the JSON file containing term-to-code mappings.

    Returns:
        dict: A dictionary where keys are terms and values are codes or a list of codes.
    """
    with open(file_path, 'r') as file:
        return json.load(file)


def preprocess_text(text: str) -> str:
    """
    Preprocess text by lowercasing, removing unnecessary characters, etc.

    Args:
        text (str): The input text to be preprocessed.

    Returns:
        str: Preprocessed text.
    """
    return utils.default_process(text)


def match_terms(text: str, term_to_code: Dict[str, Union[str, List[str]]], threshold: int = 80) -> List[str]:
    """
    Match the terms in the text against the term-to-code dictionary using fuzzy matching.

    Args:
        text (str): The input text to match.
        term_to_code (dict): A dictionary of term-to-code mappings.
        threshold (int, optional): Minimum fuzzy match score. Defaults to 80.

    Returns:
        List[str]: A list of matched codes.
    """
    matched_codes = []

    # Preprocess the input text
    processed_text = preprocess_text(text)

    # Create a dictionary with preprocessed terms
    terms = {preprocess_text(term): term for term in term_to_code.keys()}

    # Perform fuzzy matching
    matches = process.extract(processed_text, terms.keys(), scorer=fuzz.token_set_ratio, limit=10)

    # Iterate over matches and add matching codes
    for match_term, score, _ in tqdm(matches):
        if score >= threshold:
            original_term = terms[match_term]
            code = term_to_code[original_term]
            if isinstance(code, list):
                matched_codes.extend(code)
            else:
                matched_codes.append(code)

    return matched_codes, [terms[match[0]] for match in matches if match[1] >= threshold]

import json
from rapidfuzz import process, fuzz, utils
from typing import List, Dict, Union
from tqdm import tqdm
import re


def load_term_to_code(file_path: str) -> Dict[str, Union[str, List[str]]]:
    """
    Load the term-to-code mappings from a JSON file.

    Args:
        file_path (str): Path to the JSON file containing term-to-code mappings.

    Returns:
        dict: A dictionary where keys are terms and values are codes or a list of codes.
    """
    with open(file_path, "r") as file:
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


def match_terms(
    text: str, term_to_code: Dict[str, Union[str, List[str]]], threshold: int = 80
) -> List[str]:
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
    matches = process.extract(
        processed_text, terms.keys(), scorer=fuzz.token_set_ratio, limit=10
    )

    # Iterate over matches and add matching codes
    for match_term, score, _ in tqdm(matches):
        if score >= threshold:
            original_term = terms[match_term]
            code = term_to_code[original_term]
            if isinstance(code, list):
                matched_codes.extend(code)
            else:
                matched_codes.append(code)

    return matched_codes, [
        terms[match[0]] for match in matches if match[1] >= threshold
    ]


def match_terms_variable_names(
    text: str,
    code_to_term_variable: Dict[str, Union[str, List[str]]],
    threshold: int = 80,
) -> List[str]:
    """
    Match the terms in the text against the term-to-code dictionary using fuzzy matching.

    Args:
        text (str): The input text to match.
        code_to_term_variable (dict): A dictionary of code_to_term_variable mappings.
        threshold (int, optional): Minimum fuzzy match score. Defaults to 80.

    Returns:
        List[str]: A list of matched codes.
    """
    matched_codes = []
    matched_vnames = []
    matched_terms_list = []
    matched_json = {}

    # Preprocess the input text
    processed_text = preprocess_text(text)

    # Create a dictionary with preprocessed terms
    terms = {
        preprocess_text(code_to_term_variable[code]["term"]): code
        for code in code_to_term_variable.keys()
    }

    # Perform fuzzy matching
    matches = process.extract(
        processed_text, terms.keys(), scorer=fuzz.token_set_ratio, limit=10
    )
    processed_text_words = set(processed_text.lower().split())

    # Iterate over matches and add matching codes
    for match_term, score, _ in tqdm(matches):
        if score >= threshold:
            matched_term_words = set(match_term.lower().split())
            match_words = processed_text_words.intersection(matched_term_words)

            matched_terms_list.append(match_term)
            # code = code_to_term_variable[original_term]
            code = list(
                filter(
                    lambda x: preprocess_text(code_to_term_variable[x]["term"])
                    == match_term,
                    code_to_term_variable,
                )
            )[
                0
            ]  # suboptimal
            if isinstance(code, list):
                matched_codes.extend(code)
                matched_vnames.extend(code_to_term_variable[code]["variable_name"])
            else:
                matched_codes.append(code)
                matched_vnames.append(code_to_term_variable[code]["variable_name"])

            key = " ".join(match_words)
            if key not in matched_json:
                matched_json[key] = []
            matched_json[key].append(
                {
                    "score": score,
                    "variable_name": code_to_term_variable[code]["variable_name"],
                    "term": match_term,
                    "code": code,
                }
            )

    return matched_json

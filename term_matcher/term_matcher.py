import json
from rapidfuzz import process, fuzz, utils
from typing import List, Dict, Union
from tqdm import tqdm
import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

try:
    print("Downloading NLTK resources...")
    nltk.download("stopwords")
    nltk.download("punkt")

except:
    pass

stop_words = set(stopwords.words("english"))


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


def filter_label(label):
    label = utils.default_process(label)
    word_tokens = word_tokenize(label)
    # converts the words in word_tokens to lower case and then checks whether
    # they are present in stop_words or not
    filtered_sentence = [w for w in word_tokens if not w.lower() in stop_words]
    # with no lower case conversion
    filtered_sentence = []
    for w in word_tokens:
        if w not in stop_words:
            filtered_sentence.append(w)
    return " ".join(filtered_sentence)


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
    terms = {filter_label(preprocess_text(term))             : term for term in term_to_code.keys()}
    print(processed_text)
    print("KEKE")
    # Perform fuzzy matching
    matches = process.extract(
        processed_text, terms.keys(), scorer=fuzz.token_set_ratio, limit=10
    )
    print(matches)

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
    # terms = {
    #     preprocess_text(code_to_term_variable[match["code"]]["term"]): match
    #     for match in code_to_term_variable.values()
    # }
    terms = {
        filter_label(code_to_term_variable[key]["term"]): values["code"]
        for key, values in code_to_term_variable.items()
    }

    filtered_terms = [filter_label(term) for term in terms.keys()]
    # Perform fuzzy matching
    matches = process.extract(
        processed_text,
        # filter_label(terms.keys()),
        filtered_terms,
        scorer=fuzz.token_set_ratio,
        limit=10,
    )

    processed_text_words = set(processed_text.lower().split())

    # Iterate over matches and add matching codes
    for match_term, score, _ in tqdm(matches):
        if score >= threshold:
            matched_term_words = set(match_term.lower().split())
            match_words = processed_text_words.intersection(matched_term_words)

            matched_terms_list.append(match_term)

            code_keys = []  # Initialize an empty list to store matching keys

            # Iterate over the keys in code_to_term_variable
            for x in code_to_term_variable:
                # Check if the preprocessed term matches the match_term
                if filter_label(code_to_term_variable[x]["term"]) == match_term:
                    code_keys.append(x)  # Add the matching key to the list
                    break  # Exit the loop after finding the first match

            # If code_keys is not empty, the first match will be at index 0
            if code_keys:
                code_keys = code_keys[0]  # Get the first matching key
            else:
                code_keys = None  # Handle the case where there are no matches

            if isinstance(code_keys, list):
                code = [code_to_term_variable[match]["code"]
                        for match in code_keys]
                matched_codes.extend(code)
                matched_vnames.extend(
                    code_to_term_variable[code_keys]["variable_name"])
                matched_vnames.extend(
                    code_to_term_variable[code_keys]["entity"])
            else:
                code = code_to_term_variable[code_keys]["code"]
                matched_codes.append(code)
                matched_vnames.append(
                    code_to_term_variable[code_keys]["variable_name"])
                matched_vnames.append(
                    code_to_term_variable[code_keys]["entity"])

            key = " ".join(match_words)
            if key not in matched_json:
                matched_json[key] = []
            matched_json[key].append(
                {
                    "score": score,
                    "variable_name": code_to_term_variable[code_keys]["variable_name"],
                    "entity": code_to_term_variable[code_keys]["entity"],
                    "term": match_term,
                    "code": code,
                }
            )

    return matched_json

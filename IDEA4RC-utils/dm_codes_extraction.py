import pandas as pd
from tqdm import tqdm
import re
import json

SHEET_ID = "1Vw1Dr2K4oG__cDQTutGaJhZvGUvQTLwc4qWreP6qMSs"

SHEETS_TO_PROCESS = list(range(7, 24))

print("Starting conversion...")

# load file
xls = pd.ExcelFile(
    f"https://docs.google.com/spreadsheets/export?id={SHEET_ID}&format=xlsx"
)

# Initialize dictionary
result_dict = {}
id_variable_term = {}

# let's process each sheet
for index, sheet_number in enumerate(tqdm(SHEETS_TO_PROCESS)):
    # read each sheet
    dataframe = pd.read_excel(xls, sheet_name=sheet_number)
    for vname, terms, entity, description, object_property in dataframe[
        ["ObjectPropertyLabelEN", "Vocabulary",
         "ObjectClass", "DataElementConceptDefEN", "ObjectProperty"]
    ].itertuples(index=False):
        for line in str(terms).splitlines():
            # Regular expression to match the format
            pattern = r"^(?P<text>[^-]+) - (?P<number>\d+)$"

            # Match the pattern
            match = re.match(pattern, line)
            if entity == "HistologySubGroup":
                entity = "Diagnosis"
                vname = "Histology"
            if entity == "Subsite":
                entity = "Diagnosis"
                vname = "Topography"
            # Check if the match was successful
            if match:
                text = match.group(
                    "text"
                ).strip()  # Extract and strip any leading/trailing whitespace
                # Convert the number to an integer
                number = int(match.group("number"))
                result_dict[text] = number  # Add to dictionary
                key = entity + "_" + object_property + "_" + text
                id_variable_term[key] = {
                    "variable_name": vname,
                    "term": text,
                    "entity": entity,
                    "description": description,
                    "code": number,
                }


# Print the result
print(result_dict)
with open("dictionaries/term_to_code.json", "w") as fp:
    json_object = json.dump(result_dict, fp)

with open("dictionaries/code_to_term_variable.json", "w") as fp:
    json_object = json.dump(id_variable_term, fp)

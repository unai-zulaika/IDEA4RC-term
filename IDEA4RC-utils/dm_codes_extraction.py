import pandas as pd
from tqdm import tqdm
import re
import json

SHEET_ID = "1Vw1Dr2K4oG__cDQTutGaJhZvGUvQTLwc4qWreP6qMSs"

SHEETS_TO_PROCESS = list(range(7, 19))

print("Starting conversion...")

# load file
xls = pd.ExcelFile(
    f"https://docs.google.com/spreadsheets/export?id={SHEET_ID}&format=xlsx"
)

# Initialize dictionary
result_dict = {}

# let's process each sheet
for index, sheet_number in enumerate(tqdm(SHEETS_TO_PROCESS)):
    # read each sheet
    dataframe = pd.read_excel(xls, sheet_name=sheet_number)
    for text in dataframe["Vocabulary"]:
        
        for line in str(text).splitlines():
            # Regular expression to match the format
            pattern = r'^(?P<text>[^-]+) - (?P<number>\d+)$'

            # Match the pattern
            match = re.match(pattern, line)

            # Check if the match was successful
            if match:
                text = match.group('text').strip()  # Extract and strip any leading/trailing whitespace
                number = int(match.group('number'))  # Convert the number to an integer
                result_dict[text] = number  # Add to dictionary


# Print the result
print(result_dict)
with open('dictionaries/term_to_code.json', 'w') as fp:
    json_object = json.dump(result_dict, fp) 

    
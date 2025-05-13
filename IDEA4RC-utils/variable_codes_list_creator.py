import pandas as pd
from tqdm import tqdm
import re
import json

SHEET_ID = "1ANErBpHQAW6ngn1kq-a7rPpeTosG-z2PHnwfUT6IUKI"

SHEETS_TO_PROCESS = list(range(8, 26))

print("Starting conversion...")

# load file
xls = pd.ExcelFile(
    f"https://docs.google.com/spreadsheets/export?id={SHEET_ID}&format=xlsx"
)

SHEET_NAMES = ["Patient", "PatientFollowUp", "HospitalData", "HospitalPatientRecords", "CancerEpisode", "Diagnosis", "ClinicalStage", "PathologicalStage","EpisodeEvent","DiseaseExtent", "GeneticTestExpression","Surgery","SystemicTreatment","Radiotherapy", "RegionalDeepHyperthemia","IsolatedLimbPerfusion","DrugsForTreatments","OverallTreatmentResponmse","AdverseEvent"]
# Initialize dictionary
result_dict = {}
id_variable_term = {}

# let's process each sheet
for index, sheet_number in enumerate(tqdm(SHEETS_TO_PROCESS)):
    # read each sheet
    dataframe = pd.read_excel(xls, sheet_name=sheet_number)
    variables = {}
    for vname, terms, entity, description, object_property, datatype in dataframe[
        ["ObjectPropertyLabelEN", "Vocabulary",
         "ObjectClass", "DataElementConceptDefEN", "ObjectProperty", "FormatConceptualDomain"]
    ].itertuples(index=False):
        # print(
        #     f"Processing sheet {index + 1}/{len(SHEETS_TO_PROCESS)}: {sheet_number} - {vname} - {terms} - {entity} - {description} - {object_property} - {datatype}"
        # )
        # exit()
        if datatype != "Code":
            # Skip the row if the datatype is not "Code"
            continue
        # store all the codes in array
        codes = []
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
                codes.append(number)  # Add to array
            
        # add to dictionary
        if len(codes) > 0:
            # Check if the entity already exists in the dictionary
            if entity not in result_dict:
                # result_dict[vname] = codes
                variables[vname] = codes
    print(variables)
    result_dict[SHEET_NAMES[index]] = variables

                # result_dict[text] = number  # Add to dictionary
                # key = entity + "_" + object_property + "_" + text
                # id_variable_term[key] = {
                #     "variable_name": vname,
                #     "term": text,
                #     "entity": entity,
                #     "description": description,
                #     "code": number,
                # }


# Print the result
print(result_dict)
with open("variables_codes.json", "w") as fp:
    json_object = json.dump(result_dict, fp)

# with open("dictionaries/code_to_term_variable.json", "w") as fp:
#     json_object = json.dump(id_variable_term, fp)

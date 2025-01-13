import csv
import json

# Step 1: Read the CSV file
csv_file = 'input_parameters.csv'  # Replace with your CSV file path
json_file = 'parameters_from_csv.json'  # The desired output JSON file

# Step 2: Convert CSV to a List of Dictionaries
data = []
with open(csv_file, mode='r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)  # Automatically uses the first row as headers
    for row in reader:
        data.append(row)  # Add each row as a dictionary to the list

# Step 3: Write the data to a JSON file
with open(json_file, mode='w', encoding='utf-8') as f:
    json.dump(data, f, indent=4)  # Pretty-print JSON with an indentation level of 4

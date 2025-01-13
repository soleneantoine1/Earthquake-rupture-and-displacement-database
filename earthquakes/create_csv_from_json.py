import json
import pandas as pd

# Open and read the JSON file
with open('input_test_simple.json', 'r') as f:
    data = json.load(f)

# Convert to a table (DataFrame)
df = pd.DataFrame(data)

# If you want to save the table to a CSV file:
df.to_csv('test_input.csv', index=False)

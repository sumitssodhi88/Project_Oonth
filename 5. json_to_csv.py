import json
import csv
import os

# Step 1: Prompt for the folder containing JSON files
folder_path = input("Enter the folder path containing JSON files: ")

# Validate folder path
if not os.path.exists(folder_path):
    print("Invalid folder path. Please try again.")
    exit()

# Step 2: Find all JSON files in the folder
json_files = [os.path.join(folder_path, file) for file in os.listdir(folder_path) if file.endswith('.json')]

if not json_files:
    print("No JSON files found in the provided folder.")
    exit()

# Step 3: Load and merge JSON data
all_data = []

for file in json_files:
    with open(file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        all_data.extend(data)

# Step 4: Define CSV headers and write to CSV
csv_file = os.path.join(folder_path, 'combined_data.csv')
headers = ['question', 'instruction', 'answer', 'metadata', 'context']

with open(csv_file, 'w', encoding='utf-8', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=headers)
    writer.writeheader()
    for entry in all_data:
        writer.writerow({
            'question': entry.get('question', ''),
            'instruction': entry.get('instruction', ''),
            'answer': entry.get('answer', ''),
            'metadata': entry.get('metadata', ''),
            'context': entry.get('context', '')
        })

print(f"Data successfully combined and written to {csv_file}")

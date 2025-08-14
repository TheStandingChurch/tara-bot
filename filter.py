import csv
import json

# Input and output file names
input_csv = "att.csv"
output_json = "apete_matches.json"

# Storage for matching rows
matches = []

# Read CSV and look for "Apete"
with open(input_csv, newline="", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        # Check if any field contains "Apete"
        if any("sango" in str(value.lower()) for value in row.values()):
            matches.append(row)

# Write matches to JSON
with open(output_json, "w", encoding="utf-8") as jsonfile:
    json.dump(matches, jsonfile, indent=4, ensure_ascii=False)

print(f"Found {len(matches)} matching rows. Saved to {output_json}")

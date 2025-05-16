import json

# Step 1: Read the original JSON data from a file
with open('sermons.json', 'r', encoding='utf-8') as infile:
    original_data = json.load(infile)

# Step 2: Transform the data
transformed = []

for item in original_data:
    transformed_item = {
        "text": f"{item['title']}\n\n{item['description']}\n\nListen. Share. Be Transformed.",
        "media": item['cover_image'],
        "audios": [item['audio_url']]
    }
    transformed.append(transformed_item)

# Step 3: Write the transformed data to a new file
with open('transformed_sermons.json', 'w', encoding='utf-8') as outfile:
    json.dump(transformed, outfile, ensure_ascii=False, indent=2)

print("Transformation complete. Output saved to transformed_sermons.json.")

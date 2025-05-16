import json

def restructure_messages(raw_messages):
    structured = []
    current = None

    for entry in raw_messages:
        if "text" in entry:
            # Start a new message group
            current = {
                "text": entry["text"],
                "media": entry.get("media", None),
                "audios": []
            }
            structured.append(current)
        elif "audio" in entry and current:
            current["audios"].extend(entry["audio"])

    return structured


def main():
    file_path = "supernatural_business.json"

    # Read the raw JSON list
    with open(file_path, "r", encoding="utf-8") as f:
        raw_messages = json.load(f)

    # Restructure the messages
    structured_messages = restructure_messages(raw_messages)

    # Write the structured list back to the same file
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(structured_messages, f, ensure_ascii=False, indent=2)

    print(f"Restructured messages saved to {file_path}")


if __name__ == "__main__":
    main()

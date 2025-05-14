import re
import json
from collections import defaultdict

def parse_telegram_content(file_path):
    """Parse Telegram content from a text file and extract structured information."""
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Define patterns to extract entries
    text_pattern = re.compile(r'Text found: (\d+) - (.*?)(?=(?:Audio found:|Image found:|Other content found:|$|\Z))', re.DOTALL)
    # For audio, capture both the ID and the number (which will be used in the URL)
    audio_pattern = re.compile(r'Audio found: (\d+) - (\d+)')
    image_pattern = re.compile(r'Image found: (\d+)', re.DOTALL)

    
    # Find all matches
    text_matches = text_pattern.findall(content)
    audio_matches = audio_pattern.findall(content)
    image_matches = image_pattern.findall(content)
    
    # Create a dictionary to organize entries by ID
    content_by_id = defaultdict(dict)
    
    # Process text entries
    for text_id, text_content in text_matches:
        content_by_id[text_id]['text'] = text_content.strip()
    
    # Process audio entries - this is fixed to use the actual audio number
    for audio_id, audio_number in audio_matches:
        # Use the audio number from "Audio found: X - Y" where X is the number
        audio_url = f"https://t.me/TheSupernaturalStudent/{audio_id}"
        
        if 'audio' not in content_by_id[audio_id]:
            content_by_id[audio_id]['audio'] = [audio_url]
        else:
            content_by_id[audio_id]['audio'].append(audio_url)
    
    # Process image entries
    for img_id in image_matches:
        content_by_id[img_id]['media'] = f"https://t.me/TheSupernaturalStudent/{img_id}"

    # Build the final result array, sorting by ID in reverse order (bottom first)
    result = []
    for entry_id in sorted(content_by_id.keys(), key=int, reverse=True):
        # Always ensure 'audio' is an array even if there's only one item
        entry = content_by_id[entry_id]
        if 'audio' in entry and not isinstance(entry['audio'], list):
            entry['audio'] = [entry['audio']]
        result.append(entry)
    
    return result

def main():
    """Main function to parse the file and output JSON."""
    file_path = 'supernatural_student.txt'  # Change this to your actual file path
    output_path = 'supernatural_student.json'
    
    try:
        parsed_entries = parse_telegram_content(file_path)
        
        # Save to JSON file
        with open(output_path, 'w', encoding='utf-8') as json_file:
            json.dump(parsed_entries, json_file, indent=2)
        
        print(f"Successfully parsed {len(parsed_entries)} entries and saved to {output_path}")
        
        # Print a sample for verification
        if parsed_entries:
            sample_entry = parsed_entries[0]
            print("\nSample of parsed content (first entry):")
            print(json.dumps(sample_entry, indent=2))
            
            # Print specific verification of audio URLs
            if 'audio' in sample_entry:
                print("\nVerifying audio URLs:")
                for url in sample_entry['audio']:
                    print(f"  - {url}")
    
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
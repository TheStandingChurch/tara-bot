import re
import time
from telethon import TelegramClient

# Replace these with your values
api_id = "20131774"
api_hash = 'bc5fc205f1b8082a88f8d6a4b4621105'

# e.g., 'mychannel' or 'https://t.me/mychannel'
channel_username = 'TheSupernaturalBusinessMan'

phone_number = '+2349041128704'

# File to store the messages
output_file = 'supernatural_business.txt'


# Create the Telegram client
client = TelegramClient('session_name', api_id, api_hash)


def contains_link_or_date(text):
    # return False 
    text = text.lower()

    # Check for links
    link_pattern = r'(https?://|www\.|t\.me|\.com|\.org|\.ly|\.net|\.ng|\.io)'

    # # Check for greetings like "happy new year"
    # text = text.lower()
    # array = ['happy new year', 'happy new month', 'testimo', 'udent']
    # if any(keyword in text for keyword in array):
    #     return True

    # Check for month names
    # months = [
    #     'january', 'february', 'march', 'april', 'may', 'june',
    #     'july', 'august', 'september', 'october', 'november', 'december',
    #     'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
    # ]
    # if any(month in text for month in months):
    #     return True

    # Check for date-like patterns
    date_patterns = [
        # 14/05/2025 or 14-05-25
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',               # 2025-05-14
        r'\b\d{1,2}(st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b',
        r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(st|nd|rd|th)?\b',
    ]

    if re.search(link_pattern, text):
        return True

    # for pattern in date_patterns:
    #     if re.search(pattern, text):
    #         return True

    return False


async def fetch_messages():
    await client.start(phone_number)
    channel = await client.get_entity(channel_username)

    limit = 50
    offset_id = 0

    while True:
        messages = await client.get_messages(channel, limit=limit, offset_id=offset_id)

        if not messages:
            print("No more messages to fetch.")
            break

        with open(output_file, 'a', encoding='utf-8') as f:
            for message in messages:
                if message.video:
                    continue

                if message.audio and not message.video:
                    f.write(
                        f"Audio found: {message.id} - {message.audio.id}\n")

                if message.text and not contains_link_or_date(message.text):
                    f.write(f"Text found: {message.id} - {message.text}\n")

                    if message.photo:
                        f.write(f"Image found: {message.id}\n")

        offset_id = messages[-1].id
        print("Waiting for 5 seconds before fetching next batch...")
        time.sleep(5)

# Run the client
with client:
    client.loop.run_until_complete(fetch_messages())

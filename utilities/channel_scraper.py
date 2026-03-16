"""
Scrapes all audio+text posts from the Telegram channel @pst_tara using Telethon
(full MTProto API — handles grouped messages and consecutive audio→text pairs).

Requires in .env:
  TELEGRAM_API_ID=...
  TELEGRAM_API_HASH=...
  TELEGRAM_BOT_TOKEN=...

Each saved post:
  {
    "message_id": 123,
    "text": "...",
    "date": "2024-01-15",
    "channel_link": "https://t.me/pst_tara/123",
    "photo_path": "utilities/cover_photos/123.jpg",  # local path, empty if no cover
    "audio_file_id": "id:access_hash",
    "audio_filename": "sermon.mp3"
  }

Run:
  python utilities/channel_scraper.py
"""

import asyncio
import json
import os
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import (
    MessageMediaDocument,
    MessageMediaPhoto,
    DocumentAttributeAudio,
    DocumentAttributeFilename,
)

load_dotenv()

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
PHONE = os.environ.get("TELEGRAM_PHONE") or None
CHANNEL = "pst_tara"
OUT_PATH = os.path.join(os.path.dirname(__file__), "channel_messages.jsonl")


def is_audio(message) -> bool:
    """True if the message contains an audio/voice document."""
    if not isinstance(message.media, MessageMediaDocument):
        return False
    doc = message.media.document
    for attr in doc.attributes:
        if isinstance(attr, (DocumentAttributeAudio,)):
            return True
        if isinstance(attr, DocumentAttributeFilename):
            fn = attr.file_name.lower()
            if fn.endswith((".mp3", ".m4a", ".ogg", ".wav", ".aac", ".opus")):
                return True
    return False


def get_audio_info(message):
    doc = message.media.document
    file_id = f"{doc.id}:{doc.access_hash}"
    filename = ""
    for attr in doc.attributes:
        if isinstance(attr, DocumentAttributeFilename):
            filename = attr.file_name
    return file_id, filename


def has_photo(message):
    return isinstance(message.media, MessageMediaPhoto)


async def scrape():
    client = TelegramClient("tara_scraper_session", API_ID, API_HASH)
    await client.start(phone=PHONE)  # prompts for phone + code on first run; session saved after
    print(f"Connected. Fetching messages from @{CHANNEL} ...")
    async with client:

        # Load all messages into memory so we can look ahead/behind
        all_msgs = []
        async for msg in client.iter_messages(CHANNEL, reverse=True):
            all_msgs.append(msg)
        print(f"  Loaded {len(all_msgs)} total messages")

        # Group messages by grouped_id so we can pair audio + photo in albums
        groups: dict[int, list] = {}
        for msg in all_msgs:
            if msg.grouped_id:
                groups.setdefault(msg.grouped_id, []).append(msg)

        posts = []
        seen_ids = set()

        for i, msg in enumerate(all_msgs):
            if msg.id in seen_ids:
                continue

            if not is_audio(msg):
                continue

            audio_file_id, audio_filename = get_audio_info(msg)
            photo_msg = None   # the message that carries the cover photo
            text = msg.message or ""  # caption on the audio message itself

            # Case 1: grouped album (audio + photo posted together)
            if msg.grouped_id and msg.grouped_id in groups:
                siblings = groups[msg.grouped_id]
                for sib in siblings:
                    seen_ids.add(sib.id)
                    if photo_msg is None and has_photo(sib):
                        photo_msg = sib
                    if not text and sib.message:
                        text = sib.message

            # Case 2: next message is a photo (cover art posted right after)
            if photo_msg is None and i + 1 < len(all_msgs):
                nxt = all_msgs[i + 1]
                if has_photo(nxt) and not nxt.grouped_id:
                    photo_msg = nxt
                    seen_ids.add(nxt.id)
                    if not text and nxt.message:
                        text = nxt.message

            # Case 3: next message is a plain text (description posted separately)
            check_idx = i + 1
            while check_idx < len(all_msgs):
                nxt = all_msgs[check_idx]
                if nxt.id in seen_ids:
                    check_idx += 1
                    continue
                if check_idx == i + 1 and not nxt.media and nxt.message and not is_audio(nxt):
                    if not text:
                        text = nxt.message
                    seen_ids.add(nxt.id)
                break

            seen_ids.add(msg.id)

            if not text:
                print(f"  ⚠️  id={msg.id} — audio with no text, skipping")
                continue

            photo_message_id = photo_msg.id if photo_msg is not None else None

            post = {
                "message_id": msg.id,
                "text": text.strip(),
                "date": msg.date.strftime("%Y-%m-%d"),
                "channel_link": f"https://t.me/{CHANNEL}/{msg.id}",
                "photo_message_id": photo_message_id,
                "audio_filename": audio_filename,
            }
            posts.append(post)
            print(f"  ✅  id={msg.id}  {audio_filename or 'audio'}  photo={'yes' if photo_message_id else 'no'}  |  {text[:60]!r}")

        posts.sort(key=lambda p: p["message_id"])
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            for p in posts:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")

        print(f"\nSaved {len(posts)} posts to {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(scrape())

import json
import openai
import os
import numpy as np
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")

client = openai.OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


SERMONS = load_jsonl(os.path.join(os.path.dirname(__file__), "utilities", "sermons.jsonl"))
SERMON_EMBEDDINGS = None  # pre-computed at startup


def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2.T) / (np.linalg.norm(vec1) * np.linalg.norm(vec2, axis=1, keepdims=True))


def get_embeddings(texts: list) -> np.ndarray:
    batch_size = 100
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(
            input=batch,
            model="text-embedding-3-small"
        )
        all_embeddings.extend([item.embedding for item in response.data])
    return np.array(all_embeddings)


def rank_sermons(user_query: str) -> list:
    query_embedding = get_embeddings([user_query])  # 1 API call
    scores = cosine_similarity(query_embedding, SERMON_EMBEDDINGS)[0]
    return sorted(zip(SERMONS, scores), key=lambda x: x[1], reverse=True)


async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Hello! I'm Pastor Tara Akinkuade's A.I (v1.1). \n"
        "I am here to assist you in finding messages tailored to your specific needs.\n\n"
        "Type what you're dealing with or how you feel — I'll help you find the right message."
    )


async def handle_message(update: Update, context: CallbackContext):
    user_query = update.message.text

    await update.message.reply_text("Hmm... Please wait a few seconds while I search for messages to help you.")

    ranked = rank_sermons(user_query)

    lines = []
    for i, (sermon, _) in enumerate(ranked[:5], 1):
        line = f"*{i}. {sermon['title']}*"
        if sermon.get('audio_url'):
            line += f"\n🎧 [Listen here]({sermon['audio_url']})"
        lines.append(line)

    await update.message.reply_text("\n\n".join(lines), parse_mode="Markdown")


def main():
    global SERMON_EMBEDDINGS
    logging.info("Pre-computing sermon embeddings...")
    texts = [f"{s['title']} {s['description']}" for s in SERMONS]
    SERMON_EMBEDDINGS = get_embeddings(texts)
    logging.info(f"Ready — {len(SERMONS)} sermons indexed.")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

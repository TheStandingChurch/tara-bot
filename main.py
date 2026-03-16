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


BASE_DIR = os.path.dirname(__file__)
MESSAGES = load_jsonl(os.path.join(BASE_DIR, "utilities", "channel_messages.jsonl"))
MESSAGE_EMBEDDINGS = None


def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2.T) / (np.linalg.norm(vec1) * np.linalg.norm(vec2, axis=1, keepdims=True))


def get_embeddings(texts: list) -> np.ndarray:
    batch_size = 100
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(input=batch, model="text-embedding-3-small")
        all_embeddings.extend([item.embedding for item in response.data])
    return np.array(all_embeddings)


def rank_messages(user_query: str) -> list:
    query_embedding = get_embeddings([user_query])
    scores = cosine_similarity(query_embedding, MESSAGE_EMBEDDINGS)[0]
    return sorted(zip(MESSAGES, scores), key=lambda x: x[1], reverse=True)


WELCOME = (
    "Hello! I'm Pastor Tara Akinkuade's A.I (v1.3).\n"
    "I am here to assist you in finding messages tailored to your specific needs.\n\n"
    "Type what you're dealing with or how you feel — I'll help you find the right message."
)


async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(WELCOME)


async def handle_message(update: Update, context: CallbackContext):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    user_query = update.message.text

    if context.user_data.get("greeted") is None:
        context.user_data["greeted"] = True
        await update.message.reply_text(WELCOME)

    await update.message.reply_text("Searching for messages to help you...")

    ranked = rank_messages(user_query)

    for i, (msg, _) in enumerate(ranked[:5], 1):
        text = msg.get("text", "")
        snippet = text[:300].rsplit(" ", 1)[0] + "..." if len(text) > 300 else text
        link = msg.get("channel_link", "")
        caption = f"*{i}.* {snippet}"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎧 Listen on channel", url=link)]]) if link else None

        photo_message_id = msg.get("photo_message_id")

        if photo_message_id:
            await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id="@pst_tara",
                message_id=photo_message_id,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
        else:
            await update.message.reply_text(
                caption,
                parse_mode="Markdown",
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )


def main():
    global MESSAGE_EMBEDDINGS
    logging.info("Pre-computing channel message embeddings...")
    MESSAGE_EMBEDDINGS = get_embeddings([m["text"] for m in MESSAGES])
    logging.info(f"Ready — {len(MESSAGES)} messages indexed.")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

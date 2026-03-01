import json
import openai
import os
import numpy as np
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, CallbackContext
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


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

MESSAGES = {
    'life':     load_jsonl(os.path.join(DATA_DIR, "life.jsonl")),
    'learning': load_jsonl(os.path.join(DATA_DIR, "student.jsonl")),
    'family':   load_jsonl(os.path.join(DATA_DIR, "family.jsonl")),
    'business': load_jsonl(os.path.join(DATA_DIR, "business.jsonl")),
}


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


def rank_messages(user_query: str, messages: list) -> list:
    texts = [m['text'] for m in messages]
    embeddings = get_embeddings([user_query] + texts)
    query_embedding = embeddings[0].reshape(1, -1)
    msg_embeddings = embeddings[1:]
    scores = cosine_similarity(query_embedding, msg_embeddings)[0]
    return sorted(zip(messages, scores), key=lambda x: x[1], reverse=True)


def category_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏅 Life of Victory", callback_data='life'),
            InlineKeyboardButton("💼 Business & Career", callback_data='business'),
        ],
        [
            InlineKeyboardButton("💖 Family & Relationships", callback_data='family'),
            InlineKeyboardButton("📘 Learning & Development", callback_data='learning'),
        ],
    ])


async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Hello! I'm Pastor Tara Akinkuade's A.I (v1.1). \n"
        "I am here to assist you in finding messages tailored to your specific needs.\n\n"
        "Please choose a category to narrow down your search for messages:",
        reply_markup=category_keyboard()
    )


async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    category = query.data
    context.user_data['selected_category'] = category

    category_names = {
        'life': "🏅 Life of Victory",
        'business': "💼 Business & Career",
        'family': "💖 Family & Relationships",
        'learning': "📘 Learning & Development",
    }

    if category in category_names:
        await query.edit_message_text(
            f"You selected: {category_names[category]}.\n\n"
            "Now type what you're dealing with or how you feel — I'll help you find the right message."
        )
    else:
        await query.edit_message_text("Sorry, I didn't understand that option.")


async def handle_message(update: Update, context: CallbackContext):
    user_query = update.message.text
    category = context.user_data.get('selected_category', '')

    if not category:
        await update.message.reply_text(
            "Please choose a category to narrow down your search for messages:",
            reply_markup=category_keyboard()
        )
        return

    await update.message.reply_text("Hmm... Please wait a few seconds while I search for messages to help you.")

    ranked = rank_messages(user_query, MESSAGES[category])

    for msg, _ in ranked[:5]:
        if category == 'life':
            await update.message.reply_photo(
                photo=msg['media'],
                caption=f"📖 {msg['text']}\n\n🔗 [Listen to message here]({msg['audios'][0]})",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"📖 {msg['text']}", parse_mode="Markdown")
            for audio_url in msg['audios']:
                await update.message.reply_text(f"🎧 [Listen here]({audio_url})", parse_mode="Markdown")

    context.user_data['selected_category'] = ""


def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

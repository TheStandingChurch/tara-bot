import ast
import openai
import os
import numpy as np
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, CallbackContext
from dotenv import load_dotenv

# from pst_tara import MESSAGES_INFO
from website_msgs import MESSAGES_INFO
from sup_student import SSTC_MESSAGES
from sup_family import SFTC_MESSAGES
from sup_business import SBTC_MESSAGES

# Load environment variables from .env file
load_dotenv()

# Get the API keys
API_KEY = os.getenv("API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Ensure you have your API key set in environment variables or pass it directly
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", API_KEY)

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)


# Function to calculate cosine similarity


def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2.T) / (np.linalg.norm(vec1) * np.linalg.norm(vec2, axis=1, keepdims=True))


def get_embeddings(texts: list) -> np.ndarray:
    """ Get embeddings for multiple texts in a single API call, optimized for large input sizes. """
    batch_size = 100  # Process in batches of 100 to avoid token limits
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(
            input=batch,
            model="text-embedding-3-small"
        )
        all_embeddings.extend([item.embedding for item in response.data])

    # Convert to NumPy array for fast processing
    return np.array(all_embeddings)


def rank_sermons(user_query: str, sermons):
    """ Rank sermons based on relevance to user_query using cosine similarity. """

    # Create list of sermon texts
    sermon_texts = [f"{s['description']}" for s in sermons]

    # Get embeddings for query + all sermons in a single batch call
    embeddings = get_embeddings([user_query] + sermon_texts)

    # Extract query embedding and sermon embeddings
    query_embedding = embeddings[0].reshape(1, -1)  # Shape: (1, D)
    sermon_embeddings = embeddings[1:]  # Shape: (N, D)

    # Compute cosine similarities efficiently
    similarity_scores = cosine_similarity(
        query_embedding, sermon_embeddings)[0]

    # Rank sermons by similarity
    ranked_results = sorted(zip(sermons, similarity_scores),
                            key=lambda x: x[1], reverse=True)

    return ranked_results


# Telegram command handlers
async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [
            InlineKeyboardButton("🏅 Life of Victory", callback_data='life'),
            InlineKeyboardButton("💼 Business & Career",
                                 callback_data='business'),
        ],
        [
            InlineKeyboardButton("💖 Family & Relationships",
                                 callback_data='family'),
            InlineKeyboardButton("📘 Learning & Development",
                                 callback_data='learning'),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        """Hello! I'm Pastor Tara Akinkuade's A.I (v1.1). 
    I am here to assist you in finding messages tailored to your specific needs.

    Please choose a category to narrow down your search for messages:
    """, reply_markup=reply_markup
    )


async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    category = query.data
    # ✅ Store selected category
    context.user_data['selected_category'] = category

    category_names = {
        'life': "🏅 Life of Victory",
        'business': "💼 Business & Career",
        'family': "💖 Family & Relationships",
        'learning': "📘 Learning & Development",
    }

    if category in category_names:
        await query.edit_message_text(
            f"You selected: {category_names[category]}.\n\nNow type what you're dealing with or how you feel — I'll help you find the right message."
        )
    else:
        await query.edit_message_text("Sorry, I didn't understand that option.")


# Handle the user's message and search for relevant messages
async def handle_message(update: Update, context: CallbackContext):
    user_query = update.message.text
    # Default to 'general' if no category set
    category = context.user_data.get('selected_category', '')

    if category:
        structured_messages = []
        await update.message.reply_text("Hmm... Please wait a few seconds while I search for messages to help you.")

        if category == 'life':
            structured_messages = MESSAGES_INFO
        elif category == 'learning':
            structured_messages = SSTC_MESSAGES
        elif category == "family":
            structured_messages = SFTC_MESSAGES
        else:
            structured_messages = SBTC_MESSAGES

        # Convert to searchable format
        searchable_messages = [
            {
                "description": msg["text"],
                "audio_url": msg["audios"],
                "media": msg["media"]
            }
            for msg in structured_messages
        ]

        # Rank messages based on the user query
        ranked = rank_sermons(user_query, searchable_messages)

        # Send back the top 5 ranked messages
        for sermon, _ in ranked[:5]:
            if category != 'life': 
                # Send image/media (if any)
                if sermon["media"]:
                    await update.message.reply_photo(photo=sermon["media"], caption="")

                # Send text message
                await update.message.reply_text(f"📖 {sermon['description']}", parse_mode="Markdown")

                # Send audio links
                for audio_url in sermon['audio_url']:
                    await update.message.reply_text(f"🎧 [Listen here]({audio_url})", parse_mode="Markdown")
            else:
                cover_image_url = sermon['media']
                title = sermon['description']
                link = sermon['audio_url'][0]
                
                # Send the cover image first
                await update.message.reply_photo(
                    photo=cover_image_url, 
                    caption=f"📖 {title} \n\n🔗 [Listen to message here]({link})",
                    parse_mode="Markdown"
                )

        # Disable category
        context.user_data['selected_category'] = ""
    else:
        keyboard = [
            [
                InlineKeyboardButton("🏅 Life of Victory",
                                     callback_data='life'),
                InlineKeyboardButton("💼 Business & Career",
                                     callback_data='business'),
            ],
            [
                InlineKeyboardButton("💖 Family & Relationships",
                                     callback_data='family'),
                InlineKeyboardButton("📘 Learning & Development",
                                     callback_data='learning'),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Please choose a category to narrow down your search for messages:", reply_markup=reply_markup
        )


def main() -> None:
    """Start the bot without using asyncio.run()"""
    # Create the Application with a non-async builder pattern
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command handler for /start
    application.add_handler(CommandHandler("start", start))

    # Callback handler for button clicks
    application.add_handler(CallbackQueryHandler(button))

    # Callback handler for messages
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the Bot with non-async method
    application.run_polling(allowed_updates=Update.ALL_TYPES)

    # Block until the user sends a signal
    application.idle()


if __name__ == '__main__':
    main()  # Non-async call to main

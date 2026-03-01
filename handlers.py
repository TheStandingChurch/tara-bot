from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

import search


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


async def handle_message(update: Update, context: CallbackContext) -> None:
    user_query = update.message.text
    category = context.user_data.get('selected_category', '')

    if not category:
        await update.message.reply_text(
            "Please choose a category to narrow down your search for messages:",
            reply_markup=category_keyboard()
        )
        return

    await update.message.reply_text("Hmm... Please wait a few seconds while I search for messages to help you.")

    results = await search.search(category, user_query)

    for msg in results:
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

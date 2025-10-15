from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from openai import OpenAI
import faiss
import numpy as np
import json
from docx import Document
import os

# === Config === #
EMBEDDING_MODEL = "text-embedding-ada-002"
LLM_MODEL = "gpt-4"
CHUNK_SIZE = 300  # words per chunk
VECTOR_FOLDER = "transform"  # folder containing your JSON vector files
BOT_NAME = "Pst Tara's A.I"
FACTS_FILE = "json/facts.json"

openai_client = OpenAI(api_key=OPENAI_API_KEY)

def load_facts():
    if not os.path.exists(FACTS_FILE):
        return []
    with open(FACTS_FILE, "r") as f:
        return json.load(f)


FACTS = load_facts()


# === Chunking Function === #
def chunk_and_embed_sermon(docx_path, sermon_title, output_path):
    """Reads a sermon docx, chunks it, embeds it, and saves to JSON."""
    doc = Document(docx_path)
    full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    words = full_text.split()
    chunks = [" ".join(words[i:i+CHUNK_SIZE])
              for i in range(0, len(words), CHUNK_SIZE)]

    sermon_data = []
    for chunk in chunks:
        emb = openai_client.embeddings.create(
            model=EMBEDDING_MODEL, input=chunk).data[0].embedding
        sermon_data.append({
            "chunk": chunk,
            "embedding": emb,
            "sermon_title": sermon_title
        })

    with open(output_path, "w") as f:
        json.dump(sermon_data, f)
    print(f"Saved {len(sermon_data)} chunks to {output_path}")
    return sermon_data

# === Load Multiple Sermon JSON Files === #
def load_all_sermons(folder_path=VECTOR_FOLDER):
    all_chunks = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            with open(os.path.join(folder_path, filename), "r") as f:
                data = json.load(f)
                all_chunks.extend(data)
    if not all_chunks:
        raise FileNotFoundError(f"No .json files found in {folder_path}")
    return all_chunks

# === Build FAISS Index ===
def build_faiss_index(sermon_db):
    d = len(sermon_db[0]['embedding'])
    index = faiss.IndexFlatL2(d)
    index.add(np.array([np.array(s['embedding']) for s in sermon_db]))
    return index

# === Query Retrieval === #
def embed_text(text):
    res = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return np.array(res.data[0].embedding)


def query_sermons(query, sermon_db, index, top_k=3):
    query_vec = embed_text(query)
    D, I = index.search(np.array([query_vec]), top_k)
    return [sermon_db[i] for i in I[0]]

# === Generate Response === #
def generate_response(query, context_chunks):
    context = "\n\n".join(
        [f"{i+1}. {c['chunk']} (From '{c['sermon_title']}')" for i, c in enumerate(context_chunks)])

    system_message = {
        "role": "system",
        "content": (
            f"You are {BOT_NAME}, a warm and friendly conversational assistant for our church. "
            f"Here are important facts you must always remember:\n" +
            "\n".join(FACTS)
        )
    }

    user_message = {
        "role": "user",
        "content": f"Question: {query}\n\nContext:\n{context}\n\nAnswer in a friendly, human tone:"
    }

    res = openai_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[system_message, user_message]
    )
    return res.choices[0].message.content

# === Telegram Handler === #
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text
    top_chunks = query_sermons(user_msg, SERMON_DB, INDEX)
    answer = generate_response(user_msg, top_chunks)
    await update.message.reply_text(answer)

# === Main ===
if __name__ == "__main__":
    # One-time run for a new sermon file:
    # chunk_and_embed_sermon("sermons/Financial Prosperity.docx",
    #                        "Financial Prosperity in the Family",
    #                        "transform/Financial Prosperity in the Family.json")

    SERMON_DB = load_all_sermons(VECTOR_FOLDER)
    INDEX = build_faiss_index(SERMON_DB)

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(
        filters.TEXT & (~filters.COMMAND), handle_message))
    print("Bot is running...")
    app.run_polling()

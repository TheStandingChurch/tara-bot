import json
from docx import Document  # from python-docx
from openai import OpenAI

# Config
EMBEDDING_MODEL = "text-embedding-ada-002"
CHUNK_SIZE = 300  # number of words per chunk

client = OpenAI(api_key=OPENAI_API_KEY)

DOCUMENT = "docx/Marital Victories Through Prayers.docx"

# Load the .docx file
doc = Document(DOCUMENT)
full_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])

# Tokenize into chunks by words
words = full_text.split()
chunks = [" ".join(words[i:i+CHUNK_SIZE]) for i in range(0, len(words), CHUNK_SIZE)]

# Create sermon chunks with embeddings
sermon_data = []
for chunk in chunks:
    embedding = client.embeddings.create(model=EMBEDDING_MODEL, input=chunk).data[0].embedding
    sermon_data.append({
        "chunk": chunk,
        "embedding": embedding,
        "sermon_title": DOCUMENT
    })

# Save to JSON
with open("transform/sermon_chunks_3.json", "w") as f:
    json.dump(sermon_data, f)

print(f"Saved {len(sermon_data)} chunks to sermon_chunks_3.json")
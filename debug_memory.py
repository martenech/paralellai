#!/usr/bin/env python3
import psycopg2
from sentence_transformers import SentenceTransformer
import numpy as np

# Connect to database
conn = psycopg2.connect(
    "postgresql://llm_user:llm_password@localhost:5432/llm_memory"
)
cur = conn.cursor()

# Get embeddings
model = SentenceTransformer("all-MiniLM-L6-v2")

# Test query
query = "Aká je najlepšia pizza v Bratislave?"
query_embedding = model.encode(query)

# Check if we have any embeddings
cur.execute("SELECT COUNT(*) FROM message_embeddings")
count = cur.fetchone()[0]
print(f"Total embeddings in database: {count}")

# Get sample similarities
cur.execute("""
    SELECT 
        me.chunk_text,
        1 - (me.embedding <=> %s::vector) as similarity,
        m.role
    FROM message_embeddings me
    JOIN messages m ON me.message_id = m.id
    ORDER BY similarity DESC
    LIMIT 10
""", (query_embedding.tolist(),))

print("\nTop 10 similar messages:")
for row in cur.fetchall():
    print(f"Similarity: {row[1]:.4f} | Role: {row[2]} | Text: {row[0][:50]}...")

cur.close()
conn.close()
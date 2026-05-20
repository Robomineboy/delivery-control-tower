import sys
import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from tickets import get_all_tickets

def ticket_to_text(ticket):
    return (
        f"ID: {ticket['id']} | "
        f"Title: {ticket['title']} | "
        f"Status: {ticket['status']} | "
        f"Priority: {ticket['priority']} | "
        f"Assignee: {ticket['assignee'] or 'Unassigned'} | "
        f"Type: {ticket['type']} | "
        f"Labels: {', '.join(ticket['labels'])} | "
        f"Blocked by: {', '.join(ticket['blocked_by']) if ticket['blocked_by'] else 'None'} | "
        f"Customer impacting: {ticket['customer_impacting']}"
    )

def build_index():
    print("Fetching tickets from Jira...")
    tickets = get_all_tickets()

    texts = [ticket_to_text(t) for t in tickets]

    print("Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print("Embedding tickets...")
    embeddings = model.encode(texts, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype=np.float32)

    print("Building FAISS index...")
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    faiss.write_index(index, "tickets.faiss")
    with open("tickets.pkl", "wb") as f:
        pickle.dump(tickets, f)

    print(f"Done. {index.ntotal} tickets indexed from live Jira board.")

if __name__ == "__main__":
    build_index()
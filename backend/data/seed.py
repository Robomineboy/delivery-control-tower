"""
data/seed.py

Builds the FAISS vector index from the synthetic ticket dataset.
Run once before starting the backend:
    python -m data.seed

Generates:
    data/tickets.faiss   — FAISS index
    data/tickets.pkl     — id-to-ticket mapping
"""

import os
import pickle
import sys

import numpy as np

from data.tickets import get_all_tickets
from core.schemas import Ticket


def _ticket_to_text(ticket: Ticket) -> str:
    """Convert a ticket to a searchable text blob."""
    parts = [
        f"ID: {ticket.id}",
        f"Project: {ticket.project}",
        f"Title: {ticket.title}",
        f"Status: {ticket.status}",
        f"Priority: {ticket.priority}",
        f"Assignee: {ticket.assignee or 'Unassigned'}",
        f"Labels: {', '.join(ticket.labels)}",
        f"Customer impacting: {ticket.customer_impacting}",
        f"SLA deadline: {ticket.sla_deadline or 'None'}",
        f"Blocked by: {', '.join(ticket.blocked_by) if ticket.blocked_by else 'None'}",
        f"Comments: {' | '.join(ticket.comments)}",
    ]
    return " | ".join(parts)


def build_index(output_dir: str = "data") -> None:
    try:
        import faiss
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("ERROR: faiss-cpu and sentence-transformers required.")
        print("Run: pip install faiss-cpu sentence-transformers")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print("Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    tickets = get_all_tickets()
    print(f"Encoding {len(tickets)} tickets...")

    texts = [_ticket_to_text(t) for t in tickets]
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype=np.float32)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)   # inner product = cosine similarity (normalized)
    index.add(embeddings)

    faiss_path = os.path.join(output_dir, "tickets.faiss")
    pkl_path = os.path.join(output_dir, "tickets.pkl")

    faiss.write_index(index, faiss_path)
    with open(pkl_path, "wb") as f:
        pickle.dump(tickets, f)

    print(f"\nIndex built successfully.")
    print(f"  FAISS index: {faiss_path}  ({index.ntotal} vectors, dim={dim})")
    print(f"  Ticket map:  {pkl_path}")
    print("\nRun `uvicorn api.main:app --reload` to start the backend.")


if __name__ == "__main__":
    build_index()

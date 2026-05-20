import faiss
import pickle
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

_DATA_DIR = Path(__file__).parent.parent / "data"

# Load index and tickets once at startup
index = faiss.read_index(str(_DATA_DIR / "tickets.faiss"))
with open(_DATA_DIR / "tickets.pkl", "rb") as f:
    tickets = pickle.load(f)

model = SentenceTransformer("all-MiniLM-L6-v2")

def retrieve(query, top_k=5):
    # Embed the query
    query_vec = model.encode([query], normalize_embeddings=True)
    query_vec = np.array(query_vec, dtype=np.float32)

    # Search FAISS
    scores, indices = index.search(query_vec, top_k)
    scores = scores[0]
    indices = indices[0]

    # Build results
    results = []
    for score, idx in zip(scores, indices):
        if idx < 0:
            continue
        ticket = tickets[idx]
        results.append({
            "ticket": ticket,
            "score": round(float(score), 3)
        })

    return results

def retrieve_filtered(query, top_k=5, filters=None):
    """
    filters: dict of field conditions e.g.
    {"assignee": None, "status": "Blocked"}
    """
    # Get more candidates than needed so filtering has room to work
    candidates = retrieve(query, top_k=len(tickets))

    if not filters:
        return candidates[:top_k]

    filtered = []
    for r in candidates:
        t = r["ticket"]
        match = all(t.get(k) == v for k, v in filters.items())
        if match:
            filtered.append(r)

    return filtered[:top_k]

if __name__ == "__main__":
    print("=== Test 1: unassigned high priority ===")
    results = retrieve_filtered("high priority", filters={"assignee": None})
    for r in results:
        t = r["ticket"]
        print(f"[{r['score']}] {t['id']} — {t['title']}")
        print(f"         Status: {t['status']} | Priority: {t['priority']} | Assignee: {t['assignee'] or 'Unassigned'}")
        print()

    print("=== Test 2: sensor firmware bugs ===")
    results = retrieve("sensor firmware bugs")
    for r in results:
        t = r["ticket"]
        print(f"[{r['score']}] {t['id']} — {t['title']}")
        print(f"         Status: {t['status']} | Priority: {t['priority']} | Assignee: {t['assignee'] or 'Unassigned'}")
        print()
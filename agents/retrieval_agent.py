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
    query_vec = model.encode([query], normalize_embeddings=True)
    query_vec = np.array(query_vec, dtype=np.float32)

    scores, indices = index.search(query_vec, top_k)
    scores = scores[0]
    indices = indices[0]

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
    # Get all candidates first
    candidates = retrieve(query, top_k=len(tickets))

    if not filters:
        return candidates[:top_k]

    filtered = []
    for r in candidates:
        t = r["ticket"]
        match = True
        for k, v in filters.items():
            if k == "assignee_contains":
                assignee = t.get("assignee") or ""
                if v.lower() not in assignee.lower():
                    match = False
            elif k == "assignee" and v is None:
                if t.get("assignee") is not None:
                    match = False
            else:
                if t.get(k) != v:
                    match = False
        if match:
            filtered.append(r)

    if not filtered:
        print(f"  [Retrieval] No results with filters {filters} — falling back to unfiltered")
        return candidates[:top_k]

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

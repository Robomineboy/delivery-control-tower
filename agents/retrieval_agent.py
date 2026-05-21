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

def ticket_to_text(t):
    return (
        f"{t['id']} {t['title']} {t['status']} {t['priority']} "
        f"{t['assignee'] or 'unassigned'} {t['type']} "
        f"{' '.join(t['labels'])} "
        f"{'blocked' if t.get('blocked_by') else ''}"
    )

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


def rebuild_index(new_tickets=None):
    global _tickets, _index
    
    try:
        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer
        
        if new_tickets:
            _tickets = new_tickets
        
        model = SentenceTransformer("all-MiniLM-L6-v2")
        texts = [ticket_to_text(t) for t in _tickets]
        embeddings = model.encode(texts, normalize_embeddings=True)
        embeddings = np.array(embeddings, dtype=np.float32)
        
        dim = embeddings.shape[1]
        _index = faiss.IndexFlatIP(dim)
        _index.add(embeddings)
        
        # Save updated index
        faiss.write_index(_index, "data/tickets.faiss")
        import pickle
        with open("data/tickets.pkl", "wb") as f:
            pickle.dump(_tickets, f)
            
        print(f"FAISS index rebuilt with {len(_tickets)} tickets")
        
    except Exception as e:
        print(f"rebuild_index failed: {e}")

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

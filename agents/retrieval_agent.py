from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from tickets import get_all_tickets

_tickets = get_all_tickets()

def _ticket_to_text(t):
    return (
        f"{t['title']} {t['status']} {t['priority']} "
        f"{t['assignee'] or 'unassigned'} {t['type']} "
        f"{' '.join(t['labels'])} "
        f"{'blocked' if t['blocked_by'] else ''}"
    )

_texts = [_ticket_to_text(t) for t in _tickets]
_vectorizer = TfidfVectorizer()
_matrix = _vectorizer.fit_transform(_texts)

def retrieve(query, top_k=5):
    query_vec = _vectorizer.transform([query])
    scores = cosine_similarity(query_vec, _matrix)[0]
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [
        {"ticket": _tickets[i], "score": round(float(scores[i]), 3)}
        for i in top_indices
        if scores[i] > 0
    ]

def retrieve_filtered(query, top_k=5, filters=None):
    candidates = retrieve(query, top_k=len(_tickets))
    
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
        print(f"  [Retrieval] No results with filters {filters} — falling back")
        return candidates[:top_k]
    
    return filtered[:top_k]
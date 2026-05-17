"""
agents/retrieval.py

Retrieval Agent — semantic search over the FAISS ticket index.
Returns ranked relevant tickets with a retrieval confidence score.

Phase 1: Keyword fallback (no FAISS dependency needed to run skeleton).
Phase 2: Load FAISS index + sentence-transformers for real semantic search.
"""

import logging

from core.config import get_settings
from core.schemas import (
    AgentStatus,
    PipelineState,
    RetrievalOutput,
    Ticket,
)
from agents.base import BaseAgent
from data.tickets import get_all_tickets

logger = logging.getLogger(__name__)
settings = get_settings()


class RetrievalAgent(BaseAgent):
    name = "retrieval"

    def __init__(self) -> None:
        self._faiss_ready = False
        self._index = None
        self._tickets: list[Ticket] = []
        self._model = None
        self._try_load_faiss()

    def _try_load_faiss(self) -> None:
        """Attempt to load FAISS index. Falls back to keyword search if unavailable."""
        try:
            import faiss
            import pickle
            import os
            from sentence_transformers import SentenceTransformer

            faiss_path = "data/tickets.faiss"
            pkl_path = "data/tickets.pkl"

            if os.path.exists(faiss_path) and os.path.exists(pkl_path):
                self._index = faiss.read_index(faiss_path)
                with open(pkl_path, "rb") as f:
                    self._tickets = pickle.load(f)
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
                self._faiss_ready = True
                logger.info("RetrievalAgent: FAISS index loaded ✓")
            else:
                logger.warning("RetrievalAgent: FAISS index not found — using keyword fallback. Run `python -m data.seed`")
        except ImportError:
            logger.warning("RetrievalAgent: faiss-cpu not installed — using keyword fallback")

    async def run(self, state: PipelineState) -> PipelineState:
        # Check retrieval confidence threshold from previous stage
        if state.intake is None:
            state.add_trace(self.name, AgentStatus.BLOCKED, notes="Intake output missing")
            state.blocked_reason = "Retrieval cannot run without intake output."
            return state

        project_filter = state.intake.project
        query = state.user_query

        try:
            if self._faiss_ready:
                tickets, confidence = self._semantic_search(query, project_filter, top_k=10)
            else:
                tickets, confidence = self._keyword_search(query, project_filter)

            # Gate: if retrieval confidence too low, block downstream planning
            if confidence < settings.min_retrieval_confidence:
                state.add_trace(
                    agent=self.name,
                    status=AgentStatus.BLOCKED,
                    confidence=confidence,
                    notes=f"Confidence {confidence:.2f} below threshold {settings.min_retrieval_confidence}. Planning agent cannot generate executable recommendations.",
                )
                state.blocked_reason = (
                    f"Retrieval confidence ({confidence:.2f}) below minimum threshold "
                    f"({settings.min_retrieval_confidence}). Cannot generate reliable recommendations."
                )
                return state

            state.retrieval = RetrievalOutput(
                tickets=tickets,
                query_used=query,
                confidence=confidence,
                source_count=len(tickets),
            )
            state.add_trace(
                agent=self.name,
                status=AgentStatus.SUCCESS,
                confidence=confidence,
                notes=f"Retrieved {len(tickets)} tickets",
            )

        except Exception as exc:
            state.add_trace(self.name, AgentStatus.FAILED, notes=str(exc))
            state.blocked_reason = f"Retrieval failed: {exc}"

        return state

    def _semantic_search(
        self, query: str, project: str, top_k: int = 10
    ) -> tuple[list[Ticket], float]:
        import numpy as np

        query_vec = self._model.encode([query], normalize_embeddings=True)
        query_vec = np.array(query_vec, dtype=np.float32)

        scores, indices = self._index.search(query_vec, top_k * 2)
        scores = scores[0]
        indices = indices[0]

        results = []
        for score, idx in zip(scores, indices):
            if idx < 0 or idx >= len(self._tickets):
                continue
            ticket = self._tickets[idx]
            if project != "all" and ticket.project.lower() != project.lower():
                continue
            results.append(ticket)
            if len(results) >= top_k:
                break

        avg_confidence = float(np.mean(scores[:len(results)])) if results else 0.0
        avg_confidence = min(max(avg_confidence, 0.0), 1.0)

        return results, round(avg_confidence, 3)

    def _keyword_search(
        self, query: str, project: str
    ) -> tuple[list[Ticket], float]:
        """Simple keyword fallback — used when FAISS index not available."""
        all_tickets = get_all_tickets()
        query_words = set(query.lower().split())

        scored = []
        for ticket in all_tickets:
            if project != "all" and ticket.project.lower() != project.lower():
                continue
            text = f"{ticket.title} {ticket.status} {ticket.priority} {' '.join(ticket.labels)} {' '.join(ticket.comments)}".lower()
            matches = sum(1 for w in query_words if w in text)
            scored.append((ticket, matches))

        scored.sort(key=lambda x: x[1], reverse=True)
        results = [t for t, _ in scored[:10] if _ > 0]

        # Keyword fallback always returns lower confidence
        confidence = 0.68 if results else 0.30

        return results, confidence

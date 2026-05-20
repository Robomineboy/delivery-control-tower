# Sprint 1 — Intake + Retrieval Pipeline Integration

**Stage:** First end-to-end integration of the intake agent and retrieval agent via `pipeline.py`  
**Status:** Working correctly

---

## What This Tests

Three natural-language queries are routed through the full pipeline:

1. Intake agent parses the query into structured intent, urgency, filters, and a cleaned search string
2. Retrieval agent embeds the cleaned query, searches the FAISS index, and applies the parsed filters

This run validates that both agents integrate cleanly and that the filter + semantic search combination returns sensible results.

---

## Results

### Query 1 — "What are the blocked tickets?"

```
Intent: blocker_analysis | Urgency: medium
Filters: {'status': 'Blocked'}
Search query: 'blocked tickets?'

Retrieved 1 tickets:
  [0.168] SS-15 — Synchronize left/right foot sensor streams
           Status: Blocked | Priority: Highest | Assignee: Robo Mineboy
```

**Observation:** Intake correctly maps this to `blocker_analysis` and injects a `status: Blocked` filter. Retrieval returns the one blocked ticket. Score of 0.168 is low but the filter is doing the heavy lifting here — semantic similarity alone would not reliably isolate this ticket.

---

### Query 2 — "Show me unassigned high priority issues"

```
Intent: ownership_gap | Urgency: high
Filters: {'assignee': None}
Search query: 'unassigned high priority issues'

Retrieved 1 tickets:
  [0.132] SS-10 — Validate gait report format with clinical team
           Status: To Do | Priority: Highest | Assignee: Unassigned
```

**Observation:** Intake correctly identifies this as an `ownership_gap` intent and sets `assignee: None` as the filter. Only one ticket matches, and it is the correct one. The semantic score (0.132) is again low — this query type is almost entirely filter-driven, which is expected.

---

### Query 3 — "What are the biggest risks in sensor firmware?"

```
Intent: risk_analysis | Urgency: medium
Filters: {}
Search query: 'biggest risks in sensor firmware?'

Retrieved 5 tickets:
  [0.408] SS-8  — Implement FSR calibration persistence         [High, To Do]
  [0.383] SS-11 — Fix IMU timestamp drift during extended sessions [Highest, To Do]
  [0.370] SS-14 — Optimize pressure interpolation rendering     [Medium, In Review]
  [0.341] SS-15 — Synchronize left/right foot sensor streams    [Highest, Blocked]
  [0.150] SS-12 — Improve gait cycle segmentation accuracy      [Medium, To Do]
```

**Observation:** No filters applied — the retrieval is driven entirely by semantic similarity. This is where the FAISS index earns its place: the top results are genuinely firmware-adjacent (FSR calibration, IMU drift, sensor stream sync), and SS-15 (the blocked ticket) surfaces naturally through semantic relevance rather than a filter. The score spread shows a meaningful signal drop-off after SS-14, with SS-12 being a weaker match.

---

## Summary

The intake-retrieval pipeline works. Filter-driven queries (blockers, ownership gaps) are precise and rely on structured metadata. Open-ended risk queries rely on semantic search and surface contextually relevant tickets. The pipeline correctly handles both modes. Next step: add a risk reasoning layer on top of the retrieved results.

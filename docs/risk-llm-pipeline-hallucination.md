# Risk Agent (LLM) — Pipeline Integration and Hallucination Failure

**Stage:** LLM risk agent integrated into the full `pipeline.py` flow  
**Status:** Partial failure — first query works, second query hallucinates severely

---

## What This Tests

The LLM risk agent is now called as a step inside the retrieval pipeline. The flow is:

1. Intake agent parses the query and extracts filters
2. Retrieval agent fetches the top-k semantically relevant tickets (filtered by parsed metadata)
3. LLM risk agent reasons over the *retrieved subset only*

This is a critical architectural difference from the standalone LLM risk agent, which had access to all 10 tickets. Here, the LLM only sees what retrieval returns — which may be very few tickets, or none.

---

## Results

### Query 1 — "What are the biggest risks this sprint?"

```
Intent:  risk_analysis | Urgency: medium
Filters: {}

Retrieved 5 tickets:
  [0.26]  SS-11 — Fix IMU timestamp drift during extended walking sessions [To Do]
  [0.207] SS-12 — Improve gait cycle segmentation accuracy [To Do]
  [0.206] SS-10 — Validate gait report format with clinical team [To Do]
  [0.165] SS-9  — Add patient session replay API [To Do]
  [0.162] SS-17 — Create MoCap visuals using IMU Drift [To Do]

Overall health: HIGH
Findings: 3

  [HIGH] Missing Assignee for Critical Task
    Confidence: 0.8
    Evidence:   ['SS-10']
    Detail:     Task SS-10 has a high priority and is critical for the project,
                but it is unassigned. This increases the risk of delays and missed deadlines.

  [MEDIUM] Insufficient Resource Allocation
    Confidence: 0.7
    Evidence:   ['SS-11', 'SS-17']
    Detail:     Both SS-11 and SS-17 are high-priority tasks assigned to Aryan Ghosh and
                Sidharth Jain. If these tasks are not completed on time, it may impact
                the project timeline.

  [LOW] Task Dependencies and Blocking Issues
    Confidence: 0.4
    Evidence:   ['SS-11', 'SS-12', 'SS-17']
    Detail:     There are no explicit blocking issues or dependencies between tasks.
                However, the lack of dependencies may indicate tasks are not properly
                sequenced, which could lead to inefficiencies.
```

**Observation:** The first query works correctly. 5 relevant tickets are retrieved, no filters are applied, and the LLM reasons over them coherently. SS-10 is correctly flagged as unassigned. The LOW finding (absence of dependencies interpreted as a risk) is a stretch, but it is grounded in the retrieved data.

---

### Query 2 — "Show me blocked and unassigned tickets"

```
Intent:  blocker_analysis | Urgency: medium
Filters: {'status': 'Blocked', 'assignee': None}

Retrieved 0 tickets

Overall health: CRITICAL
Findings: 4

  [CRITICAL] Delays in Critical Feature Implementation
    Confidence: 0.9
    Evidence:   ['SS-14', 'SS-13']
    Detail:     The implementation of the critical feature is delayed due to the complexity
                of the task and the team's limited experience with the new technology...

  [HIGH] Insufficient Testing and Quality Assurance
    Confidence: 0.85
    Evidence:   ['SS-12', 'SS-11']
    Detail:     The testing and quality assurance process may not be thorough enough due
                to the tight project timeline and the team's limited resources...

  [MEDIUM] Dependence on a Single Team Member
    Confidence: 0.7
    Evidence:   ['SS-10']
    Detail:     One team member is responsible for a significant portion of the project's
                codebase, which may lead to a single point of failure...

  [LOW] Scope Creep and Feature Bloat
    Confidence: 0.6
    Evidence:   ['SS-9']
    Detail:     The project scope is not clearly defined, and there is a risk of feature
                creep and bloat...
```

**This is a hallucination failure.**

---

## Analysis of the Failure

The retrieval step returned **0 tickets** — no ticket is both `Blocked` AND `Unassigned` at the same time. The LLM was passed an empty context.

Rather than reporting "no tickets found," the LLM generated 4 confident findings with specific ticket IDs, invented risk categories, and fabricated detail strings. None of the findings are grounded in anything the pipeline retrieved:

| Hallucinated finding | Why it is fabricated |
|---|---|
| "Delays in Critical Feature Implementation" citing SS-13, SS-14 | SS-13 and SS-14 were not in the retrieved set — they were not retrieved at all |
| "team's limited experience with the new technology" | No ticket in the dataset mentions team experience — this is invented |
| "Scope Creep and Feature Bloat" citing SS-9 | SS-9 is a session replay API ticket, not related to scope definition |
| Overall health CRITICAL | Based on zero retrieved tickets |

The LLM appears to have drawn on knowledge from prior queries in the session (or its own priors about software projects) rather than the empty context it was given.

---

## Root Cause

There is no validation step between retrieval and LLM reasoning. When retrieval returns an empty set, the pipeline still invokes the LLM and the LLM fills the vacuum with plausible-sounding but entirely fabricated output. The system has no way to distinguish a grounded finding from an invented one.

---

## Required Fix: Critic Agent

A critic (or guard) agent must sit between the LLM risk agent and the final output. Its responsibilities:

1. **Empty context check** — if 0 tickets were retrieved, return a null result immediately without calling the LLM
2. **Evidence grounding check** — verify that every ticket ID cited in a finding actually appears in the retrieved set; discard findings that cite tickets not in context
3. **Hallucination detection** — flag or suppress any detail string that references facts not present in the ticket metadata (e.g., mentions of team experience, technology familiarity, scope definitions)

Until this layer exists, the pipeline output cannot be trusted for queries that return few or zero tickets.

---

## Summary

Integrating the LLM risk agent into the pipeline exposes a critical failure mode: when retrieval returns no results, the LLM hallucinates authoritative-sounding findings from nothing. The first query (broad, no filters, 5 results) works well. The second query (two filters, 0 results) fails completely. A critic agent that validates LLM outputs against the retrieved context is the required next architectural step.

# Risk Agent — LLM Reasoning Implementation

**Stage:** Risk agent replaced from rule-based evaluation to LLM reasoning over the full ticket set  
**Status:** Qualitatively stronger — shows genuine inference and cross-ticket correlation

---

## What This Tests

The risk agent is rewritten to pass all 10 Jira tickets to an LLM and ask it to reason about project risk holistically. No hardcoded rules are applied. The LLM has access to ticket ID, title, status, priority, assignee, and due date, and is asked to identify risks, estimate confidence, and cite specific tickets as evidence.

---

## Results

```
Overall project health: HIGH
Total findings: 4

[HIGH] Delays in IMU Quaternion sandbox implementation
  Confidence: 0.8
  Evidence:   ['SS-16']
  Detail:     The IMU Quaternion sandbox implementation is due on 2026-05-15, but it is currently
              in the 'To Do' status. This indicates a potential delay in meeting the deadline,
              which could impact the project timeline.

[MEDIUM] Blockage in feature development due to missing dependencies
  Confidence: 0.7
  Evidence:   ['SS-15']
  Detail:     The 'Synchronize left/right foot sensor streams' feature is currently blocked,
              which could prevent the development of dependent features. This might lead to a
              ripple effect and delays in the project timeline.

[HIGH] Unassigned task with high priority
  Confidence: 0.9
  Evidence:   ['SS-10']
  Detail:     The 'Validate gait report format with clinical team' task has a high priority but
              is unassigned. This increases the risk of delays or missed deadlines, as no one
              is responsible for completing the task.

[MEDIUM] Multiple high-priority tasks assigned to the same person
  Confidence: 0.6
  Evidence:   ['SS-11', 'SS-9']
  Detail:     Aryan Ghosh is assigned to multiple high-priority tasks, including 'Fix IMU
              timestamp drift during extended walking sessions' and 'Add patient session replay
              API'. This could lead to overcommitment and potential delays.
```

---

## Comparison with Rules-Based Output

| Dimension | Rules-Based | LLM Reasoning |
|---|---|---|
| SS-16 (overdue) | Flagged as SLA violation, confidence 0.99 | Flagged as delay risk — explains *why* it matters to the timeline |
| SS-15 (blocked) | Flagged as blocker, confidence 0.95 | Flagged at MEDIUM — notes ripple effect on dependent features |
| SS-10 (unassigned) | Flagged as ownership gap, confidence 0.98 | Flagged at HIGH — articulates the accountability risk |
| SS-11 + SS-9 | Not connected — flagged separately | **Cross-ticket finding:** both assigned to Aryan Ghosh, flagged as overcommitment risk |

---

## Key Observations

**Cross-ticket correlation appears.** The overcommitment finding (SS-11 + SS-9) does not exist in the rules-based output at all. The LLM identified that a single person holds multiple highest-priority tickets and inferred a systemic risk. This is genuine inference — it requires holding two tickets in context simultaneously and reasoning about their relationship.

**Severity and confidence are calibrated differently.** The rules-based agent assigned SS-15 (blocked) a `HIGH` with 0.95 confidence. The LLM rates it `MEDIUM` with 0.7 — a blocked ticket is less urgent than an overdue one or an unowned critical task. This is a more nuanced prioritisation that reflects relative impact.

**Detail strings explain reasoning, not just facts.** The rules-based agent says "1 ticket is blocked: SS-15." The LLM explains that a blocked feature may prevent dependent features from starting, creating a ripple effect. This framing is more useful to a project manager.

**The output is not deterministic.** Unlike the rules-based agent, the LLM's findings can vary across runs. The overall health rating, severity levels, and the specific risks surfaced are all subject to model temperature and prompt variation. This is a trade-off: more nuanced reasoning at the cost of repeatability.

---

## Summary

Switching to LLM reasoning produces a qualitatively richer risk report. The agent can identify patterns that no rule was written to catch, and it frames risks in terms of impact rather than just state. The overcommitment finding is a clear example of inference that a rules engine cannot produce without being explicitly programmed for it. The next step is integrating this agent into the full retrieval pipeline — though that introduces a new problem: the LLM must now reason over a *filtered subset* of tickets rather than the full board.

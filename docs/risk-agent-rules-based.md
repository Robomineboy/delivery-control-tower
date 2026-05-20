# Risk Agent — Rules-Based Implementation

**Stage:** First risk agent implementation, using deterministic rule evaluation over Jira tickets  
**Status:** Functional, but brittle — see observations

---

## What This Tests

A rule-based risk agent loads all tickets directly from Jira and evaluates them against a fixed set of rules:

- Are any tickets blocked?
- Are any tickets past their due date?
- Are high-priority tickets unassigned?
- Are critical bugs still open?

Each rule fires independently and returns a finding with a severity, confidence score, evidence list, and detail string.

---

## Results

```
Overall project health: CRITICAL
Total findings: 4

[HIGH] Active blockers detected
  Confidence: 0.95
  Evidence:   ['SS-15']
  Detail:     1 ticket(s) are blocked: SS-15 (Synchronize left/right foot sensor streams)

[CRITICAL] SLA violations — tickets past due date
  Confidence: 0.99
  Evidence:   ['SS-16']
  Detail:     1 ticket(s) past their due date: SS-16 due 2026-05-15

[HIGH] High priority tickets with no owner
  Confidence: 0.98
  Evidence:   ['SS-10']
  Detail:     1 high priority ticket(s) unassigned: SS-10 (Validate gait report format with clinical team)

[CRITICAL] Critical bugs unresolved
  Confidence: 0.96
  Evidence:   ['SS-11']
  Detail:     1 critical bug(s) open: SS-11 (Fix IMU timestamp drift during extended walking sessions)
```

---

## Observations

**The findings are factually correct.** Every finding maps directly to a real ticket and a real condition — this is expected, since the rules were written with knowledge of the dataset.

**The confidence scores are artificially high.** Values like 0.99, 0.98, and 0.96 do not reflect uncertainty in the analysis — they are hardcoded constants attached to each rule. A blocked ticket is "95% confident" not because of any reasoning, but because the rule author assigned that number. These scores carry no real information.

**The rule set encodes bias toward the known data.** A category like "Critical bugs unresolved" presupposes that SS-11 is a critical bug — this knowledge is baked into the rule, not inferred. A new ticket type or a different sprint structure would require the rules to be manually updated.

**There is no cross-ticket reasoning.** Each finding is isolated. The agent cannot observe that Aryan Ghosh is assigned to both the overdue IMU work (SS-16 adjacent) and the blocked sensor sync, or connect patterns across tickets. Risk is assessed ticket-by-ticket, not holistically.

**The output pattern is completely predictable.** Every run against this dataset will produce identical findings in identical order. There is no reasoning — only pattern matching.

---

## Summary

The rules-based risk agent serves as a useful correctness baseline: it tells you *what* is objectively wrong with the board at a metadata level. But it cannot tell you *why* it matters or how risks compound. It is essentially an alert system, not an analyst. Switching to an LLM reasoning approach is the natural next step.

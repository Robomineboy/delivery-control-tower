Query: 'What are the blocked tickets?'

Intent: blocker_analysis | Urgency: medium
Filters: {'status': 'Blocked'}
Search query: 'blocked tickets?'

Retrieved 1 tickets:
  [0.168] SS-15 — Synchronize left/right foot sensor streams
           Status: Blocked | Priority: Highest | Assignee: Robo Mineboy

============================================================

Query: 'Show me unassigned high priority issues'

Intent: ownership_gap | Urgency: high
Filters: {'assignee': None}
Search query: 'unassigned high priority issues'

Retrieved 1 tickets:
  [0.132] SS-10 — Validate gait report format with clinical team
           Status: To Do | Priority: Highest | Assignee: Unassigned

============================================================

Query: 'What are the biggest risks in sensor firmware?'

Intent: risk_analysis | Urgency: medium
Filters: {}
Search query: 'biggest risks in sensor firmware?'

Retrieved 5 tickets:
  [0.408] SS-8 — Implement FSR calibration persistence
           Status: To Do | Priority: High | Assignee: Robo Mineboy
  [0.383] SS-11 — Fix IMU timestamp drift during extended walking sessions
           Status: To Do | Priority: Highest | Assignee: Aryan Ghosh
  [0.37] SS-14 — Optimize pressure interpolation rendering
           Status: In Review | Priority: Medium | Assignee: Sidharth Jain
  [0.341] SS-15 — Synchronize left/right foot sensor streams
           Status: Blocked | Priority: Highest | Assignee: Robo Mineboy
  [0.15] SS-12 — Improve gait cycle segmentation accuracy
           Status: To Do | Priority: Medium | Assignee: Sidharth Jain

============================================================
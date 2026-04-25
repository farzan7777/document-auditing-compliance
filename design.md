# OpenEnv Compliance UI Design Spec

## Product Intent

OpenEnv Compliance is an AI compliance operations interface for evaluating document-auditing agents in realistic enterprise workflows. The UI must prioritize trust, analytical clarity, and decision support over decorative presentation.

## Primary Users

- Compliance officer validating AI findings
- ML engineer evaluating agent behavior and failure modes
- Product/research lead reviewing benchmark readiness

## UX Priorities

- Make audit reliability legible within 10 seconds
- Expose why an action was rewarded or penalized
- Distinguish auditor claims from verifier judgments at all times
- Highlight progression across curriculum levels and model confidence

## Information Model

### A. Session Control

- Task selector (Task 1/2/3)
- Seed input
- Buttons: Reset, Step, Submit, Grade
- Current session ID and run state

### B. Document Review Workspace

- Full document text panel with section anchors
- Findings panel split into:
  - Auditor findings
  - Verifier decisions (approve/reject)
- Severity filter chips: critical, major, minor

### C. Decision Quality Panel

- Metrics:
  - Current reward
  - Cumulative reward
  - Precision proxy (false positives)
  - Coverage proxy (missed required fields/clauses)
- Reward reason feed (chronological, newest first)

### D. Multi-Agent Oversight

- Auditor score
- Verifier score
- Combined weighted score
- Hallucinations caught
- Decision confidence average

### E. Curriculum Intelligence

- Current level and role title
- Rolling average with threshold markers
- Promotion/demotion logic explanation
- Level history timeline

### F. API and Debug Surface

- Endpoint quick actions (reset/step/state/grader/multi)
- JSON request composer
- JSON response viewer with schema-aware formatting

## Interaction Patterns

- One-click run path: select task -> reset -> step loop -> grade
- Progressive disclosure: basic metrics first, technical breakdown on expand
- Persistent context rail: task, level, steps, score always visible
- Inline status feedback: success, warning, error, fallback mode

## Visual Behavior Rules

- Keep contrast high for dense operational reading
- Use color semantically only:
  - cyan = system/info
  - green = valid/approved
  - yellow = caution/incomplete
  - red = violations/errors
- Use motion to indicate data change, not to decorate:
  - score updates
  - decision state transitions
  - curriculum level change

## Accessibility and Trust

- WCAG-compliant contrast for all KPI/readout text
- Reduced motion mode with no critical meaning loss
- Keyboard support for all run controls
- Avoid ambiguous icons without labels

## Output Targets

- Desktop-first command center (1440px baseline)
- Tablet adaptation for read-only monitoring
- Mobile fallback for status and scoring only

## Success Criteria

- User can identify top risk and final quality score quickly
- User can explain why the score was obtained
- User can compare auditor/verifier behavior without confusion
- User can verify whether the model is improving over episodes

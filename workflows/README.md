# Orchestration workflows

These are the AI orchestration scripts used to build this project. Each runs many subagents
concurrently under a deterministic control flow, with structured (schema-validated) output and
adversarial verification stages. They are parameterized via the workflow runner's `args`.

| Script | Purpose | Shape |
|---|---|---|
| `scope-map.js` | Map a provided repo/dataset into a structured summary | parallel readers |
| `implement-fanout.js` | Build independent tasks concurrently, verify each | pipeline: implement → verify |
| `find-verify.js` | Hunt defects, then adversarially confirm each | pipeline: find → verify |
| `judge-panel.js` | Explore N approaches, score, synthesize a winner | propose → judge → synthesize |

## Principles encoded here

- **Pipeline by default.** Work streams through stages without a barrier, so a later stage for
  one item starts as soon as that item is ready, instead of waiting for the whole batch.
- **Structured output.** Every agent returns typed data, so merging results is code, not prose
  parsing.
- **Adversarial verification.** Nothing is accepted on an agent's say-so. An independent agent
  tries to refute each result, and a real run confirms it.
- **Failure isolation.** A pipeline isolates a dead agent to its own item; the rest complete,
  and the failed branch can be resumed without re-running the successful work.

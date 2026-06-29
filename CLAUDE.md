# CLAUDE.md — How this project is built

This repository was built with AI orchestration as a first-class method. This file is the
operating directive for the AI agents working in it: it defines the engineering discipline,
not just the task. It is part of the deliverable, alongside `workflows/` and
`docs/HOW-THIS-WAS-BUILT.md`.

## The method

Build the best possible working solution by **orchestrating parallel AI agents under explicit
verification gates**, rather than coding linearly or trusting model output blindly. The
discipline below is what makes that produce correct, owned code instead of plausible noise.

## Non-negotiables

1. **Scope before fanning out.** Restate the goal in one sentence. Discover the work-list
   directly (files, data shape, independent tasks) before delegating. Don't spawn agents to
   "understand" before the shape of the work is known.
2. **Fan out along independent seams.** Use the `Workflow` scripts in `workflows/`. Default to
   `pipeline` (stream, no barrier); use a `parallel` barrier only when a stage genuinely needs
   all prior results at once. Decompose so agents own distinct files and don't collide.
3. **Every fan-out agent returns a schema.** Integration is code over structured output, not
   reading prose summaries. This is what keeps orchestration organized at scale.
4. **Always verify adversarially.** Green linters and passing tests are not proof of
   correctness. Each finding or implementation is real only after an independent agent tries to
   refute it and a real run confirms it. Trust `git diff` plus execution over any self-report.
5. **Own and explain every line shipped.** The author reads the core files and can defend each
   design choice. Code that can't be explained doesn't ship.
6. **Vertical slice first.** A small end-to-end path that runs beats a half-built grand design.
   Get one path working, then expand outward.
7. **Honest attribution.** `Co-Authored-By` lines stay. The orchestration approach is documented
   openly in `docs/HOW-THIS-WAS-BUILT.md`.

## Orchestration toolkit (`workflows/`)

- `scope-map.js` — parallel readers map a provided repo/dataset into a structured map.
- `implement-fanout.js` — implement independent tasks in parallel, adversarially verify each.
- `find-verify.js` — find issues across the code, adversarially verify each before acting.
- `judge-panel.js` — generate N approaches, score independently, synthesize a winner.

Each is parameterized via the workflow runner's `args`. See `workflows/README.md`.

## Layout

```
src/        application code
tests/      tests
workflows/  the AI orchestration scripts used to build this
docs/       HOW-THIS-WAS-BUILT.md — the build narrative
```

<!-- PUBLIC. Fill the <...> at the end of the build. This is the orchestration narrative. -->

# How this was built

This solution was built in a fixed timebox by orchestrating parallel AI agents under explicit
verification gates. The goal of this document is to show the *method and the judgment*, not to
claim the code wrote itself. Every design decision and every shipped line was reviewed and is
explainable.

## The orchestration approach

1. **Scope.** The problem was restated in one sentence and the work-list (data shape,
   independent tasks) was mapped directly before any delegation.
2. **Decompose into independent seams.** The build was split into tasks that own distinct
   modules so they can be implemented concurrently without collision.
3. **Fan out with structured output.** Each task was implemented by a dedicated agent that
   returns a typed result, so integration is code over data rather than reading prose.
4. **Adversarial verification.** Every implementation was checked by an independent agent
   prompted to refute it, and confirmed with a real run. Passing linters alone was never
   treated as proof of correctness.
5. **Integrate and harden.** Results were merged on a always-runnable main, then a final
   find-and-verify pass hunted for remaining defects.

The scripts that drove this are in [`workflows/`](../workflows): `scope-map`, `implement-fanout`,
`find-verify`, and `judge-panel`. The operating discipline is in [`CLAUDE.md`](../CLAUDE.md).

## What I actually did for this problem

<Fill at go-time: the specific decomposition. e.g.
- Mapped the dataset with scope-map (N readers) -> found <shape>.
- Chose architecture X over Y because <reason>.
- Fanned out M implementation tasks: <list>.
- Verification caught <real issue> that linting passed.
- Integrated and ran end-to-end: <result>.>

## Where I used judgment over automation

<Fill: the calls a model wouldn't make on its own — the architecture choice, what to cut for
time, a verification finding I overrode or accepted, the trade-offs below.>

## Trade-offs made for the timebox

- <deferred>
- <known limitation>

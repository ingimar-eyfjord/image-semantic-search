// implement-fanout.js — build N independent tasks in parallel, adversarially verify each.
// The core build engine: most of the solution is produced through this pattern.
//
// args: {
//   tasks: [{ key, description, files?: string[], acceptance: string }],
//   isolate?: boolean   // true -> each impl agent runs in its own git worktree (use when
//                       // tasks mutate overlapping files). Default false (tasks own distinct files).
// }
//
// Returns: { tasks: [{ key, impl, review, passed }], passedCount, failed: [...] }

export const meta = {
  name: 'implement-fanout',
  description: 'Implement independent tasks in parallel, adversarially verify each',
  phases: [{ title: 'Implement' }, { title: 'Verify' }],
}

const IMPL_SCHEMA = {
  type: 'object',
  required: ['key', 'summary', 'filesChanged', 'howToRun'],
  properties: {
    key: { type: 'string' },
    summary: { type: 'string', description: 'what was built, one paragraph' },
    filesChanged: { type: 'array', items: { type: 'string' } },
    howToRun: { type: 'string', description: 'exact command to exercise this piece' },
    assumptions: { type: 'array', items: { type: 'string' } },
  },
}

const REVIEW_SCHEMA = {
  type: 'object',
  required: ['key', 'meetsAcceptance', 'ranIt', 'issues'],
  properties: {
    key: { type: 'string' },
    meetsAcceptance: { type: 'boolean', description: 'true only if acceptance criteria are genuinely met' },
    ranIt: { type: 'boolean', description: 'did you actually execute the code / tests?' },
    issues: { type: 'array', items: { type: 'string' }, description: 'real defects; empty if clean' },
  },
}

const tasks = (args && args.tasks) || []
const isolate = !!(args && args.isolate)
if (!tasks.length) throw new Error('implement-fanout: pass args.tasks = [{key, description, acceptance}]')

log(`Implementing ${tasks.length} tasks${isolate ? ' (worktree-isolated)' : ''}, verifying each`)

const results = await pipeline(
  tasks,
  (t) =>
    agent(
      `Implement this task. Write real, runnable Python (or the project's language). Match existing
project conventions. Keep it minimal and correct; do not gold-plate.

Task "${t.key}": ${t.description}
${t.files ? `Likely files: ${t.files.join(', ')}` : ''}
Acceptance: ${t.acceptance}

After implementing, actually run it to confirm it works. Return the impl report for "${t.key}".`,
      { schema: IMPL_SCHEMA, label: `impl:${t.key}`, phase: 'Implement', ...(isolate ? { isolation: 'worktree' } : {}) }
    ),
  (impl, t) => {
    if (!impl) return { key: t.key, impl: null, review: null, passed: false }
    return agent(
      `Adversarially verify the implementation of task "${t.key}".
Acceptance criteria: ${t.acceptance}
Implementer's claim: ${impl.summary}
Run it yourself ("${impl.howToRun}"). Read the changed files: ${(impl.filesChanged || []).join(', ')}.
Flag meetsAcceptance=false if it is missing, incomplete, broken at runtime, or only superficially done.
Set ranIt=true only if you actually executed it. List concrete issues.`,
      { schema: REVIEW_SCHEMA, label: `verify:${t.key}`, phase: 'Verify' }
    ).then((review) => ({ key: t.key, impl, review, passed: !!(review && review.meetsAcceptance) }))
  }
)

const clean = results.filter(Boolean)
const passedCount = clean.filter((r) => r.passed).length
const failed = clean.filter((r) => !r.passed).map((r) => ({ key: r.key, issues: r.review?.issues || ['no review'] }))
log(`${passedCount}/${clean.length} tasks passed verification`)
return { tasks: clean, passedCount, failed }

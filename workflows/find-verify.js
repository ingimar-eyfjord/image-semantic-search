// find-verify.js — find issues across targets, adversarially verify each finding.
// Use to harden the solution (bug hunt / gap analysis) before shipping.
//
// args: {
//   targets: [{ key, path }],          // one finder per target
//   dimension?: string                 // what to look for; default "bugs and correctness gaps"
// }
//
// Returns: { confirmed: [...], refutedCount }

export const meta = {
  name: 'find-verify',
  description: 'Find issues across targets, adversarially verify each before reporting',
  phases: [{ title: 'Find' }, { title: 'Verify' }],
}

const FIND_SCHEMA = {
  type: 'object',
  required: ['target', 'findings'],
  properties: {
    target: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'title', 'severity', 'location', 'description', 'fix'],
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          location: { type: 'string' },
          description: { type: 'string' },
          fix: { type: 'string' },
        },
      },
    },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['target', 'verdicts'],
  properties: {
    target: { type: 'string' },
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'isReal', 'reasoning'],
        properties: {
          id: { type: 'string' },
          isReal: { type: 'boolean', description: 'true only if a genuine, not-already-handled defect' },
          reasoning: { type: 'string' },
        },
      },
    },
  },
}

const targets = (args && args.targets) || []
const dimension = (args && args.dimension) || 'bugs and correctness gaps'
if (!targets.length) throw new Error('find-verify: pass args.targets = [{key, path}]')

log(`Finding ${dimension} across ${targets.length} targets, verifying each finding`)

const results = await pipeline(
  targets,
  (t) =>
    agent(
      `Read ${t.path} and find ONLY real instances of: ${dimension}.
Cite locations. Do not report style nits or hypotheticals. Return findings for "${t.key}".`,
      { schema: FIND_SCHEMA, label: `find:${t.key}`, phase: 'Find' }
    ),
  (found, t) => {
    if (!found || !found.findings || !found.findings.length) return { target: t.key, findings: [], verdicts: [] }
    return agent(
      `Adversarially verify these findings against ${t.path}. Re-read the file. A finding is real
only if it is a genuine, not-already-handled defect and not a false positive. Default to false when uncertain.

${found.findings.map((f) => `- [${f.id}] (${f.severity}) ${f.title} @ ${f.location}: ${f.description}`).join('\n')}

Return a verdict for every id, for "${t.key}".`,
      { schema: VERDICT_SCHEMA, label: `verify:${t.key}`, phase: 'Verify' }
    ).then((v) => ({ target: t.key, findings: found.findings, verdicts: v?.verdicts || [] }))
  }
)

const confirmed = []
let refutedCount = 0
for (const r of results.filter(Boolean)) {
  const real = new Set((r.verdicts || []).filter((v) => v.isReal).map((v) => v.id))
  for (const f of r.findings || []) {
    if (real.has(f.id)) confirmed.push({ target: r.target, ...f })
    else refutedCount++
  }
}
log(`${confirmed.length} confirmed, ${refutedCount} refuted`)
return { confirmed, refutedCount }

// judge-panel.js — generate N independent approaches, score with judges, synthesize a winner.
// Use ONLY when the architecture is genuinely non-obvious. If the approach is
// clear, skip this and just decide; don't spend time deliberating the obvious.
//
// args: {
//   question: string,        // the design/architecture decision
//   context?: string,        // constraints, data shape, must-haves
//   n?: number               // number of approaches to generate (default 3)
// }
//
// Returns: { winner, scores, synthesis }

export const meta = {
  name: 'judge-panel',
  description: 'Generate N approaches, score independently, synthesize the best',
  phases: [{ title: 'Propose' }, { title: 'Judge' }, { title: 'Synthesize' }],
}

const APPROACH_SCHEMA = {
  type: 'object',
  required: ['name', 'sketch', 'tradeoffs', 'firstSteps'],
  properties: {
    name: { type: 'string' },
    sketch: { type: 'string', description: 'the architecture in a few sentences' },
    tradeoffs: { type: 'string' },
    firstSteps: { type: 'array', items: { type: 'string' }, description: 'first 3 concrete build steps' },
  },
}

const SCORE_SCHEMA = {
  type: 'object',
  required: ['scores'],
  properties: {
    scores: {
      type: 'array',
      items: {
        type: 'object',
        required: ['approach', 'fitsTimebox', 'correctnessRisk', 'total', 'note'],
        properties: {
          approach: { type: 'string' },
          fitsTimebox: { type: 'integer', description: '1-5, can it ship in the remaining time' },
          correctnessRisk: { type: 'integer', description: '1-5, 5 = lowest risk' },
          total: { type: 'integer', description: 'overall 1-10' },
          note: { type: 'string' },
        },
      },
    },
  },
}

const question = args && args.question
const context = (args && args.context) || ''
const n = (args && args.n) || 3
if (!question) throw new Error('judge-panel: pass args.question')

log(`Generating ${n} approaches for: ${question}`)

const angles = ['ship-fastest / simplest thing that works', 'most-correct / robust', 'most-impressive / best showcase']
const approaches = (await parallel(
  Array.from({ length: n }, (_, i) => () =>
    agent(
      `Propose ONE architecture for this challenge decision, biased toward the angle: "${angles[i % angles.length]}".
Question: ${question}
${context ? `Context: ${context}` : ''}
Be concrete and buildable in a 90-minute timebox. Return the approach.`,
      { schema: APPROACH_SCHEMA, label: `propose:${i + 1}`, phase: 'Propose' }
    )
  )
)).filter(Boolean)

const judging = await parallel(
  ['timebox-realist', 'correctness-skeptic'].map((lens) => () =>
    agent(
      `As a ${lens}, score these ${approaches.length} approaches for the challenge decision "${question}".
${context ? `Context: ${context}` : ''}

${approaches.map((a) => `### ${a.name}\n${a.sketch}\nTradeoffs: ${a.tradeoffs}`).join('\n\n')}

Score each on fitsTimebox (1-5), correctnessRisk (1-5, 5=lowest risk), and total (1-10).`,
      { schema: SCORE_SCHEMA, label: `judge:${lens}`, phase: 'Judge' }
    )
  )
)

const totals = {}
for (const j of judging.filter(Boolean)) {
  for (const s of j.scores || []) totals[s.approach] = (totals[s.approach] || 0) + s.total
}
const winnerName = Object.keys(totals).sort((a, b) => totals[b] - totals[a])[0] || (approaches[0] && approaches[0].name)

const synthesis = await agent(
  `Synthesize the final architecture to build now. The judges favored "${winnerName}".
Approaches considered:
${approaches.map((a) => `### ${a.name}\n${a.sketch}\nFirst steps: ${(a.firstSteps || []).join('; ')}`).join('\n\n')}

Recommend the concrete plan: the winning approach, plus any better ideas worth grafting from the
others. Give the first 3 build steps. Keep it to what fits the timebox.`,
  { label: 'synthesize', phase: 'Synthesize' }
)

return { winner: winnerName, scores: totals, synthesis }

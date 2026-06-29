// scope-map.js — parallel readers map a provided repo/dataset into a structured map.
// Use when handed starter code or a dataset that needs to be understood fast.
//
// args: { targets: [{ area: string, path: string, hint?: string }] }
//   each target is read by one agent. Pass actual JSON, not a string.
//
// Returns: { map: [{ area, purpose, keyFiles, entryPoints, dataShape, gotchas }] }

export const meta = {
  name: 'scope-map',
  description: 'Fan out parallel readers to map a provided repo/dataset into a structured map',
  phases: [{ title: 'Map' }],
}

const MAP_SCHEMA = {
  type: 'object',
  required: ['area', 'purpose', 'keyFiles', 'entryPoints', 'dataShape', 'gotchas'],
  properties: {
    area: { type: 'string' },
    purpose: { type: 'string', description: 'what this area is for, one sentence' },
    keyFiles: { type: 'array', items: { type: 'string' } },
    entryPoints: { type: 'array', items: { type: 'string' }, description: 'where execution/data starts' },
    dataShape: { type: 'string', description: 'schema/columns/format if data; empty if code' },
    gotchas: { type: 'array', items: { type: 'string' }, description: 'risks, surprises, missing pieces' },
  },
}

const targets = (args && args.targets) || []
if (!targets.length) throw new Error('scope-map: pass args.targets = [{area, path, hint?}]')

log(`Mapping ${targets.length} targets in parallel`)

const map = await parallel(
  targets.map((t) => () =>
    agent(
      `Read and map the target at ${t.path} (area: "${t.area}"${t.hint ? `; hint: ${t.hint}` : ''}).
Report ONLY what is actually there: purpose, the key files, entry points (where execution or data flow begins), the data shape/schema if it is data, and any gotchas (risks, surprises, missing pieces, ambiguity). Be concrete and terse. Do not propose solutions.`,
      { schema: MAP_SCHEMA, label: `map:${t.area}`, phase: 'Map' }
    )
  )
)

return { map: map.filter(Boolean) }

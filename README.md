<!-- PUBLIC. This is the submission README. Fill the <...> at go-time; keep it tight. -->

# <Project name>

<One-sentence description of what this solves.>

## Problem

<2-3 sentences restating the challenge in your own words.>

## Approach

<The architecture in a short paragraph. What it does, the key design choice, and why.>

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # + requirements-ai.txt if used
# <the actual run command>
```

## Project layout

```
src/      # <what's here>
tests/    # <what's here>
```

## Tests

```bash
pytest
```

## How this was built

<Short, honest note: built in a 90-minute timebox by orchestrating parallel AI agents
(scope -> fan-out implementation -> adversarial verification -> integration). Trade-offs
made for time are listed below.>

## Trade-offs / what I'd do next

- <deferred item>
- <known limitation>

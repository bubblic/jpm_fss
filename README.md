# KG Encoding Spike

One-day spike for the financial statement simulator: prove that a
knowledge-graph encoding works mechanically on one real filing (Apple's
latest 10-K balance sheet). See CLAUDE.md for full context and PROMPT.md for
the task given to Claude Code.

## Setup (once)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# SEC requires an identifying User-Agent on every request.
# EDIT THIS to your real name and email before running anything:
export SEC_USER_AGENT="Jaebum Chung your.email@example.com"
```

## Run with Claude Code

From this directory:

```bash
claude
```

then paste the contents of PROMPT.md, or non-interactively:

```bash
claude "$(cat PROMPT.md)"
```

Claude Code will read CLAUDE.md automatically, write a plan to `out/plan.md`,
implement `src/spike/*`, and produce:

- `out/report.md`   – the spike findings (the artifact to show the director)
- `out/overlay.json` – z (leaf values) + m (presentation map) for the filing
- `out/graph.graphml` – the taxonomy-derived graph

## Manual entry points (after implementation)

```bash
make fetch    # download + cache the filing
make all      # full pipeline -> out/report.md
```

## What success looks like

Balance sheet foots within rounding tolerance, A = L + E holds, >= 95% of
face lines resolve to taxonomy concepts with stock/flow and sign attributes,
and the round trip from (z, m) reproduces the native rows exactly. Surprises
(negated labels, calc-linkbase inconsistencies, extension anchoring gaps) are
documented in the report; they are findings, not failures.

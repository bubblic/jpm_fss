# Financial Statement Simulator (FSS)

Two artifacts live in this repository:

1. **The FSS reference implementation** (`src/fss`): the full pipeline from
   the proposal (`proposal/Financial_Statement_Simulator_Proposal.pdf`):
   filing acquisition, redundant PDF extraction with a reconciliation gate,
   knowledge-graph state space with lossless encode/decode, a no-plug
   accounting engine, and scenario Monte Carlo, validated on four real
   annual reports (Apple, Microsoft: US GAAP 10-K; SAP, Spotify: IFRS 20-F).
2. **The original one-day KG encoding spike** (`src/spike`), kept intact as
   evidence: it proves the knowledge-graph encoding mechanics on one filing
   (see `out/report.md` after running it).

## FSS quick start

```powershell
$env:PYTHONPATH = "src"
$env:SEC_USER_AGENT = "Your Name your.email@example.com"
python -m fss fetch      # acquire filings, warm taxonomy caches, render PDFs
python -m fss extract    # tag-path ground-truth statements
python -m fss measure    # PDF-only extraction accuracy vs ground truth
python -m fss accept     # the full acceptance battery -> out/acceptance/
python -m pytest tests   # unit + seeded-error tests
```

`out/acceptance/report.md` carries the battery verdict: extraction accuracy
(zero accepted-cell errors required), perfect reconstruction, footing,
Monte Carlo identity integrity, the directional battery, and plausibility.
Per-company simulated statements and flow journals land in
`out/acceptance/<company>/`.

---

# KG Encoding Spike (original)

One-day spike for the financial statement simulator: prove that a
knowledge-graph encoding works mechanically on one real filing (Apple's
latest 10-K balance sheet). See CLAUDE.md for full context and PROMPT.md for
the task given to Claude Code.

## Setup (once)

### Windows (PowerShell, e.g. VS Code terminal)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# if activation is blocked: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
pip install -r requirements.txt

# SEC requires an identifying User-Agent on every request.
# EDIT THIS to your real name and email. $env: vars are per-terminal-session.
$env:SEC_USER_AGENT = "Jaebum Chung your.email@example.com"
```

### macOS / Linux / WSL

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SEC_USER_AGENT="Jaebum Chung your.email@example.com"
```

## Run with Claude Code

From this directory, launch:

```
claude
```

and type: `Read PROMPT.md and implement it.`

One-liner alternatives: `claude "$(Get-Content PROMPT.md -Raw)"` (PowerShell; the
-Raw flag matters, otherwise the prompt is mangled) or `claude "$(cat PROMPT.md)"`
(bash).

Claude Code will read CLAUDE.md automatically, write a plan to `out/plan.md`,
implement `src/spike/*`, and produce:

- `out/report.md`   – the spike findings (the artifact to show the director)
- `out/overlay.json` – z (leaf values) + m (presentation map) for the filing
- `out/graph.graphml` – the taxonomy-derived graph

## Manual entry points (after implementation)

Windows PowerShell (the Makefile is Unix-only, skip it):

```powershell
$env:PYTHONPATH = "src"
python -m spike.fetch
python -m spike.report
```

macOS / Linux:

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

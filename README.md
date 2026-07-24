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

The engine's flow system is verified symbolically (SymPy) before any run,
and the stochastic fan executes vectorized in TensorFlow with per-path
identity checks; the Decimal engine replays selected paths bit-exactly for
the audit artifacts.

## Untagged annual-report PDFs (no XBRL)

LLMs participate at BUILD time only; the runtime inference path is
deterministic (proposal v2). See `DEMO.md` for the full walkthrough.

Document scope is born-digital PDFs: statement pages must carry AUTHORED
text. Scanned or image-compiled documents -- including OCR'd scans, whose
invisible text layer would pass a naive has-text check while feeding every
reader from one OCR error source -- are detected mechanically per
statement page (page-dominating raster + absent/invisible text) and
abstain with "not born-digital" in both build and runtime modes.

```powershell
python -m fss onboard <pdf-or-folder>    # BUILD: LLM-assisted, audited;
                                         #   emits artifacts/mappings/<doc>.json
python -m fss onboard --rebuild <pdfs>   # BUILD: artifacts from committed
                                         #   build products, no model calls
python -m fss onboard <pdf> --carry-from <doc>
                                         # BUILD: seed pages and the label->
                                         #   concept map from a prior year's
                                         #   artifact; model consulted only
                                         #   for genuine deltas
python -m fss.carry_demo                 # two-pair cross-year validation vs
                                         #   the filers' own tags -> out/carry/
python -m fss runtime <pdf-or-folder>    # RUN: replay from the signed
                                         #   artifact; no model access; logs
                                         #   source/code/artifact versions;
                                         #   abstains on drift
python -m fss untagged <pdf-or-folder>   # exploration mode (legacy sweep)
python -m fss untagged --merge           # out/untagged/summary.md
python -m fss runtime  --merge           # out/runtime/summary.md
```

At build time the LLM (DeepSeek API via `DEEPSEEK_API_KEY`, or the Azure
gateway via `AZURE_DEEPSEEK_ENDPOINT`; `.env` supported) may propose
statement pages, median-voted readings for flagged cells, and concept
choices over lexical shortlists; every proposal passes a mechanical
validator (density bar, reader agreement, polarity veto, footing) and is
recorded in the audit log and the mapping artifact for human sign-off. At
run time no model client is ever constructed: adjudications replay only
where a deterministic reader still reads the signed value, outputs are
bit-exact across runs, and a changed document is refused with
"re-onboarding required". Unresolved cells stay flagged; documents with
flagged balance-sheet cells are refused simulation by design.

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

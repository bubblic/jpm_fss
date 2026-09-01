# PDF ingestion of annual reports

This is the operator path for a born-digital annual-report PDF with no XBRL
in the loop. It locates the balance sheet, income statement, and cash flow,
extracts cells through three independent readers, maps rows to taxonomy
concepts, and writes a reviewable mapping artifact.

Two commands, in order:

| Step | Command | What it does |
| --- | --- | --- |
| Build (ingest) | `python -m fss onboard <pdf>` | Locate, extract, map, check, write the artifact. An LLM is optional. |
| Run | `python -m fss runtime <pdf>` | Replay that signed artifact. No LLM. Refuses if the PDF was never onboarded or the bytes changed. |

`DEMO.md` is the recorded walkthrough of that split. This file is how to run
it on a new document.

## Setup (once)

Python 3.11 or newer. From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --isolated --index-url https://pypi.org/simple -r requirements.txt
export PYTHONPATH=src
```

PowerShell (Windows):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --isolated --index-url https://pypi.org/simple -r requirements.txt
$env:PYTHONPATH = "src"
```

`--isolated --index-url https://pypi.org/simple` skips a global NVIDIA extra
index that otherwise retries a dead host on every package. Bare `pip install
-r requirements.txt` is enough if that index is not on the machine.

Confirm the venv, not the system Python, is on the path:

```bash
python -c "import pypdf, pdfplumber; print(pypdf.__version__)"
```

If that raises `No module named 'pypdf'`, the venv is not active.

An LLM is not required for onboard. Runtime never uses one.

## Ingest a new PDF

```bash
python -m fss onboard /path/to/annual-report.pdf
```

A folder of PDFs works the same way:

```bash
python -m fss onboard /path/to/reports/
```

Sample documents already in this repository:

```bash
python -m fss onboard previous_LLM_extractor/annual_reports/for_financial_statements/microsoft_2025.pdf
```

The document name in outputs is a slug of the PDF stem (and of the parent
folder when the stem is only a year). `microsoft_2025.pdf` becomes
`microsoft_2025`.

Onboard always writes `artifacts/mappings/<doc>.json`, even when some
statements stay unresolved. Runtime will not accept a PDF that has no
artifact.

## Without an LLM (deterministic pipeline only)

Onboard does not require an endpoint. If neither `DEEPSEEK_API_KEY` nor
`AZURE_DEEPSEEK_ENDPOINT` is set, `default_client()` returns None and every
LLM-assisted stage falls back to the deterministic path.

```bash
unset DEEPSEEK_API_KEY AZURE_DEEPSEEK_ENDPOINT
python -m fss onboard /path/to/annual-report.pdf
```

There is no `--no-llm` flag. Unset the variables (or leave them unset). If
they are set, onboard will call the model for the fallbacks below.

What still runs with no model: page locate, three-reader extract, the
agreement gate, lexical and unique-hit taxonomy mapping, printed-subtotal
footing, Assets = Liabilities + Equity, the cash tie, and the mapping
artifact.

What stays unresolved without a model:

| Step | Result |
| --- | --- |
| Statement pages the locator misses | `"not located (no LLM fallback configured)"` |
| Cells the readers do not agree on | stay flagged; a flagged balance sheet refuses simulation |
| Labels the dictionary and taxonomy miss | stay unmapped |
| Reporting standard if the document scan abstains | unresolved, unless you pass `--standard` |

`--rebuild` is not a no-LLM ingest of a new PDF. It only rebuilds an artifact
from a previous onboard's committed products under `out/untagged/`.

## With an LLM (build time only)

Onboard may consult a hosted model for four fallbacks: statement pages the
locator missed, median-voted readings of flagged cells, concept choices over
a lexical shortlist, and a reporting-standard reading when the document scan
abstains. Every proposal still has to pass a mechanical check (density bar,
reader agreement, polarity veto, footing) and is written into the audit log
and the artifact.

Put credentials in the environment or in `.env` at the repo root:

```bash
export DEEPSEEK_API_KEY="..."
# optional: export DEEPSEEK_TEXT_MODEL="deepseek-v4-flash"
# or: export AZURE_DEEPSEEK_ENDPOINT="https://..."
python -m fss onboard /path/to/annual-report.pdf
```

The direct DeepSeek key wins when both are set. `python -m fss llm-check`
round-trips the configured client.

## After onboard: sign-off, then runtime

The artifact is written with `"approved_by": "PENDING SIGN-OFF"`. Review
`artifacts/mappings/<doc>.json` (pages, label-to-concept choices, cell
adjudications) and set `approved_by` to a name and date. Runtime stamps that
field into every report, so an unsigned artifact is visible.

Then replay with no model access:

```bash
python -m fss runtime /path/to/annual-report.pdf
```

Runtime looks up `artifacts/mappings/<doc>.json` and stops if it is missing:

```
no mapping artifact: run `fss onboard` and sign it off first
```

It also stops if the PDF bytes no longer match the SHA-256 recorded at
onboard (`re-onboarding and sign-off required`). It never locates pages,
never guesses a concept map, and never constructs an LLM client.

## Flags

| Flag | Command | When |
| --- | --- | --- |
| `--standard us-gaap` or `--standard ifrs` | `onboard` | The document scan cannot tell which framework it is. Recorded as the operator's declaration. |
| `--carry-from <doc>` | `onboard` | Seed this year's label-to-concept map from a prior document's artifact (semantics only, never page locations). Labels that match resolve without a model; the polarity veto, footing, and identities still run. |
| `--rebuild` | `onboard` | Rebuild artifacts from committed products under `out/untagged/`. No LLM, and not a path for a new PDF. |
| `--merge` | `runtime` or `untagged` | Rewrite the sweep summary from existing per-document outcomes. |

`python -m fss untagged <pdf>` is the older exploration sweep. For a new
annual report, use `onboard`.

Related helpers:

```bash
python -m fss.standards /path/to/annual-report.pdf   # declaration scan only
python -m fss.taxlabels                              # unique-hit taxonomy-label cache
```

Supported reporting standards are US GAAP and IFRS. A document that declares
a different framework, and no supported one, is refused. After review, rerun
with `--standard` to override.

## Outputs

Onboard (and `untagged`) write under `out/untagged/<doc>/`:

| File | Contents |
| --- | --- |
| `report.md` | Pages found, cell counts, footing / identity / cash-tie, mapping stats, whether simulation ran |
| `outcome.json` | The same facts as JSON |
| `balance_sheet.json`, `income_statement.json`, `cash_flow.json` | Extracted statements, when located |
| `audit_llm.json` | Call-by-call LLM record (empty `calls` when no client was configured) |

The mapping artifact is `artifacts/mappings/<doc>.json`.

Runtime writes the same statement and report shape under `out/runtime/<doc>/`.
Sweep summaries: `out/untagged/summary.md` and `out/runtime/summary.md`.

Simulation (six scenarios through the TensorFlow engine) runs only when all
three statements extracted, the balance sheet has no remaining flags, and
footing / identity / cash-tie pass. Otherwise the report names the skip.

## What will refuse

- **Not born-digital.** Statement pages must carry authored text. A scan, or
  a raster page with an invisible OCR overlay, abstains with
  `"not born-digital"` in both onboard and runtime. OCR ingestion is out of
  scope.
- **Unsupported reporting standard.** Frameworks other than US GAAP and IFRS
  are refused rather than mapped as if covered.
- **Runtime with no artifact, or a changed PDF.** See above.
- **Flagged balance-sheet cells.** They stay flagged until a later onboard
  (with LLM adjudication, or a signed replay that still matches a
  deterministic reader) resolves them. Simulation does not run on a flagged
  balance sheet.

Self-consistency is checked, not assumed. Printed subtotals, Assets =
Liabilities + Equity, and the cash tie can fail on a document the readers
did extract. That is a documented skip, not a silent pass.

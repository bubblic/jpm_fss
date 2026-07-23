# CLAUDE.md — KG Encoding Spike

## What this project is

A one-day spike for a financial statement simulator (internship project at a
major financial institution). The simulator's architecture encodes financial
statements into a common state space specified as a knowledge graph over the
US GAAP XBRL taxonomy. This spike proves the riskiest mechanical claims on one
real filing before the full build:

1. The taxonomy loads as a graph and carries the attributes we rely on
   (periodType = stock/flow, balance = sign convention, labels, calc arcs).
2. A real 10-K's balance sheet resolves onto that graph (a "firm overlay").
3. The overlay foots: subtotals equal weighted sums of children, and
   Assets = Liabilities + Equity, within rounding tolerance.
4. A round trip (values + presentation map -> regenerated statement rows)
   reproduces the native balance sheet exactly.

The spike is evidence for a proposal review, so the written report
(`out/report.md`) matters as much as the code. Surprises and limitations are
first-class findings, not failures.

## Hard constraints

- Host environment: Windows 11, PowerShell (VS Code integrated terminal).
  Do not emit bash-only syntax: no `export`, no `VAR=x command` prefixes, no
  `source`. Set env vars with `$env:NAME = "..."`, activate the venv with
  `.\.venv\Scripts\Activate.ps1`, and prefer plain `python -m spike.X`
  invocations. Use `pathlib` for all paths in code; never hard-code `/` or
  `\` separators. The Makefile is a Unix convenience only; on this machine,
  validate through the entry points directly (with `$env:PYTHONPATH = "src"`).
- Python 3.11+, virtualenv at `.venv`, deps only from `requirements.txt`.
- All SEC requests MUST send a User-Agent from the env var `SEC_USER_AGENT`
  (format: "Name email@example.com"). If unset, exit with a clear error.
  Stay well under 10 requests/second. Cache every download under `data/`
  and never re-download when the cached file exists.
- Never hand-edit or hard-code financial values. Everything in the report
  must be computed from the filing.
- No network calls in any code path other than the fetch step.

## Target filing

Apple Inc., CIK 0000320193, most recent 10-K.
- Find it via the submissions API: https://data.sec.gov/submissions/CIK0000320193.json
  (filter form == "10-K", take the most recent accession + primaryDocument).
- Filing files live under
  https://www.sec.gov/Archives/edgar/data/320193/{accession_no_dashes}/{file}.
- Modern 10-Ks are inline XBRL: the primary document (.htm) IS the instance.

## Arelle hints (these save hours)

- Install as `arelle-release` (import name `arelle`).
- Programmatic load:
    from arelle import Cntlr
    ctlr = Cntlr.Cntlr(logFileName="logToStdErr")
    model = ctlr.modelManager.load(path_or_url)
  Loading the local cached .htm inline-XBRL file works; Arelle discovers the
  DTS (taxonomy) from the filing's schemaRefs and downloads what it needs.
  Point Arelle's web cache somewhere inside `data/` if convenient.
- Concepts: `model.qnameConcepts` (dict qname -> ModelConcept), with
  `.periodType` ("instant"/"duration"), `.balance` ("debit"/"credit"/None),
  `.isMonetary`, `.label()`.
- Facts: `model.factsInInstance`; each fact has `.concept`, `.qname`,
  `.xValue`, `.context` (with `.instantDatetime` / `.endDatetime`,
  `.qnameDims` for dimensions), `.decimals`, `.unit`.
- Relationship sets:
    from arelle import XbrlConst
    calc  = model.relationshipSet(XbrlConst.summationItem)    # calc 1.0
    calc11= model.relationshipSet(XbrlConst.summationItem11)  # calc 1.1 (newer filings)
    pres  = model.relationshipSet(XbrlConst.parentChild, linkrole)
  Use `rel.weight` on calc rels (+1 / -1). Merge calc 1.0 and 1.1 results.
- Statement roles: iterate `model.roleTypes`; the balance sheet's linkrole
  definition typically contains "BALANCE SHEET" or "STATEMENT OF FINANCIAL
  POSITION" (case-insensitive, ignore parenthetical variants). Prefer the
  role whose definition contains "Statement" and not "Parenthetical".
- Presentation order: walk parentChild for the chosen linkrole; children are
  ordered by `rel.order`. `rel.preferredLabel` may be a negated label role
  (e.g. .../negatedLabel): if so, the DISPLAYED sign is flipped relative to
  the fact value. Record this in the presentation map; it is exactly the kind
  of subtlety the spike exists to surface.

## Tolerance rule for footing checks

Use the fact's `decimals` attribute: a value with decimals = -6 is stated to
the nearest million, so allow abs diff <= 0.5 * 10^6 * (n_children + 1) when
summing (rounding of each addend can compound). Report the actual diff.

## Suggested module layout (adjust freely)

    src/spike/fetch.py      # EDGAR submissions API + file download w/ cache
    src/spike/graph.py      # taxonomy -> networkx graph, stats
    src/spike/overlay.py    # facts -> firm overlay: z (leaves) + m (labels/order/signs)
    src/spike/checks.py     # footing, A = L + E, stock/flow coverage
    src/spike/roundtrip.py  # (z, m) -> rows; diff vs native rows
    src/spike/report.py     # writes out/report.md, out/overlay.json, out/graph.graphml

Entry point contract (the Makefile calls these):
    python -m spike.fetch
    python -m spike.report   # runs the whole pipeline end-to-end

## Definition of done

See PROMPT.md acceptance criteria. If any step blocks for more than ~30
minutes, stop fighting it, document the blocker and its implications in the
report's "Findings and limitations" section, and move on. A documented
blocker is a valid spike outcome.

## Style

Type hints, small functions, no cleverness. Standard library + the three
declared deps only. Keep prose in the report free of em dashes.

## Proposal writing

Any edit under `proposal/`, or to the claim-restating parts of `README.md`
and `DEMO.md`, follows `proposal/WRITING-GUIDE.md`: first principles before
use, no em dashes in prose, numbers only from committed pipeline artifacts,
and claim-level consistency across the summary surfaces listed there. Keep
that guide and this file in sync.

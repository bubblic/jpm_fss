# FSS design record

Architecture decisions for the Financial Statement Simulator (FSS)
implementation. The proposal document is the authority on intent; this file
records the concrete engineering choices the code follows.

Evidence status: the four-filer acceptance build validates numeric extraction,
statement reconstruction, arithmetic checks, and balanced simulation. Concept
mapping and economic-role assignment are still provisional. The IR validation
report contains mismatches that must be corrected and reviewed before those
layers are described as validated across firms or standards.

## Test set

| Firm | Standard | Form | Fiscal year end | Currency |
| --- | --- | --- | --- | --- |
| Apple Inc. | US GAAP | 10-K | 2025-09-27 | USD |
| Microsoft Corp. | US GAAP | 10-K | 2025-06-30 | USD |
| SAP SE | IFRS | 20-F | 2025-12-31 | EUR |
| Spotify Technology S.A. | IFRS | 20-F | 2025-12-31 | EUR |

Statements in scope: balance sheet, income statement, cash flow statement,
all comparative columns. Statement of equity and OCI are out of MVP scope.

## Pipeline and package layout

    src/fss/
      paths.py, config.py, manifest.py      shared services, audit manifest
      edgar.py                              EDGAR acquisition + PDF rendering
      xbrl.py                               Arelle loading, offline cache
      kg.py                                 taxonomy graph, roles, label index
      statements.py                         StructuredStatement model
      tagread.py                            tag-path extractor (iXBRL)
      pdfread/                              PDF readers (geometry, lines, pypdf)
      reconcile.py                          agreement gate, identities, audit
      encdec.py                             E(s)=(z,m), D(z,m), reconstruction
      engine/                               ledger, laws of motion, projection
      drivers.py, simulate.py               scenarios, Monte Carlo
      validate.py, render.py                checks, native rendering
      accept.py, cli.py                     acceptance battery, entry points
      measure.py                            PDF-only accuracy vs tag ground truth
      llm.py                                LLM clients (build time only), audit
      symbolic.py                           SymPy flow-closure and DAG order proof
      tfsim.py                              vectorized TensorFlow Monte Carlo fan
      untagged.py                           untagged pipeline; onboard/runtime
                                            mapping artifacts; carry-forward
      carry_demo.py                         adjacent-year carry-forward validation
      taxlabels.py                          unique-hit taxonomy-label tier index
      standards.py                          declared reporting standard: scan,
                                            scoping, unsupported-framework refusal
      ir_demo.py                            IR editions scored vs filings' tags

## Extraction error model

- Tag path (Arelle over iXBRL) is the ground-truth reference for the
  measured accuracy of the PDF-only mode, and the primary statement source
  when tags exist.
- PDF-only mode uses three decorrelated readers: R1 word-geometry table
  reconstruction (pdfplumber), R2 line-regex reader over pdfplumber text,
  R3 line-regex reader over pypdf text (independent PDF engine).
- A value is accepted only when at least two independent readers agree
  exactly after normalization (parentheses negatives, scale headers,
  per-share and share-count scale exemptions, currency symbols); all
  disagreements become flags, never silent picks.
- Accounting-identity checks (footing along calc arcs, A = L + E, cash
  begin + net change = end) run on the accepted set with the decimals-based
  tolerance rule from the spike.
- The measurable bar on the gating set: zero accepted-field errors vs
  ground truth, flag rate reported, rule-of-three upper bound quoted.
  The 1e-8 concordant-error figure is an architectural design target,
  argued from reader decorrelation, not an empirical claim from four
  filings.

## Statement model

Row identity is (concept qname, frozenset of (axis, member) qnames). Face
statements may use dimensions (Apple and Microsoft disaggregate revenue and
cost of sales by ProductOrServiceAxis on the face); dimensioned rows take
the member's label and are ordered members-first, undimensioned total last,
matching the EDGAR renderer. Instant rows inside the cash flow statement
(beginning and ending cash) resolve through periodStart and periodEnd
preferred labels. Values are Decimal, display sign via negated preferred
labels, unit and decimals carried per cell.

## Encode and decode

E(s) = (z, m): z holds leaf values keyed by (concept, dims); subtotals and
totals are derived (dropped from z, recomputed on decode through the calc
arcs); m holds row order, labels, signs, units, decimals, scale, column
periods, and derivation formulas discovered from the filing. D(z, m)
re-renders the statement; reconstruction must be exact on every cell of
every statement of every firm.

## Semantic mapping

- Concept mapping answers which US GAAP or IFRS concept a printed row
  represents. It is standard-scoped and should use the filer's own tag when
  available, then prior reviewed choices, then constrained candidates. An LLM
  may rank candidates at build time, but the selected concept requires evidence
  and review. The runtime replays a signed choice but does not treat replay as
  proof that the choice was semantically correct.
- Role mapping answers which economic law of motion applies. It is a separate,
  versioned, hand-authored table. Shared roles preserve the source concept and
  native presentation; they do not convert IFRS to US GAAP.
- A missing or ambiguous material concept or role refuses simulation rather
  than silently assigning a cross-standard equivalent.
- Runtime artifacts must be signed, declare a supported reporting standard,
  and contain no mapping outside that standard unless the individual record
  carries an explicit reviewer-approved bridge/extension rationale.
- Simulation readiness is a separate gate from extraction quality. It names
  material document-local rows, broad default roles, unbound working-capital
  movements, and missing cash/equity/articulation roles; those rows remain in
  the structured report but cannot silently drive or be zeroed by a scenario.
- Mapping outputs record row label, concept, source tier, declared standard,
  balance, period type, and any standard exception. Candidate lists, note
  evidence, dimensions, and reviewer identity remain work for the review UI.

## Engine (no plugs, no circularity)

Double-entry posting core: every flow posts balanced amounts to at least two
ledger accounts (the balance-sheet leaves plus an income summary closed to
retained earnings). A = L + E holds by construction and is asserted, never
plugged. Cash is never a residual account: it accumulates only explicit cash
postings, and the simulated cash flow statement is the journal of cash
postings grouped by native line, so the cash tie holds by construction.

Computation order per simulated period: (1) income statement leaves from
driver rules; (2) operating stock targets (ratio rules: DSO, DIO, DPO,
revenue-linked others) imply working-capital flows; (3) discretionary flows
(capex, buybacks, dividends, debt schedule, investment purchases and
maturities) from base-year levels and the liquidity policy rule (excess cash
swept to securities above a floor, a behavioral rule rather than an
accounting plug); (4) post everything, close income to retained earnings;
(5) recompute derived subtotals through the calc arcs; (6) validate.
Equity and other unmodeled stocks carry base-year residual movements as
explicit held-at-base "other movement" flows, disclosed in the audit trail.

## Driver layer

Scenario schema: real GDP growth (pp), inflation (pp), short rate change
(bp), industry competition index (z-score), firm demand shock (z-score).
Reasoned nonlinear responses: revenue growth = base momentum + beta_gdp *
GDP surprise - competition squeeze (logistic), margins compress under
competition and unrecovered inflation, interest income and expense reprice
with the rate shift on floating shares. Gaussian noise on growth and margin
with fixed seeds; Monte Carlo (default N = 500) propagates through the
engine so every path is internally consistent. Directional battery compares
scenario means; plausibility battery checks signs, bounded growth and
margins, non-negative cash, inventory, PP&E, and exact identities.

## Auditability

Every run writes a manifest (input file SHA-256 hashes, package versions,
config, seed), a field-level provenance log (each reader's raw token, page,
normalized value, agreement status, adjudication), the posting journal for
every simulated path summary, and the validation results. All computations
are Decimal or seeded; reruns are bit-identical.

## Licensing

pdfplumber (MIT), pypdf (BSD), Arelle (Apache-2.0), networkx (BSD),
requests (Apache-2.0). No AGPL components. IFRS taxonomy files download
from the IFRS Foundation's public distribution during DTS resolution and
stay in the local cache; their license permits use for analysis but not
redistribution, so data/ is git-ignored.

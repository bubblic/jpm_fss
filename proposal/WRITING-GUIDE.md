# Writing guide for the proposal

These conventions govern every edit to the proposal documents under `proposal/`.
They are enforced the same way as in the repository this guide was adapted from:
`CLAUDE.md` (loaded at the start of every session) points here for any edit under
`proposal/`. Keep this guide and `CLAUDE.md` in sync.
(`WRITING-GUIDE_examplefrombefore.md` is the frozen original from the white-paper
repo; this file is the live rule set for this one.)

The document set:

- `Financial_Statement_Simulator_Proposal.tex` is the **full proposal**, the owner
  of every claim, and the deliverable: the director reads the PDF, so the rebuilt
  PDF is committed with the source.
- `Financial_Statement_Simulator_Proposal_Draft_v2.tex` is the June discussion
  draft. It stays circulated, so it receives **corrections, not upgrades**: when a
  claim it states has since been corrected as wrong (the born-digital scope gate
  was such a case), propagate the correction so the retired claim stands nowhere
  as if still true. Deliberate evolution (the tightened timeline, the softened
  measurement language) stays, because the full proposal narrates those deltas
  explicitly. When in doubt, propagate.
- `Financial_Statement_Simulator_Proposal_Draft.tex` (v1) is frozen history. Do
  not edit it.

## 1. The cardinal rule: first principles before use

Introduce every concept and every equation from first principles, and explain it
before using it. Nothing appears cold.

Concretely, before a term, symbol, or formula is deployed in an argument:

- **Define the term at first use**, in plain language, before leaning on it.
- **Introduce notation before it appears in a formula.** No symbol shows up in an
  equation that was not named first.
- **Give the intuition before the formalism.** Say what the equation means and why
  it is true in words, then write it.
- **Derive equations, or sketch the derivation inline.** This proposal has no
  appendices; a proposition gets its proof idea in the following paragraph (as
  the injectivity proposition does), and a one-line derivation ("by linearity")
  is written out rather than asserted.
- **Assume a smart reader who knows finance but not XBRL.** The readers (the
  director, quant colleagues, the accountant reviewer, model risk) are fluent in
  statements, debits and credits, and Monte Carlo, and fluent in none of: XBRL
  internals (concept, linkbase, dimension, period type, balance attribute), the
  taxonomy graph, or this codebase. Define those at first use; never lecture
  accounting basics.

Worked examples already in the proposal, to match the standard:

- The state space is motivated in words (line items are heterogeneous; standards
  become cheap to add; Part II needs a pooled representation) before `E(s) = (z, m)`
  appears, and the cost of the indirection (nothing may be lost) is stated before
  the injectivity proposition formalizes it; the proof idea (statements agreeing
  on `(z, m)` agree cell for cell, because derived cells are functions of stored
  ones) is given inline, with the two key-clause failure modes (dimensioned rows,
  period roles) named and turned into regression tests.
- Balance polarity `beta_a` and the posting map `phi_f` are defined before the
  balanced-flow equation; residual invariance is then derived by linearity before
  it is asserted per path; "no plugs" is given an operational meaning (preserve
  the filer's own printed residual, add exactly zero of your own) before SAP's
  two-million-euro case exercises it.
- Every driver symbol carries its units at introduction (percentage points, basis
  points, z-scores) before the equations, and the economics is argued in words
  alongside: inflation passes into costs faster than into prices, hence
  `lambda_pi < lambda_c`; a rate hike's sign follows the firm's own net cash
  position, computed from its balance sheet, not asserted.
- The rule-of-three bound `3/N` is stated with its citation the first time a
  zero-error result is quantified; the footing tolerance `0.5 * 10^(-d) * (n+1)`
  is built from what `decimals` means before any gate cites it.
- The silent-concordance model is built in words first (the two failure modes
  have different costs; disagreement costs review time, concordance is the
  expensive event) before `c * prod(p_i)` and the `10^-8` target appear.

A quick checklist for any new concept or equation:

1. Is the term defined, in words, at first use?
2. Is every symbol introduced before it appears in a formula?
3. Is the intuition stated before the math?
4. Is the equation derived inline, or its derivation sketched in one line?
5. Could a smart reader with no XBRL or graph background follow it?

If any answer is "no," explain it first.

## 2. Style and voice

- **No em dashes.** Not `---`, not a Unicode em dash, and not a spaced `--` doing
  an em dash's job in prose. Use commas, semicolons, colons, parentheses. En-dash
  ranges (`\ref{eq:a}--\ref{eq:b}`, date and page ranges) and TikZ path syntax
  (`--` inside `\draw`) are fine and are excluded by the checks in section 4.
- **One continuous argument.** The spine: a bank needs forward-looking statements
  it can audit; three design commitments carry the answer (ingestion at a
  near-zero error bar enforced by decorrelated agreement; encoding lossless by
  injectivity; an engine that cannot break the books); each commitment gets its
  mechanism section, its measured result in the evidence section, and its
  governance wrapper. Every section builds a commitment, evidences it, or wraps
  it for deployment; nothing free-floats.
- **Tight and information-dense**, matching the existing prose. `\lead` paragraphs
  are the unit of argument below subsections; numbers live in tables, prose
  carries meaning; state each idea once, in its owner section, then
  cross-reference rather than repeat.
- **Intellectual honesty is the sales pitch.** The proposal's credibility rests on
  "these are not aspirations" and "reported honestly as such". Concede what is
  not measured; keep the risk register's mitigation column honest statements,
  not reassurance; name the blockers (an image-based document is the designed
  OCR boundary, a flagged balance sheet refuses simulation by design).
- **Name slippery distinctions explicitly** rather than blur them. This
  proposal's list:
  - extraction vs encoding: a measured error rate vs deterministic and lossless;
  - accepted vs flagged: "zero errors" is a claim about accepted cells, and
    flags are the design working, not failures;
  - measured vs defended by construction: `3/N` is measured, `10^-8` is a target;
  - residual invariance vs zero residual: preserve SAP's two million, add none;
  - build time vs run time: the LLM onboards, the runtime replays;
  - born-digital vs has-a-text-layer: OCR'd scans carry (invisible) text;
  - stochastic by construction vs calibrated: Part I vs Part II;
  - stored vs derived rows: demotion is disclosure, not failure;
  - tagged filings vs the PDF-only ablation vs the truly untagged sweep: three
    evidence regimes, each at its own bar;
  - directional credibility vs point forecast.

## 3. Structure, mechanics, and numbers

- **Single-file LaTeX per document** (unlike the source guide's modular paper):
  preamble and palette at the top, body in `% ===== N. Title =====` banner
  blocks, bibliography inline as `thebibliography`. The banner numbers match the
  rendered section numbers (keep them matching when sections move), and
  cross-references go only by `\ref` with labels (`sec:success`,
  `sec:engine`, `sec:drivers`, `sec:robustness`, `sec:evidence`,
  `sec:governance`, `sec:plan`, `sec:limits`), never by hand-typed number.
- **Helpers**: `\lead{color}{Title.}` for argument paragraphs, `\headtext` in
  table headers, `\pass`, the `proposition` theorem environment. Figures are
  TikZ and conceptual (the pipeline, the gate); tables carry the measured
  numbers.
- **Every external claim cites** a `thebibliography` entry: standards and specs
  (XBRL 2.1, Calculations 1.1, the taxonomies, EDGAR and ESEF mandates),
  literature (no-plug forecasting, stock-flow consistency, extraction datasets),
  governance texts (SR 11-7, BCBS 239), and tools.
- **Numbers are computed, never recalled.** Every quantitative claim in any
  proposal document traces to a committed pipeline artifact: the acceptance
  battery under `out/acceptance/` (extraction table, reconstruction counts,
  Monte Carlo integrity, directional and plausibility batteries), the untagged
  sweep under `out/untagged/`, runtime determinism under `out/runtime/` and
  `artifacts/mappings/`. Quote the artifact; when in doubt re-run it
  (`$env:PYTHONPATH = "src"`, then `python -m fss accept --company X` per firm
  and `python -m fss accept --merge`; a single-shot full accept exceeds the
  10-minute command cap). Never hand-type a financial value or a result count
  from memory; this extends CLAUDE.md's hard rule for the spike report to the
  proposal.
- **Table figures equal the artifact exactly** (994, 198/227/319/250, 1,162,
  12,000, fourteen). If a pipeline change moves a number, the change lands in
  the artifact first, then in every restating surface (section 5), never the
  other way around.

## 4. Build hygiene (Windows, PowerShell)

- Compile from `proposal/` with the user-scoped MiKTeX, twice, so labels and
  references settle:

      & "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe" `
        -interaction=nonstopmode Financial_Statement_Simulator_Proposal.tex

  Zero undefined references and no real errors; fix overfull boxes beyond a few
  points. There is no Make target for the proposal; the repo Makefile is the
  spike's Unix convenience.
- Dash checks (both must return nothing):

      Select-String -Path *.tex -Pattern '---|—' |
        Where-Object { $_.Line -notmatch '^\s*%' }
      Select-String -Path *.tex -Pattern ' -- ' |
        Where-Object { $_.Line -notmatch '\\draw' }

- Retired-phrasings scan (section 5; must return nothing):

      Select-String -Path .\Financial_Statement_Simulator_Proposal.tex,
        ..\README.md, ..\DEMO.md -Pattern
        'one more gated reader|All processing is local|has a text layer|text-based'

- After a figure or table change, open the PDF and look at the page before
  committing.
- Commit the rebuilt PDF with the source. If a correction propagated into
  Draft_v2, rebuild and commit its PDF too.

## 5. Consistency is claim-level, not just structural

A substantive claim lives in one **owner** section but is restated on several
**summary surfaces**. When the owner is corrected, the summaries go stale unless
the change is propagated by hand. Cross-references resolving and a clean compile
do **not** catch this; it is a semantic, claim-level check. (The live example
from this repo: the build/runtime split landed in the robustness section and in
Draft_v2, but the governance section kept "LLM-based readers, when added, run as
one more gated reader" and an unscoped "all processing is local" until
2026-07-23. The mechanism section had moved on; a summary surface had not.)

**Owners.** The evidence section (`sec:evidence`) owns every measured number;
the success section (`sec:success`) owns the gates; the robustness section
(`sec:robustness`) owns the extraction, LLM, and document-scope claims; the
engine section owns no-plugs and invariance; the reconstruction subsection owns
losslessness; the plan section owns dates.

**The summary surfaces.** Re-read all of these on any substantive claim change,
and whenever asked whether the proposal is consistent:

- the executive summary (the three design commitments and the headline numbers),
- the context section's "riskiest mechanical claims have been retired" paragraph,
- the success section's preamble ("every one of them has already been met"),
- the component-status table in the architecture section, and its caption,
- figure and table captions that state verdicts (the pipeline caption asserts
  "deterministic and lossless"; the gate caption asserts independence
  weighting),
- "What this de-risks" at the end of the evidence section,
- the risk register's mitigation column,
- the open-questions preamble ("settled ... by evidence"),
- Draft_v2's corresponding paragraphs (precision asymmetry, tags not a
  prerequisite, LLMs at build time, residual risk, born-digital scope),
- `README.md` (the FSS overview and untagged section restate the zero-error
  bar, the born-digital scope, and the build/runtime split),
- `DEMO.md` (the walkthrough restates the build/runtime constraint end to end),
- `docs/DESIGN.md` (the test-set and scope tables).

**The rule.**

1. When you change a substantive claim, open every summary surface and update
   each restatement to match. Then re-read each to confirm it states the *same*
   claim, in the *same* direction, as the owner section.
2. Treat your own recent edits as suspect. Re-read them; do not assume they
   already align.
3. When asked "is it consistent," re-read all summary surfaces and diff each
   restated claim against its owner. Report *what* you checked (claim-level vs
   structural). Never answer "yes, consistent" from a structural skim.
4. Run the section 4 checks (build, dashes, retired phrasings) as the mechanical
   backstop. They do not replace step 3.

**The load-bearing claims** (keep these phrased the same wherever they appear):

- *Extraction*: zero errors among **accepted** cells (994 of 994; four filers,
  three statements, all columns); the "accepted" qualifier always present; the
  rule-of-three 95% upper bound is `3/N` (0.30% at 994); every non-accepted cell
  is flagged, never guessed; every unmatched ground-truth row sits in a
  documented benign category.
- *Concordant error*: `10^-8` per field is a design **target** for silent
  concordant error, defended by construction and seeded-error testing, measured
  only where measurement is possible. Never presented as measured.
- *Reconstruction*: `D(E(s)) = s` exactly, 1,162 of 1,162 cells over 12
  statements; injectivity keys are (concept, dimensions, period role);
  filer-rounded subtotals are demoted to stored with the discrepancy disclosed
  (SAP's sixteen).
- *Engine*: no plugs, no circularity; stocks move only through balanced flows;
  the engine asserts residual **invariance**, preserving the filer's own printed
  residual (SAP's two million euro at millions precision) and adding exactly
  zero; the liquidity sweep is a behavioral treasury rule, the books balance
  without it; per-firm flow closure is proven symbolically (SymPy) before any
  numerics, which caught the latent NCI gap.
- *Simulation*: 12,000 paths (six scenarios x 500 paths x four firms), zero
  identity violations; common random numbers across scenarios so mean deltas
  measure response, not noise; TensorFlow float64 fan with bit-exact Decimal
  replay agreeing to `1e-10`; the directional battery passes in full, with the
  rate-hike sign taken from the firm's own net cash position.
- *The gate*: independence-weighted; geometry plus one text engine accepts; the
  two text engines alone accept only where geometry has no reading, recorded as
  the weaker rule.
- *The LLM*: may break ties, may never introduce a number no deterministic
  reader read; concept choices from lexical shortlists under a polarity veto;
  build time only. `fss onboard` emits a signed, versioned mapping artifact;
  `fss runtime` never constructs a model client, replays adjudications only
  where a reader still reads the signed value, refuses drifted hashes
  ("re-onboarding required"), and reruns byte-identically. With no endpoint,
  every stage degrades to deterministic behavior plus flags. A prior year's
  signed artifact can seed a new year's onboarding (`--carry-from`):
  exact-label matches replay reviewed choices, deltas go to the model, and
  carry replicates the prior artifact verbatim, errors included, so the
  inherited sign-off, not the mechanism, is the accuracy gate.
- *Document scope*: born-digital means **authored** text on statement pages;
  OCR'd scans carry an invisible text layer over raster and must abstain; the
  gate is mechanical and per page; the cut removes an OCR dependency, not the
  correlated-failure concern (a poisoned ToUnicode map is born-digital, and the
  identities and tag path still cover it).
- *Untagged sweep*: fourteen investor-relations documents, five jurisdictions,
  five distressed filers; a flagged balance-sheet cell refuses simulation (the
  structural quality gate).
- *Part I vs Part II*: Part I is stochastic by construction, a
  scenario-conditioned distribution with reasoned, documented (not fitted)
  parameters, and is **not** a calibrated probabilistic forecast; Part II
  replaces the noise with a learned conditional joint distribution, everything
  else fixed, and starts only on MVP sign-off.
- *Vendor data*: standardized feeds are a non-injective encoding and cannot be
  the primary representation regardless of accuracy; outsourcing ingestion
  fails the capability test by construction; a licensed feed can serve as an
  adjudication reader.
- *Dates*: internship window 31 August 2026 to 26 February 2027; MVP
  feature-complete 4 December 2026; accountant sign-off 15 January 2027
  (Draft_v2 keeps its own older dates by design; the full proposal narrates the
  delta).
- *Sev-1 rule*: any accepted-cell error, ever, is a sev-1 against the
  extraction layer; the fix is a general rule demonstrated by a new seeded
  test, never a filer-specific patch.

**Retired phrasings** (must not reappear; mirrored in the section 4 scan):

- The silent-concordance target presented as measured ("toward `10^-8`,
  measured"). The corrected posture: measured where measurement is possible
  (the `3/N` bound on accepted cells), defended by construction and seeded
  errors where it is not. (Draft_v2's own sentence stays as draft history; the
  scan therefore covers the full proposal, README, and DEMO only.)
- Tags as a prerequisite. Corrected: tags are the best case, not a
  prerequisite; reduced redundancy surfaces as a higher flag rate, not silent
  error.
- "Text-based PDF" or "has a text layer" as the untagged scope criterion.
  Corrected 2026-07-23 (commit `dfebc17`): the criterion is **authored** text;
  OCR'd scans have text layers and must abstain.
- The LLM as a runtime reader ("runs as one more gated reader", "when added"),
  and the unscoped "all processing is local". Corrected 2026-07-23 in the
  governance section, propagating the build/runtime split (commit `b8bed`):
  the runtime path is local and model-free; build-time onboarding may call the
  hosted endpoint under the leash.

Add to this list, and to the scan pattern in section 4, whenever a substantive
claim is corrected.

**What auto-maintains, and what you update by hand.** Nothing here
auto-maintains: there is no check script yet, so the section 4 commands are run
by hand and the summary-surface list above is a *principle* (any surface that
restates a verdict it does not own), not a fixed set; a newly added surface is
already in scope and just needs re-reading against its owner. If the checks
grow, a `scripts/` check in the style of the source repo is the natural Phase 0
industrialization. Two things no script could infer must be updated as part of
the edit that occasions them: the **retired-phrasings list** (and its scan
pattern) and the **load-bearing claims** above, whose canonical phrasing must
track the argument as it evolves. Recognizing that an edit *reframes, corrects,
or retires* a claim (from the request, "fix this," "that's overstated," "we no
longer say X," or from your own act of replacing a verdict's wording) is a
judgment made at the moment of the edit, and the follow-through is part of that
same edit: retire the old wording here, propagate the corrected claim to every
summary surface (including `README.md` and `DEMO.md`, which live outside
`proposal/`), rebuild the touched PDFs, and run the scans. A script cannot infer
what you just retired; you can, because you are the one retiring it.

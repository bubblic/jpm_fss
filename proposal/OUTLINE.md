# Proposal outline (working scaffold, 2026-07-27)

Purpose: a claim-level map of `Financial_Statement_Simulator_Proposal.tex` for
the restructure review. Mark bullets: `KEEP` / `MOVE to X` / `CUT` / `FIX:
note` / add new bullets where something is missing. This file is a scaffold,
not a summary surface: it restates claims only to map them, must not be cited,
and gets deleted when the restructure lands.

My first-pass flags are inline: **[order?]** possible misplacement,
**[dup?]** possible redundancy, **[gap]** candidate missing content,
**[check]** verify wording or claim. Everything unflagged I believe is
correct, in place, and pulling weight.

History: the pipeline reorder was executed 2026-07-27 (extraction before the
state space and engine; onboarding consolidated into 7.1; sections 6.1/6.2
promoted to 8.1/8.2; everything after renumbered). As of 2026-07-28 this
outline follows the current document order and numbering throughout.

---

## 1. Executive summary

- System definition in one sentence: reads an annual report, re-expresses it
  in one state space spanning both standards, advances it under a scenario
  with an engine that cannot break the books, renders next-period statements
  in the firm's own lines and standard.
  **[FIX applied 2026-07-27]** Dropped "economic" from the opening sentence:
  the union container is structural, the economic commonality is the
  behavior layer's; "economic state space" joined the retired-phrasings list
  and scans.
- Bank uses: forward-looking credit, scenario and stress analysis of
  counterparties, portfolio what-if screening, auditable substrate for MRM.
- Four design commitments (each with its mechanism section and its measured
  result):
  - Ingestion at a near-zero error bar, enforced by decorrelated readers,
    exact agreement, identity arbitration; everything else flagged.
  - Encoding provably lossless: encode-then-decode exact, injective encoder.
  - Simulation cannot silently break accounting: balanced flows, cash never
    a residual, identities asserted per path.
  - Machinery written once: union state space; behavior (glossed: how a line
    item moves under a scenario) attaches to roles, the common behavior
    layer; engine and scenario layer serve every name with no per-firm code.
- Already demonstrated: four filers, two standards; 994/994 accepted PDF
  cells exact; 1,162/1,162 reconstruction; 12,000 consistent Monte Carlo
  paths, directional battery passes; map of mechanism sections.

## 2. Context and alignment

- Enterprise-grade bar was the intent from the outset.
- Prior intern contributions: no-circularity engine core, autoregressive
  drivers validated on synthetic data.
- What was missing and is scoped here: extraction layer for real filings,
  per-standard encode/decode adapters, the union state space itself, a
  credible driver-to-flow relationship layer.
- Part I (MVP, this proposal): faithful simulator, stochastic by
  construction. Part II (conditional): learned conditional joint driver
  distribution, everything else fixed.
- Working code retired the riskiest mechanical claims: the one-day KG spike,
  then the validation build extending it end to end. Gates are committed on
  observed evidence, not judgment alone.

## 3. Problem statement and intended use

- Banks consume statements at scale, almost entirely retrospectively.
- The forward-looking questions are answered today by hand-built spreadsheet
  models: slow, inconsistent, unauditable, plug-dependent.
- Five properties: faithful (to the digit), consistent (identities, no
  plugs), comparable (one union state space, common vocabulary above it),
  presentable (native lines), auditable (bit-for-bit reproducible).
- Intended users and uses lead; analytical tool, not a regulatory model;
  graduation to model inventory is a process step, not a rewrite.
- Non-goals: no point-estimate competition, no pricing, no cross-standard
  conversion; Part I output is scenario-conditioned distribution, not a
  calibrated forecast.

## 4. Prior work

- Internal: interns' symbolic-first discipline (SymPy validation, TF
  compilation) adopted; author's LLM extraction pipeline reused (client,
  prompts, median vote); director's redundant-reader pattern is the
  robustness backbone; the June spike citation.
- Statement modeling without plugs: Velez-Pareja and Tham; Godley and Lavoie
  stock-flow consistency; Penman articulation. Engine is the firm-level,
  line-item application, closure asserted programmatically.
- Structured financial data: XBRL 2.1, Calculations 1.1, US GAAP and IFRS
  taxonomies as the node set, EDGAR and ESEF mandates, Arelle as tag-path
  reader.
- Document extraction: table-structure and financial QA literature documents
  how error-prone extraction is; motivates the gate rather than trust in any
  single reader.
- Vendor data: standardized feeds are a non-injective encoding, so they
  cannot be the primary representation regardless of accuracy; as-reported
  feeds are third-party extraction pipelines; the capability under
  examination is ingestion itself, so outsourcing fails the test by
  construction; a licensed feed can serve as an adjudication reader.
- Governance standards: SR 11-7 and BCBS 239 define what enterprise-grade
  concretely means here.

## 5. Definition of success (acceptance bar)

- Qualitative bar: accountant finds nothing obviously wrong; exact line-item
  parity; conforms to the source standard; correct directional response.
- Quantified gates (all already met by the validation build):
  1. Extraction: zero errors among accepted cells against verified ground
     truth (glossed: filer's own tags, or hand-verified double-entry where
     no tags exist); every non-accepted cell flagged; unmatched ground-truth
     rows in documented benign categories; rule-of-three bound derived
     inline (3/N at 95 percent); silent concordant error target 10^-8 is a
     design target, defended by construction and seeded errors, never
     presented as measured.
  2. Reconstruction: D(E(s)) = s exactly, every cell, every attribute.
  3. Arithmetic: footing within the decimals tolerance, derived inline;
     A = L + E; cash flow ties to the balance-sheet delta.
  4. Simulation integrity: zero identity violations; the filer's own printed
     rounding residual preserved exactly.
  5. Directional battery passes in full.
  6. Plausibility: automated bounds plus accountant review; sign-off is the
     human gate.
- Precision asymmetry lead: extraction near-zero, encoding exact by
  construction, simulation directionally credible with absolute internal
  consistency.

## 6. System architecture

- Simulation core is common; standard-specific work sits at the boundaries.
- Figure 1: pipeline (extract, encode with the behavior-layer branch beside
  it, drive and post, decode).
  **[FIX applied 2026-07-27]** The behavior layer was missing from Figure 1:
  the structured statement now feeds both the encoder (to (z, m)) and the
  role cascade (to roles per line), and the driver layer + engine consume
  both; caption states that identities bind on (z, m) alone.
- Component-status table: extractor, onboarding + mapping artifact,
  adapters, union state space, engine, driver layer; all validated by the
  build.
- Exposition follows the pipeline: extraction first, then the state space,
  then engine and drivers, argued in one sentence.
  **[FIX applied 2026-07-27]** This replaced the earlier inside-out order; a
  balance-polarity gloss was added at the term's first use since Section 7
  now precedes Section 8.2.

## 7. Extraction robustness

- Bar rationale; mirrors the director's redundant-reader engineering.
- What reading a PDF means lead: a PDF stores drawing instructions; text
  recovery is interpretation; R2/R3 are two engines that fail differently,
  R1 reconstructs the table spatially from positions, R4 reads tags without
  interpreting the page; exact source plus decorrelated interpreters is why
  agreement is evidence.
  **[dup?]** Overlaps filter item "Decorrelated input paths" below; consider
  merging the filter's list into this lead or trimming one of the two.
- Figure 2: the reconciliation gate; independence-weighted agreement.
- Failure-mode economics: disagreement costs review time; silent concordance
  is the expensive event; numbered concordance equation (product of error
  rates times the wrong-value overlap kernel, with q_i introduced and the
  kernel entering once for the ensemble); three scale inputs tied to the
  equation's parts; 10^-8 posture.
  **[FIX applied 2026-07-28]** Formalized with an equation label per review;
  downstream equation numbers shift by one (driver equations now three
  higher-numbered; all references are by eqref).
- Three filters: cross-reader agreement (weighted acceptance rules);
  decorrelated input paths (positions, two text engines, tags, optional
  vision reader and prior-year comparatives; pathology decorrelation vs the
  tag path); accounting-identity checks (also surface genuine filing typos).
- Document scope, born-digital lead: authored text required; where the
  characters come from (authored exact vs OCR guessed); the mechanical
  per-page gate (image XObject plus absent/invisible text; font embeddedness
  deliberately not a hard signal); enforced and tested with seeded scan
  pages; the cut removes an OCR dependency, not the correlated-failure
  concern (corrupted text layers; defenses named).
- Tags are the best case, not a prerequisite: untagged mode generalizes;
  PDF-only ablation defined; ablation certifies the method, production uses
  tags.
- Arithmetic before semantics: words nominate, numbers confirm; footing
  solver with weight search and multi-column closure; balance-sheet identity
  anchors (Chinese label pack; not-checkable honesty); cash tie nomination
  and fallbacks; all before any taxonomy concept is assigned.
- Figure 3: untagged order with the behavior layer joining at simulation
  time.
- The mapping ladder: four rungs in order (harvested lexicon, carried
  artifact, unique taxonomy labels, model over a shortlist); polarity veto
  on the heuristic rungs (glossed at first use); precision-not-coverage
  character of the taxonomy tier.
- Residual risk: the silent intersection (for example uniform mis-scaling);
  seeded-error battery including the scan/OCR abstain test; re-prompts never
  count as independent; adjudication weight follows path independence.

### 7.1 Onboarding and the mapping artifact **[FIX applied 2026-07-27]**

- Intro: ingestion is per-run computation, but mapping choices and
  adjudications are per-document judgment; judgment gets a lifecycle (made
  once with the model's help, validated mechanically, reviewed, signed,
  replayed). Timescale asymmetry stated: sign-off gates concept mapping;
  versioning and the battery gate the behavior layer.
- Figure 4: the lifecycle (document, onboard under the leash, signed
  hash-bound artifact, sign-off, model-free runtime replay with drift
  refusal, the carry-from arc: semantics, never layout).
- The LLM's leash: reused pipeline; page-identification fallback (measured:
  five of forty-two); cell reading only ratifies a value a reader read;
  mapping from a shortlist; no endpoint means deterministic degradation.
- LLMs at build time, determinism at run time: why hosted inference cannot
  sit in the runtime path; onboard emits a signed mapping artifact; runtime
  never constructs a model client, replays only still-read values, refuses
  drifted hashes; byte-identical reruns demonstrated; endpoint-refusal
  anecdote absorbed by design.
- Across years: carry-forward: artifact binds to one document by hash; carry
  seeds semantics, never layout; only genuine deltas reach the model; carry
  replicates errors too, so inherited sign-off is the gate.

## 8. The union state space

- Section intro (two sentences): extraction delivers native lines;
  simulation needs a representation to evolve them in; encoding and its
  proof first, then the graph and the behavior layer.

### 8.1 Encoding, decoding, and perfect reconstruction

- Why a state space at all: heterogeneity of native lines; standards become
  cheap to add; Part II needs a pooled representation. Price: nothing may be
  lost.
- Common means shared coordinates, not shared shape: no vendor-style
  template; z has no fixed width; each firm populates the subset it
  discloses.
- Rows already carry their nodes by encode time (tags or onboarding); E only
  splits values from presentation, which keeps losslessness a proved
  property of E rather than a claim about mapping quality.
- Firms of different shape meet through three graph mechanisms: aggregation
  upward; driver inheritance downward (rates push down, aggregates recompute
  upward, pro-rata deltas and exact footing fall out; preserved-mix
  limitation named); roles for the engine, written once.
- Formal core: s, E(s) = (z, m); injectivity proposition with keys
  (concept, dimensions, period role); proof idea inline; dimension and
  period-role lessons as regression tests.
- Mapping-error taxonomy: wrong-but-distinct concept costs E nothing;
  key-collision breaks injectivity and trips the reconstruction gate.
- Filer-rounded subtotals demoted to stored with disclosure (SAP).
- Encoding construction is deterministic; no model participates.
- A forecast is the same mechanism: D(z', m).

### 8.2 The state space as a knowledge graph

- One typed graph over both taxonomies (roughly 17,000 concepts each), each
  standard at its own coordinates, values never merged.
- Node attributes: period type (stock/flow), balance polarity, monetary
  flags, labels. Five edge types: composition, dimensional aggregation, laws
  of motion (authored), label/synonym, driver attachments.
- Authored layers cover the simulated core (one to three hundred concepts).
- Figure 5: machinery on a fragment of real overlays; Appendix A pointer for
  the complete Apple overlay.
- Firm overlay: how native lines resolve (tagged, extension-anchored,
  untagged label-index with footing and polarity confirmation, abstain
  rule); leaves become z; one graph serves five consumers.
- The common behavior layer: behavior defined in plain language (which
  drivers act, which flows carry changes, which policy rules touch it; same
  role, same rules); concepts answer which, roles answer what kind; ninety
  authored roles across the three statements; deterministic cascade with
  recorded provenance (concept table, label keywords with section, section
  and polarity default, extension inheritance); classified every face line
  of all four filers with no per-firm code.
  **[FIX applied 2026-07-27]** Cascade provenance strings renamed in code
  to name the rule tier, not the field: concept_table, label_rule (and the
  cash begin/end split now carries its accurate provenance, period). Prose
  already spoke in tier terms; no document change needed. All 69 tests pass.
- Two boundaries: identities need nothing from roles (a misclassified line
  can steer a driver, never unbalance a book); unresolved core driver roles
  refuse simulation.
- Naming discipline: union state space common as container; behavior layer
  common as vocabulary.
- Three practice-taught cautions: verify calc linkbases, face-only axes,
  pinned taxonomy versions.

### 8.3 Edges of the vocabulary: two worked examples **[FIX applied 2026-07-27]**

- Purpose: show what the cascade does to lines outside the validated
  sectors, and name the two kinds of coverage gap with their two different
  fixes; makes "held" and the refusal gate concrete on real economics.
- Example 1: asset retirement obligation (an oil producer).
  - Cascade trace: the US GAAP ARO concepts are not in the concept table and
    no label rule matches, so the section-and-polarity default lands the
    line in other-non-current-liability (provenance section); an IFRS filer
    presenting it inside decommissioning provisions hits the concept table
    (provision).
  - MVP behavior: the stock holds, or moves to a revenue-scaled target where
    a working-capital cash-flow line binds it; an accretion row on the cash
    flow classifies as other-non-cash and projects to zero; the capitalized
    retirement cost inside PP\&E depreciates with the capital pool.
  - Safety: not a core role, so simulation proceeds; identities never
    consult roles; the approximation is visible to the plausibility bounds
    and the accountant, never a silent corruption.
  - The proper account, a vocabulary gap: add an aro role (concept-table
    entries for both standards) plus one authored law of motion (accretion
    at the locked discount rate, settlements through the firm's own
    cash-flow line, new layers arriving with capex); written once, serving
    every energy name.
- Example 2: premiums receivable, net of allowance for credit losses (an
  insurer).
  - Cascade trace: no insurance concepts in the table; no label rule matches
    "premiums receivable"; insurers commonly present unclassified balance
    sheets, so the default lands the line in other-non-current-asset.
  - MVP behavior, and the refusal gate fires first: before the receivable
    matters, the income statement's "premiums earned" resolves to no
    revenue role, and unresolved core driver roles refuse simulation with
    the missing roles named; the insurer abstains rather than simulating on
    a misread core.
  - The proper account, a recognizer gap: premiums receivable is the
    receivable kind the vocabulary already has (it tracks premium revenue
    through its own cash-flow line, the allowance netted inside the line
    exactly as with "accounts receivable, net"); a concept-table or
    label-rule entry mapping premiums earned to revenue and premiums
    receivable to ar restores full behavior; no new role, no new law.
- The general lesson: coverage failures split into recognizer gaps (one
  mapping line into an existing role) and vocabulary gaps (a new role plus
  a new law); the defaults keep both safe meanwhile, refusal guards the
  core, and the gating set's deliberately awkward inclusions are the
  mechanism that forces such firms into the validated set.
- Sector honesty: the validation set is tech and software; sector-specific
  dynamics are designed-but-unmeasured until such filers enter the gating
  set.

## 9. The accounting engine: no plugs, no circularity

- Contract: cannot produce an unbalanced statement; nothing plugged.
  Circularity is the companion problem; every quantity computed once in an
  explicit dependency order.
- Balance polarity, flows, the balanced-flow equation; residual invariance
  derived by linearity; asserted exactly per path.
- SAP's printed two-million-euro base residual preserved to the cent; the
  operational meaning of no plugs (preserve the filer's residual, add zero).
- Period cycle in seven steps: project income leaves; working-capital
  targets through the firm's own cash-flow lines; discretionary schedule
  held at reasoned levels; close income to retained earnings; liquidity
  sweep (behavioral treasury rule, not a plug); recompute derived rows;
  assert invariants including the cash tie.
- Articulation lead: cross-statement identities hold because both sides come
  from the same flow; both standards' styles close exactly.
- Symbolic verification lead: per-firm SymPy closure proof before numerics;
  DAG order check; caught the latent NCI gap. Runtime pipeline is symbolic
  check, TensorFlow execution, numerical check.
- Auditability lead: journals, hashes, versions, seeds; bit-identical
  reruns.

## 10. The driver-to-flow layer and scenarios

- Scenario vector defined with units; MVP driver map reasoned and nonlinear,
  parameters documented, not fitted.
- Equations (5) to (7) with every symbol introduced; economics argued in
  words (inflation passes into costs faster than prices; rate sign follows
  the firm's own net cash position).
- Guardrails: tax-rate clip, dividend cap and floor, buyback halving,
  revenue floor. Common random numbers across scenarios.
- No-line inheritance defers to Section 8.1 mechanics.
- Monte Carlo in TensorFlow (batched float64, seeded, per-path residual
  checks); bit-exact Decimal replay of audit paths; 1e-10 agreement test.
- Directional battery requirements enumerated.
- Part II replaces the noise with a learned conditional joint distribution,
  keeping every other component fixed.

## 11. Validation evidence: four filers, two standards

- Provenance: reference implementation (roughly 9,000 lines, pytest, audit
  manifests); Apple, Microsoft (10-K), SAP, Spotify (20-F); three evidence
  regimes, each at its own bar.
- Extraction ablation table: 198/227/319/250, total 994/994; rule-of-three
  0.30 percent; benign categories in the caption.
- Pathologies survived on the way to zero (list); each fixed as a general
  rule; several are seeded regressions.
- Reconstruction: 1,162/1,162; SAP's sixteen demotions disclosed.
- Footing and identities: all pass within tolerance; SAP rounding reported.
- Simulation: six scenarios times 500 paths times four filers, zero
  violations on 12,000 paths; residuals preserved exactly; directional
  battery full pass; artifacts under out/acceptance; plausibility bounds
  pass.
- Untagged sweep: fourteen IR documents, five jurisdictions, five distressed
  filers; new pathology families, each now a general rule with a regression;
  footing, A = L + E, cash tie verified with no tags; structural quality
  gate refuses simulation on flagged balance-sheet cells; page location 37
  of 42 deterministic, five LLM fallbacks; the image-based English half of
  one document is the designed OCR boundary.
- Cross-year carry-forward: Microsoft FY2024 boundary case (lexicon covers
  it; deltas to the model); BBBY 2021 payoff case (26 carried choices, model
  calls 55 to 37, simulates end to end); two lessons (statement-scoped
  lexicon; carry replicates errors, sign-off is the gate).
- Foreign layouts against tags: six documents, 1,343 accepted cells, 1,316
  exact (98.0 percent); all 27 exceptions in named attribution categories;
  digits read true, attribution is the residual failure mode, feeding the
  Phase 1 worklist under the sev-1 rule; both bank balance sheets refuse
  honestly (netted presentation); mapping accuracy without tags 111 of 270,
  which is why sign-off gates simulation.
- What this de-risks: the four commitments restated with their evidence.

## 12. Testing and acceptance plan

- Four levels: unit and property tests (grammars, gate battery, injectivity,
  driver signs); golden statements; the acceptance battery as binary go/no-go
  gate; accountant review feeding new automated bounds.
- Gating set extension: roughly three filers per standard, deliberately
  awkward inclusions, one truly untagged document with hand-verified
  double-entry ground truth.
- Sev-1 rule: any accepted-cell error is a sev-1; fixes are general rules
  demonstrated by new seeded tests.

## 13. Governance, controls, and operations

- SR 11-7 mapping: documentation, methodology, lineage, developmental
  evidence, ongoing monitoring, limitations; effective challenge via
  determinism.
- BCBS 239 posture: accuracy/integrity are the gates; completeness measured;
  timeliness bounded; adaptability is the rule architecture.
- Audit trail: per-run hashes, versions, seeds, per-field provenance,
  demotion list, flow journal, verdicts; retention; inputs immutable.
- Security and licensing: runtime fully local, EDGAR-only egress; build-time
  LLM under the leash with excerpts of public documents; permissive licenses
  only; the model has no authority to accept a field alone.
- Operations: CLI stages, batch execution, minutes per filer, loud failures.

## 14. Phased build plan and timeline

- Validation build de-risks Phase 1; phases harden and extend.
- Phase 0 (2 weeks): scope lock, gating set, criteria frozen, battery into
  CI, golden statements.
  **[gap]** Candidate addition from the 2026-07 review discussion: measure
  the born-digital share of the actual target portfolio's documents, so the
  scope boundary is sized by evidence rather than judgment.
- Phase 1 (7 weeks): readers extended (vision, comparatives, untagged
  semantic mapper); carry-forward to the full set with constrained
  shortlists; adjudication UI; seeded battery to full catalogue; foreign
  layout bar extended, starting from the two attribution findings; IFRS
  hardening. Gate: extraction gates on the full set.
- Phase 2 (2 weeks): engine integration with the team's lineage; reviewed
  toggles; end-to-end demo.
- Phase 3 (3 weeks): macro layer from the external model; directional
  battery extended with accountant expectations; stochastic review.
- Hardening (4 weeks): sign-off cycles, adversarial filings, performance,
  governance documentation.
- Phase 4 (5 weeks, conditional): learned driver distributions, on sign-off.
- Timeline table and milestones (feature-complete 4 Dec 2026; sign-off 15
  Jan 2027).
  **[gap]** Post-internship ownership is not stated: who owns the sev-1
  rule, re-onboarding, and taxonomy pinning after 26 February 2027. Even one
  sentence (handover artifact, owning team) would close it.

## 15. Risk register

- Six risks with honest mitigations: uniform mis-scaling; unseen layout
  pathologies; driver realism judged insufficient; filing anomalies;
  dependence on prior interns' engine; accountant availability.
- Caption: extraction correctness deliberately absent as a risk line; it is
  the central control, gated continuously.

## 16. Open questions for alignment

- Settled list (standards scope, precision asymmetry, parity, state space,
  gate feasibility, the last by evidence).
- Open: macro model interface; reviewer and batch sizes for the accountant
  gate; which mode gates Part I acceptance (recommendation stated).

## Appendix A: one firm complete, every line wired

- Purpose: Figure 5's machinery with the elision removed for one filer;
  reading guide for the three columns, boxes, trunks, articulation.
- Generated, not drawn: script, production cascade and binder; law-of-motion
  column restates the engine dispatch; two reading notes (the close drawn
  through the cash-flow row; held marks attachment slots).
- Figure 6.

## References

- Twenty entries; every external claim in the body cites one.

---

## Candidate gaps from my first pass (beyond the inline flags)

1. Portfolio scope measurement (Phase 0 flag above): the born-digital
   boundary is defended architecturally but never sized against the bank's
   actual document population.
2. Post-internship ownership and maintenance (Section 14 flag above).
3. Build-time LLM cost and volume: the leash bounds authority but the
   proposal never states the scale of model usage onboarding incurs (calls
   per document are in the artifacts; a sentence would preempt the obvious
   review question).
4. Batch/portfolio operational shape: operations states per-filer minutes;
   a portfolio-screening use implies N-filer batches and refresh cadence;
   one sentence in Operations would connect the use case to the mechanics.

## Process note

- Verdict workflow: annotate this file (KEEP/MOVE/CUT/FIX/add), or dictate
  verdicts in conversation; changes execute surgically on the .tex,
  preserving load-bearing phrasings and the scan discipline. Delete this
  file when the review concludes.

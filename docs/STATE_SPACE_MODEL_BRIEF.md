# Financial Statement Simulator: State-Space and Forecasting Brief

**Status:** Working brief based on the current design discussion  
**Purpose:** Clarify the representation, extraction, and forecasting decisions that the Financial Statement Simulator (FSS) must resolve before expanding beyond its MVP.

## 1. Problem

The central design problem is turning an annual-report PDF (or an XBRL-tagged
filing) into a structured representation that can be advanced under economic
scenarios and decoded into a plausible future financial statement.

The phrase *state-space model* has been used for two different things:

1. **The economic state-space model.** Latent macroeconomic and firm/industry
   conditions evolve over time and drive accounting roles, which then drive
   observed line-item values.
2. **The retained statement state.** A container of line-item labels, values,
   signs, periods, units, and presentation metadata. This is a registry, not a
   latent econometric model.

The second object should be called the **accounting dictionary** (or retained
statement registry). Keeping that name separate from the economic state space
will make the architecture and its documentation unambiguous.

### Product thesis

The MVP should be narrow enough to build credibly but complete enough that a
user would care about its output. A simulator that ingests a filing but then
applies one generic revenue projection and preserves every initial sub-line
proportion is unlikely to be useful. A stronger MVP would ingest IFRS and US
GAAP luxury-goods filings, preserve economically meaningful detail, and use
macroeconomic conditions plus comparable-company evidence to produce credible
future line items.

This is the intended "iPhone 2G" standard: limited industry scope, but the core
workflow must solve a real forecasting problem end to end. If it works, the
same method becomes a blueprint for other industries.

### Stakeholder requirements

- **Chak's concern:** different accounting standards, industries, and native
  labels can describe the same economic meaning. The role-mapping layer must
  make that correspondence explicit and auditable.
- **Yifan's concern:** a firm's behavior should not be inferred only from its
  own time series. The forecast should learn from comparable firms in the same
  industry while preserving meaningful firm and sub-line differences.

## 2. Working Terminology

| Term | Meaning | Not to confuse it with |
| --- | --- | --- |
| Economic state space | Latent/common states such as GDP growth, inflation, interest rates, industry competition, and firm demand | The list of rows printed on a statement |
| Economic role | A standard-neutral economic meaning, such as revenue, receivables, inventory, or deferred/contract liabilities | A filing's exact label or XBRL QName |
| Industry state set | The roles, concepts, relationships, and drivers needed to model a particular industry | A universal list that assumes every industry has the same economics |
| Accounting dictionary | Per-statement retained values and presentation information needed for lossless reconstruction | A probabilistic model |
| Role assignment | Mapping a native line item to an economic role using concepts, labels, context, and constraints | The retired/non-standard term "behavioral layer" |
| Projection contract | Rules defining which levels are forecast independently and how totals and sub-items reconcile | A choice that can be left implicit |

The current repository design also uses a common knowledge-graph state space and
per-standard encode/decode adapters. This brief refines the open question inside
that design: the common layer may need a shared core plus industry-specific
state-set extensions rather than one flat, universal role vocabulary.

## 3. Proposed End-to-End Flow

```text
Filing (PDF and/or XBRL)
    -> extraction and validation
    -> structured statement + accounting dictionary
    -> role assignment and industry-state-set mapping
    -> economic drivers and panel/peer model
    -> accounting engine and reconciliation
    -> next-period structured statement
    -> native-standard rendering
```

The representation must preserve the distinction between:

- **Economic content:** roles, stocks, flows, drivers, and accounting
  relationships used by the simulator.
- **Native presentation:** labels, row order, signs, units, periods, and
  disclosed aggregation retained by the accounting dictionary.

Encoding may omit a subtotal only when it is an exact function of retained
components; decoding recomputes it and restores the native presentation. The
encode/decode round trip must remain lossless for the source statement.

## 4. Extraction Strategy

The MVP already has multiple extraction rungs. The runtime should use the
following ladder:

1. **XBRL/iXBRL path.** When tags are present, read the filer's tagged facts,
   including concept, dimensions, period, unit, scale, decimals, and sign.
2. **PDF line-item path.** When tags are absent or insufficient, extract the
   statement tables and line-item labels from the PDF. Use the labels,
   statement section, neighboring rows, calculation/footing constraints, and
   standard context to infer the applicable concept and role.
3. **Validation and abstention.** Redundant readers and accounting-identity
   checks must surface disagreement. An unresolved or materially ambiguous
   core row is flagged or refused; it is never silently assigned a role.

The system must not assume that every input PDF is XBRL-tagged or that every
sub-line item has a useful tag. XBRL coverage, custom extension usage, and
detail-level coverage should be measured empirically on the MVP filing set.

The extraction result should record, for every row:

- native label and displayed value;
- source standard and, when available, XBRL concept/dimensions;
- inferred economic role and industry state set;
- mapping source (concept table, taxonomy label, deterministic rule, or human
  adjudication);
- confidence, validation status, and provenance.

## 5. Industry-Specific State Sets

The current working view is that state sets should be **industry-aware**. A
single universal role vocabulary may be too coarse for industries whose
economics and liabilities differ materially.

Examples motivating this view include:

- **Insurance:** premium collection is not equivalent to immediate cash
  revenue. The model may need premium/insurance-contract liabilities,
  claims/loss reserves, policyholder-related assets, and investment income.
  The exact terminology must follow the applicable insurance standard (for
  example, "insurance contract liability" or "unearned premium" rather than
  assuming generic deferred revenue).
- **Oil and gas:** asset retirement obligations and related remediation or
  decommissioning economics require industry-specific treatment.
- **Luxury goods and retail:** product/category disclosures may require
  product revenue, inventory, markdown, wholesale/retail, or geographic
  distinctions that are not meaningful for every industry.

The preferred architecture to test is:

- a **shared core** for broadly reusable roles and accounting identities;
- **industry extensions** containing additional roles, relationships, and
  driver attachments;
- explicit mappings from each standard's concepts and each filer's labels into
  the selected industry state set;
- explicit "not equivalent" mappings where IFRS and US GAAP recognition or
  measurement differs.

This is a working hypothesis, not a final taxonomy decision. The alternative
is a fully separate role vocabulary per industry. The MVP should compare both
designs on mapping reuse, forecast quality, and the number of industry-specific
exceptions they require.

Role mapping solves nomenclature differences, not all accounting-standard
differences. For example, labels such as "trade receivables" and "accounts
receivable" can map to a receivables role, while standard-specific recognition
and measurement remain in the appropriate encode/decode adapter.

## 6. Forecasting and Cross-Sectional Modeling

The economic state-space model supplies scenario variables, for example:

- macroeconomic growth and inflation;
- interest-rate changes;
- industry competition;
- firm or industry demand shocks.

These states drive roles and flows. A useful model should retain industry and
sub-line nuance rather than applying one proportional growth rate to every
revenue row.

### Panel structure

"Cross-sectional analysis" here means a panel of firms observed over years,
not only a one-period cross-section. The intended data structure is:

```text
firm by fiscal year by industry state/role
```

The baseline should support firm effects, year effects, and cohort effects,
with lagged predictors to avoid look-ahead leakage. Peer information should be
available for all firms as a source of information, while peer borrowing is
especially valuable for firms with a short or thin history. Peer groups must
be defined by economic comparability, not merely by superficial industry
labels.

Comparability may differ by sub-line within the same firm. Apple's service or
subscription revenue could be tested against service-oriented peers such as
Google, while its hardware/product revenue could be tested against product
manufacturers such as HP. These are candidate cohorts to validate, not assumed
equivalences.

### Aggregate versus sub-line forecasts

Some sub-lines plausibly deserve independent projections:

- Apple's services revenue versus hardware/product sales;
- a comparable firm's subscription or service revenue versus product sales.

Other disclosures may be too granular, unstable, or poorly comparable for
independent estimation. For example, shoes versus clothing within a luxury
company may be better handled as an aggregate if the detail is inconsistently
reported or does not have distinct predictive drivers. Whether Chanel or
similar filers disclose and maintain that split is an empirical question.

The choice should be based on:

- distinct economic drivers or behavior;
- materiality to the user and to the statement;
- consistency of disclosure across years and peer firms;
- sufficient observations for estimation;
- comparability across standards and companies;
- improvement in out-of-sample forecast performance.

The model should support a variable-width, hierarchical state rather than
forcing every firm into the same sub-line vector. A firm that discloses only a
single revenue line can populate the aggregate role; a firm that discloses
service and product revenue can populate both children while retaining the
reported presentation.

## 7. Projection Contract: Open Design Decision

The projection contract is not yet settled. The key question is whether:

1. an aggregate is forecast first and sub-items are allocated to it;
2. sub-items are forecast independently and the aggregate is their sum; or
3. both are forecast and a reconciliation method chooses adjusted forecasts
   that satisfy the hierarchy.

The recommended research direction is **hierarchical forecasting with
reconciliation**:

- forecast economically meaningful sub-items independently when the evidence
  supports it;
- forecast at an aggregate level when detail is immaterial, unavailable, or
  statistically weak;
- reconcile all forecasts so disclosed subtotals and totals foot exactly;
- make the reconciliation and any allocation rule visible in the audit trail.

This preserves Apple's service-versus-hardware distinction without requiring
an unsupported shoes-versus-clothes model for every luxury filer. A simple
proportional split can be a fallback closure rule, but it should not be the
default where independent behavior is material and estimable.

## 8. MVP Scope

The proposed "iPhone 2G" MVP is one complete industry implementation:

- **Industry:** luxury goods;
- **Standards:** IFRS and US GAAP filers;
- **Workflow:** ingest annual-report PDFs, use XBRL when available, fall back
  to label-based PDF extraction, map rows into the luxury-goods state set,
  project under macro and industry scenarios, and render future statements in
  the source standard;
- **Output:** an auditable end-to-end blueprint that can be extended to other
  industries.

The MVP should intentionally include both tagged and untagged or incompletely
tagged examples. That makes the extraction fallback and the mapping evidence
part of the product rather than an untested assumption.

## 9. Research Agenda

### Taxonomy and accounting semantics

- Decide whether the shared-core-plus-industry-extension design is preferable
  to fully separate industry state sets.
- Define the luxury-goods role inventory and identify which roles are common to
  both IFRS and US GAAP.
- Document standard-specific recognition/measurement differences that cannot
  be represented as a simple synonym mapping.
- Measure XBRL coverage at face-statement and sub-line levels across the sample;
  catalog custom extensions and recurring untagged labels.

### Forecast granularity and reconciliation

- Build a hierarchy for aggregate revenue and disclosed sub-lines.
- Compare aggregate-only, independent sub-line, proportional-allocation, and
  reconciled forecasts using rolling out-of-sample tests.
- Define materiality and minimum-observation thresholds for promoting a
  sub-line to independent treatment.
- Decide whether the aggregate is authoritative, the leaves are authoritative,
  or reconciliation is the authoritative projection contract.

### Panel and peer methodology

- Establish the baseline panel specification: firm effects, year/cohort
  effects, lag structure, industry-year peer features, and clustered standard
  errors.
- Test peer definitions and cold-start behavior without using future
  information.
- Compare a conventional panel model with repeated cross-sectional methods
  where appropriate.
- Report uncertainty and calibration, not only point forecasts.

## 10. Suggested Canonical Materials

- Hyndman and Athanasopoulos, *Forecasting: Principles and Practice*, chapters
  on hierarchical/grouped forecasting and forecast reconciliation.
- Wickramasuriya, Athanasopoulos, and Hyndman, "Optimal Forecast
  Reconciliation Through Trace Minimization" (MinT).
- Wooldridge, *Econometric Analysis of Cross Section and Panel Data*, for
  fixed effects, random effects, dynamic panels, and specification choices.
- Fama and MacBeth (1973), for the canonical repeated cross-sectional
  regression framework. It is useful background, but is not identical to the
  proposed firm-by-year forecasting panel.
- Petersen, "Estimating Standard Errors in Finance Panel Data Sets," for
  firm and time clustering practice in finance.
- IFRS 8 and ASC 280, for operating-segment disclosure and aggregation logic.
- IAS 1, SEC Regulation S-X, and relevant insurance/oil-and-gas guidance, for
  presentation, aggregation, materiality, and industry-specific disclosures.

## 11. Immediate Next Steps

1. Select a small luxury-goods filing set with both standards and varied
   disclosure detail.
2. Create a mapping inventory with columns for native label, standard, XBRL
   concept (if any), role, industry state, parent/aggregate, source, and
   confidence.
3. Quantify tagging and disclosure persistence for every candidate sub-line.
4. Implement an aggregate baseline and at least one independent sub-line
   model, then evaluate reconciled forecasts out of sample.
5. Record the chosen taxonomy and projection contract in the design record
   only after those tests provide evidence.

## Executive Summary

The simulator should separate a latent economic state-space model from the
accounting dictionary that preserves each statement's native rows. Extraction
should prefer XBRL but must fall back to validated PDF label mapping. The
working taxonomy direction is a shared core plus industry-specific state sets,
with explicit standard adapters. Forecasts should use firm-by-year panel data,
macroeconomic states, and economically meaningful peer information. The main
open design decision is forecast granularity and reconciliation; hierarchical
forecasting is the recommended framework to study. Luxury goods across IFRS
and US GAAP is the proposed end-to-end MVP and blueprint for expansion.

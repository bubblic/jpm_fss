# Prompt for Claude Code

Read CLAUDE.md first; it has the project context, Arelle API hints, SEC
etiquette rules, and the tolerance rule. Then implement this spike.

## Goal

Prove, on one real filing, that a knowledge-graph encoding of financial
statements works mechanically: load the US GAAP taxonomy as a graph, overlay
Apple's latest 10-K balance sheet onto it, verify the arithmetic, and
demonstrate a perfect round trip from (values, presentation map) back to the
native statement rows.

## Deliverables

1. **Fetch** (`python -m spike.fetch`): resolve Apple's most recent 10-K via
   the EDGAR submissions API, download the primary inline-XBRL document (and
   let Arelle pull the DTS), cache everything under `data/`.

2. **Graph** (`src/spike/graph.py`): load the filing with Arelle, build a
   networkx DiGraph over the discovered taxonomy:
   - nodes = concepts, with attrs: qname, periodType, balance, isMonetary,
     standard label;
   - edges = calculation arcs (merge calc 1.0 and 1.1), with attr weight.
   Export `out/graph.graphml` and report counts: concepts, calc edges,
   labeled concepts, plus a 5-concept sample table of (qname, periodType,
   balance).

3. **Overlay** (`src/spike/overlay.py`): restrict to the consolidated balance
   sheet role. Using the presentation linkbase for row order and the
   calculation arcs for structure, build:
   - `z`: dict of LEAF concept -> reported value (facts in the default
     context for the latest balance-sheet date; skip dimensioned facts and
     note how many were skipped);
   - derived set: concepts that are calc parents on this statement (subtotals
     and totals), excluded from `z`;
   - `m`: ordered list of rows with native label (honoring preferredLabel,
     including negated-label sign flips), concept qname, leaf/derived flag,
     and displayed sign convention.
   Company extension concepts (namespace != us-gaap): keep them, record their
   calc parent as the anchor, and count them.
   Write `out/overlay.json` with z, m, and the derived set.

4. **Checks** (`src/spike/checks.py`):
   - Footing: every derived concept's value equals the weighted sum of its
     calc children present on the statement, within the decimals-based
     tolerance from CLAUDE.md. Report each subtotal: computed vs reported vs
     diff vs pass/fail.
   - Identity: Assets = Liabilities + Equity (use the reported totals; state
     which concepts you matched for each side).
   - Coverage: fraction of face-of-statement lines that resolved to a concept
     with both periodType and balance populated (target >= 95%); every
     balance-sheet concept should be periodType == instant, report any that
     are not.

5. **Round trip** (`src/spike/roundtrip.py`): regenerate the balance sheet
   rows purely from (z, m) plus the calc arcs (recompute derived values; do
   NOT read them from the filing), and diff (label, displayed value, order)
   against the natively extracted rows. Target: exact match on every row.

6. **Report** (`python -m spike.report`, writes `out/report.md`): one page a
   reviewer can read in five minutes. Sections: What was tested; Graph stats;
   Overlay summary (rows, leaves, derived, extensions, dimensioned facts
   skipped); Check results (tables); Round-trip result; **Findings and
   limitations** (every surprise: negated labels hit, calc inconsistencies,
   missing anchors, role-selection ambiguity, anything skipped). End with a
   3-bullet "what this de-risks for the full build".

## Acceptance criteria

- `make all` (or the two entry points) runs end-to-end from a clean clone
  with only `SEC_USER_AGENT` set.
- Balance sheet foots: all subtotal checks pass within tolerance.
- A = L + E passes.
- >= 95% of face lines resolve with periodType + balance populated.
- Round trip reproduces every native row exactly (label, value, order).
- `out/report.md`, `out/overlay.json`, `out/graph.graphml` exist and are
  self-explanatory.

## Ground rules

- Follow CLAUDE.md's SEC etiquette and caching rules exactly.
- Timebox per CLAUDE.md: a documented blocker in the report is an acceptable
  outcome; silent fudging is not. Never hard-code a number to make a check
  pass.
- Work in small commits if git is initialized; otherwise just keep the module
  layout clean.

Start by writing a short plan (5-8 bullets) into `out/plan.md`, then build.

# KG encoding spike: Apple 10-K balance sheet

Filing: Apple Inc., form 10-K, accession 000032019325000079, filed 2025-10-31, period 2025-09-27. Statement role: 9952153 - Statement - CONSOLIDATED BALANCE SHEETS. Balance-sheet date used: 2025-09-27.

## What was tested

1. The US GAAP taxonomy discovered from the filing loads as a directed graph carrying periodType (stock/flow), balance (sign convention), monetary flags, labels, and weighted calculation arcs.
2. The filing's consolidated balance sheet resolves onto that graph as a firm overlay: z holds leaf values, m holds the ordered presentation map.
3. The overlay foots: every subtotal equals the weighted sum of its calc children within the decimals-based rounding tolerance, and Assets = Liabilities + Equity.
4. A round trip from (z, m) plus the calc arcs regenerates the native statement rows (label, displayed value, order) without reading derived values from the filing.

## Graph stats

- Concepts (nodes): 18,697
- Calculation edges (calc 1.0 + 1.1 merged): 213 (a filing DTS carries the filing's own calculation linkbase; the standard taxonomy's template calc networks are not part of it)
- Concepts with a standard label in this DTS: 700 (labels ride with the filing's linkbases, which only cover concepts the filing uses; the rest of the taxonomy still resolves structurally)

| Concept | periodType | balance |
| --- | --- | --- |
| `us-gaap:Assets` | instant | debit |
| `us-gaap:Liabilities` | instant | credit |
| `us-gaap:StockholdersEquity` | instant | credit |
| `us-gaap:CashAndCashEquivalentsAtCarryingValue` | instant | debit |
| `us-gaap:AccountsPayableCurrent` | instant | credit |

## Overlay summary

- Statement linkrole: `http://www.apple.com/role/CONSOLIDATEDBALANCESHEETS`
- Rows in m: 38 (30 face lines, 8 abstract headers)
- Leaves in z: 21
- Derived (calc parents, excluded from z): 8
- Company extension concepts: 0
- Dimensioned facts skipped: 42 at the balance-sheet date, 100 across all dates
- Face rows without a value at the date: 1

## Check results

### Footing (subtotal = weighted sum of calc children)

| Subtotal | Children | Computed | Reported | Diff | Tolerance | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Total current assets (`us-gaap:AssetsCurrent`) | 6 | 147,957,000,000 | 147,957,000,000 | 0 | 3,500,000 | PASS |
| Total non-current assets (`us-gaap:AssetsNoncurrent`) | 3 | 211,284,000,000 | 211,284,000,000 | 0 | 2,000,000 | PASS |
| Total assets (`us-gaap:Assets`) | 2 | 359,241,000,000 | 359,241,000,000 | 0 | 1,500,000 | PASS |
| Total current liabilities (`us-gaap:LiabilitiesCurrent`) | 5 | 165,631,000,000 | 165,631,000,000 | 0 | 3,000,000 | PASS |
| Total non-current liabilities (`us-gaap:LiabilitiesNoncurrent`) | 2 | 119,877,000,000 | 119,877,000,000 | 0 | 1,500,000 | PASS |
| Total liabilities (`us-gaap:Liabilities`) | 2 | 285,508,000,000 | 285,508,000,000 | 0 | 1,500,000 | PASS |
| Total shareholders’ equity (`us-gaap:StockholdersEquity`) | 3 | 73,733,000,000 | 73,733,000,000 | 0 | 2,000,000 | PASS |
| Total liabilities and shareholders’ equity (`us-gaap:LiabilitiesAndStockholdersEquity`) | 2 | 359,241,000,000 | 359,241,000,000 | 0 | 1,500,000 | PASS |

8 of 8 subtotal checks pass.

### Identity: Assets = Liabilities + Equity

- Matched concepts: assets `us-gaap:Assets`, liabilities `us-gaap:Liabilities`, equity `us-gaap:StockholdersEquity`
- 359,241,000,000 vs 285,508,000,000 + 73,733,000,000: diff 0, tolerance 1,500,000: PASS
- cross-check: reported us-gaap:LiabilitiesAndStockholdersEquity minus Assets = 0

### Coverage

- Strict, all face lines: 28 of 30 resolve to a concept with both periodType and balance populated: 93.3% (target 95%): FAIL
- Monetary face lines only: 28 of 28: 100.0%: PASS (balance is only defined for monetary concepts; see findings)
- Non-instant face concepts: none

## Round trip

- 38 of 38 rows match exactly on (label, displayed value, order): PASS
- Derived values were recomputed from z through the calc arcs; reported subtotals were not read back from the filing. Labels and order come from m, which is what the encoding stores.

## Findings and limitations

1. Role selection needed care: the text heuristic matched 18 linkroles, but 17 of them are template roles that ship inside the us-gaap taxonomy itself (for example "104000 - Statement - Statement of Financial Position, Classified"). Restricting to roles defined by the filing's own schema left exactly one. A production loader should always filter to filing-defined roles before matching on definitions.
2. No negated preferred labels occur on this statement, so the sign-flip handling in m is implemented but was not exercised by this filing.
3. Calculation arcs found under arcrole(s): http://www.xbrl.org/2003/arcrole/summation-item. Calc 1.0 and calc 1.1 sets were merged; no conflicting weights between them.
4. No company extension concepts appear on this statement; every row is a standard us-gaap concept.
5. Dimensioned facts skipped: 42 at the balance-sheet date (100 across all instant dates for these concepts). These are member-level breakdowns (for example equity by component) that belong to other statements or notes; the face of the balance sheet uses only undimensioned facts here.
6. Arelle logged 29 facts filing-wide with an unrecognized transformation namespace (the SEC-specific registry http://www.sec.gov/inlineXBRL/transformation/2015-08-31, which plain Arelle does not register without the EDGAR plugin). None of them is a balance-sheet fact; they are cover-page booleans, small integer counts, and duration strings.
7. Face rows with no undimensioned fact value at the balance-sheet date: `us-gaap:CommitmentsAndContingencies`. Typically these are nil-valued rows such as commitments and contingencies; they carry no amount and drop out of z.
8. Footing sums skipped calc children without values: `us-gaap:CommitmentsAndContingencies` (consistent with the nil rows above).
9. Every face concept is periodType instant, as a balance sheet requires; the stock/flow attribute behaves as the state-space encoding assumes.
10. The strict coverage metric counts non-monetary face rows: `us-gaap:CommonStockSharesOutstanding`, `us-gaap:CommonStockSharesIssued` are share counts, and XBRL defines the balance attribute only for monetary items, so such rows can never satisfy the strict metric. On monetary lines alone, coverage is 100.0%. The full build should track the two bases separately.
11. Scope: the overlay covers the latest column of the statement only. The prior-year column is present in the filing and would need a second z vector; nothing in the encoding prevents that.

## What this de-risks for the full build

- The common state space is real: one taxonomy graph carries the attributes the simulator needs (stock vs flow, sign convention, calc structure), and a real filing lands on it without manual mapping.
- The arithmetic layer is trustworthy: subtotal footing and the accounting identity hold within stated rounding, so simulated deltas to z can be re-aggregated mechanically through the same arcs.
- Values and presentation separate cleanly: (z, m) reproduces the native statement exactly, so a simulator can mutate z alone and re-render statements without touching presentation logic.

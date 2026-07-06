# Spike plan

1. **Fetch with cache**: `spike.fetch` resolves Apple's latest 10-K from the
   EDGAR submissions API (form == "10-K", newest accession), downloads the
   primary inline-XBRL .htm plus the co-located extension files (.xsd,
   _cal/_def/_lab/_pre.xml) into `data/filings/<accession>/`, always sending
   `SEC_USER_AGENT` and skipping anything already cached. It also warms
   Arelle's web cache (under `data/arelle_cache/`) once so the DTS download
   happens in the fetch step; later loads run offline.
2. **Graph**: `spike.graph` loads the cached filing with Arelle, builds a
   networkx DiGraph (nodes = DTS concepts with qname, periodType, balance,
   isMonetary, standard label; edges = calc 1.0 + 1.1 arcs with weight),
   exports `out/graph.graphml`, and reports counts plus a 5-concept sample.
3. **Overlay**: `spike.overlay` picks the consolidated balance sheet linkrole
   (definition contains "balance sheet"/"statement of financial position",
   has "Statement", not "Parenthetical"), walks parentChild in `rel.order`
   order to build `m` (label honoring preferredLabel, negated-label sign
   flips, leaf/derived/abstract kind), selects undimensioned facts at the
   latest instant for `z` (leaves only), counts skipped dimensioned facts and
   extension concepts with their calc-parent anchors.
4. **Checks**: `spike.checks` foots every derived concept against the
   weighted sum of its on-statement calc children using the decimals-based
   tolerance (0.5 * 10^-decimals * (n_children + 1)), verifies
   Assets = Liabilities + Equity from reported totals, and measures coverage
   (periodType + balance populated; everything should be instant).
5. **Round trip**: `spike.roundtrip` recomputes derived values purely from
   (z, m) plus calc arcs, renders rows (label, displayed value, order), and
   diffs them against the natively extracted rows; target is an exact match.
6. **Report**: `spike.report` orchestrates fetch -> load -> graph -> overlay
   -> checks -> roundtrip and writes `out/report.md` (stats, check tables,
   round-trip result, findings and limitations, what this de-risks),
   `out/overlay.json`, and `out/graph.graphml`.
7. **Guardrails**: pathlib everywhere, no network outside the fetch step
   (Arelle runs with its cache in offline mode afterwards), nothing
   hand-coded from the filing, every surprise logged into the report.
8. **Validate on Windows**: run `python -m spike.fetch` then
   `python -m spike.report` with `$env:PYTHONPATH = "src"`, confirm all
   acceptance criteria or document blockers, commit in small steps.

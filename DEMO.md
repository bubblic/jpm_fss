# Demonstration: LLMs at build time, determinism at run time

This walkthrough demonstrates the build/runtime control on real annual
reports: a hosted LLM participates only during onboarding (build time), where
its proposals are constrained, recorded, and frozen into a reviewable mapping
artifact. The runtime path is reviewed code plus that signed artifact, logs
the hashes it ran under, replays bit-exactly, and abstains on drift instead of
consulting an LLM. Deterministic replay proves reproducibility of a reviewed
choice; it does not by itself prove that the semantic concept choice was
correct.

```
BUILD TIME (change management)              RUN TIME (production path)
--------------------------------            --------------------------------
fss onboard <pdf>                           fss runtime <pdf>
  PDF -> locate/extract/check                 PDF -> SHA256 gate vs artifact
  LLM proposes:                               locate/extract from artifact
    - statement pages (fallback)              adjudications replayed ONLY if
    - flagged-cell readings (voted)             a reader still reads the same
    - concept choices (shortlist)               value (artifact cannot inject)
  every proposal mechanically constrained:    concept map from artifact
    density bar / reader agreement            all checks re-run (footing,
    / polarity veto / footing                   A=L+E, cash tie, quality gate)
  -> artifacts/mappings/<doc>.json            symbolic closure + TF Monte
     (versioned; PENDING SIGN-OFF)              Carlo when the gates pass
  human signs off ----------------->        standard + sign-off gate
                                              semantic-readiness refusal gate
                                            NO LLM CLIENT IS EVER CONSTRUCTED
```

The commands below document the workflow. The acceptance report validates the
numeric and accounting controls; concept-level correctness remains subject to
the mapping audit described in the proposal.

Legacy artifacts in this repository predate the declared-standard and enforced
sign-off fields. They remain evidence from earlier prototype runs, but they are
not eligible runtime inputs under the hardened gate: each must be rebuilt,
audited, and signed. Wrong-standard entries are rejected at the artifact
boundary even when a lexical hit could otherwise mask the stale entry.

## 1. Build step (LLM allowed, audited)

```powershell
$env:PYTHONPATH = "src"
python -m fss onboard previous_llm_extractor\annual_reports\for_financial_statements\bbby\ar2022.pdf
```

The run used the live DeepSeek API (`deepseek-v4-flash`), made its
(capped, audited) calls — page-identification fallback for the cash flow,
median-voted cell adjudications, concept mapping over lexical shortlists —
and wrote the mapping artifact:

```
artifacts/mappings/bbby_ar2022.json
{
 "document": "bbby_ar2022",
 "source_sha256": "1c0493f0331effa2009b98f64cae9988b11b5b6ae635a258c0d15d52bf481d25",
 "code_version": "f798bfc",
 "approved_by": "PENDING SIGN-OFF",
 "statements": { "balance_sheet": { "pages": [66, 67], "mapping": [...], ... } }
}
```

The onboarding report (`out/untagged/bbby_ar2022/report.md`) shows what the
LLM was consulted for and what the validators accepted; the full
call-by-call record is `out/untagged/bbby_ar2022/audit_llm.json`.

## 2. Sign-off (the human gate)

The artifact is a small, readable JSON: page locations, label-to-concept
choices with balance polarity, and cell adjudications. Review it and set

```json
"approved_by": "PENDING SIGN-OFF"   ->   "approved_by": "J. Chung, 2026-07-22"
```

The runtime stamps this field into every report it produces, so an
unapproved artifact is visible in the output trail.

## 3. Runtime step (no LLM in the inference path)

```powershell
python -m fss runtime previous_llm_extractor\annual_reports\for_financial_statements\bbby\ar2022.pdf
```

`fss runtime` never constructs an LLM client — the guard is structural
(mode == "runtime" skips client creation entirely), not an environment
accident. The report header states the terms it ran under:

```
# Runtime report (deterministic inference path): bbby_ar2022
Source SHA256: `1c0493f0...bf481d25`
LLM assist: FORBIDDEN in this mode (no model in the inference path)
Mapping artifact: `artifacts/mappings/bbby_ar2022.json` (approved by: ...; built at code f798bfc)
...
LLM calls: 0 (runtime mode; replay is bit-exact given the same source, artifact, and code versions)
```

The archived Microsoft runtime report shows the earlier deterministic replay:
`accepted cells 68, flags 0, artifact-adjudicated 2`.
the two flagged share-par cells are resolved by replaying the signed
values, accepted only because a deterministic reader still reads exactly
those values today. Both Microsoft and BBBY clear every gate at runtime
and run the full six-scenario TensorFlow Monte Carlo with zero identity
violations.

## 4. Determinism proof

Two independent runtime executions over Microsoft and BBBY, hashing every
produced file (outcomes, reports, statement JSONs):

```
files compared: 12; differing: 0
```

Same source + same artifact + same code = the same bytes. That is the
model-approval property: any historical output, right or wrong, replays
exactly.

## 5. Drift refusal

Appending a single byte to a copy of the BBBY PDF and running the runtime
against it:

```
# Runtime report (deterministic inference path): bbby_ar2022
- FAILED: source hash mismatch: the document changed since onboarding;
  re-onboarding and sign-off required
```

The runtime abstains and routes back to change management. It never
guesses and never phones an LLM.

## 6. The whole fleet, both modes

`out/untagged/summary.md` is the build sweep (LLM-assisted, audited);
`out/runtime/summary.md` is the same 14 documents through the
then-current deterministic runtime, reproducing the build results, with the
same statements, same checks, same two simulations (Microsoft, BBBY), and
**zero** LLM calls. Under the hardened gate described above, these legacy
artifacts now refuse until they are rebuilt, audited, and signed.

## A field note worth telling the director

Between the build runs and this demonstration, the original hosted
endpoint began returning `HTTP 403` — the exact "hosted endpoints change
silently" failure mode the proposal cites as the reason LLMs cannot sit in
the inference path. Nothing in production would have noticed: the mapping
artifacts were reconstructed from the committed build products
(`fss onboard --rebuild`, no LLM calls), and the runtime is indifferent
to the endpoint's existence. The build path was then re-verified live on
the replacement API (direct DeepSeek, `deepseek-v4-flash`).

## Command reference

| Step | Command |
| --- | --- |
| Build (LLM, audited) | `python -m fss onboard <pdf-or-folder>` |
| Rebuild artifacts from committed build products | `python -m fss onboard --rebuild <pdf-or-folder>` |
| Sign off | edit `artifacts/mappings/<doc>.json` -> `approved_by` |
| Runtime (deterministic) | `python -m fss runtime <pdf-or-folder>` |
| Summaries | `python -m fss untagged --merge` / `python -m fss runtime --merge` |

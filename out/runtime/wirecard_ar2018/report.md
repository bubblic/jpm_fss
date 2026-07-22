# Runtime report (deterministic inference path): wirecard_ar2018

Source: `previous_llm_extractor\annual_reports\for_financial_statements\wirecard\ar2018.pdf`  
Source SHA256: `b3f1151fd4ff3aa004a5fe1e08f5f7808b816d0683c7a056412f5928db3f0fd1`  
LLM assist: FORBIDDEN in this mode (no model in the inference path)  
Mapping artifact: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\artifacts\mappings\wirecard_ar2018.json` (approved by: PENDING SIGN-OFF; built at code f798bfc)  

**Diagnosis:** 104 text-bearing pages (e.g. pages 32-222) extract with ZERO digits: their fonts lack unicode mappings for numerals, so no text engine can read numbers there. If the statements live in that region, any rows extracted elsewhere are condensed summaries, not the statement face; an OCR/vision reader is required.

## balance_sheet

- pages [76] (artifact), 6 rows x 2 columns, scale 1000000
- accepted cells 10, flags 1
- footing: 0 verified groups, PASS
- A = L + E: N/A (no 'Total assets' row)
- concept mapping: 1 lexical, 3 artifact, 0 LLM, 2 unmapped

## income_statement

- pages [72] (artifact), 13 rows x 2 columns, scale 1000000
- accepted cells 20, flags 3, artifact-adjudicated 1
- footing: 1 verified groups, PASS
- concept mapping: 1 lexical, 5 artifact, 0 LLM, 7 unmapped

## cash_flow

- pages [72] (artifact), 13 rows x 2 columns, scale 1000000
- accepted cells 20, flags 3, artifact-adjudicated 1
- footing: 1 verified groups, PASS
- cash tie: N/A (no beginning/ending cash rows)
- concept mapping: 1 lexical, 5 artifact, 0 LLM, 7 unmapped

## Simulation

- skipped: 1 flagged balance-sheet cells (adjudication required before simulation)

LLM calls: 0 (runtime mode; replay is bit-exact given the same source, artifact, and code versions)
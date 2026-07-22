# Runtime report (deterministic inference path): lvmh_dec_2024

Source: `previous_llm_extractor\annual_reports\for_financial_statements\lvmh_dec_2024.pdf`  
Source SHA256: `57f976f7e1d1d16d39dd5b6a8df1e290e19ac3668dd758722412aaefd33e8103`  
LLM assist: FORBIDDEN in this mode (no model in the inference path)  
Mapping artifact: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\artifacts\mappings\lvmh_dec_2024.json` (approved by: PENDING SIGN-OFF; built at code f798bfc)  

## balance_sheet

- pages [26] (artifact), 32 rows x 3 columns, scale 1
- accepted cells 96, flags 22
- footing: 2 verified groups, FAIL
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 12 lexical, 19 artifact, 0 LLM, 1 unmapped

## income_statement

- pages [24, 25] (artifact), 42 rows x 3 columns, scale 1000000
- accepted cells 121, flags 11
- footing: 9 verified groups, FAIL
- concept mapping: 5 lexical, 18 artifact, 0 LLM, 19 unmapped

## cash_flow

- pages [28] (artifact), 34 rows x 4 columns, scale 1000000
- accepted cells 113, flags 0
- footing: 7 verified groups, FAIL
- cash tie: N/A (no net-change row or activity totals)
- concept mapping: 3 lexical, 22 artifact, 0 LLM, 9 unmapped

## Simulation

- skipped: 22 flagged balance-sheet cells; balance_sheet footing unverified; cash_flow footing unverified; income_statement footing unverified (adjudication required before simulation)

LLM calls: 0 (runtime mode; replay is bit-exact given the same source, artifact, and code versions)
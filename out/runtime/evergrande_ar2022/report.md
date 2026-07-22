# Runtime report (deterministic inference path): evergrande_ar2022

Source: `previous_llm_extractor\annual_reports\for_financial_statements\evergrande\ar2022.pdf`  
Source SHA256: `0432019428b560b52598743075094af865854d5034492ffd1883d8a220535191`  
LLM assist: FORBIDDEN in this mode (no model in the inference path)  
Mapping artifact: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\artifacts\mappings\evergrande_ar2022.json` (approved by: PENDING SIGN-OFF; built at code f798bfc)  

## balance_sheet

- pages [46, 47] (artifact), 13 rows x 2 columns, scale 1000000
- accepted cells 26, flags 8
- footing: 4 verified groups, FAIL
- A = L + E: N/A (no 'Total assets' row)
- concept mapping: 4 lexical, 4 artifact, 0 LLM, 5 unmapped

## income_statement

- pages [48, 49] (artifact), 34 rows x 2 columns, scale 1
- accepted cells 60, flags 21, artifact-adjudicated 5
- footing: 9 verified groups, FAIL
- concept mapping: 4 lexical, 22 artifact, 0 LLM, 8 unmapped

## cash_flow

- pages [52, 53] (artifact), 34 rows x 2 columns, scale 1000000
- accepted cells 63, flags 1
- footing: 3 verified groups, FAIL
- cash tie: PASS (begin 5435 + change -1103 (net-change row, fx added) vs end 4334)
- concept mapping: 4 lexical, 23 artifact, 0 LLM, 7 unmapped

## Simulation

- skipped: 8 flagged balance-sheet cells; balance_sheet footing unverified; cash_flow footing unverified; income_statement footing unverified (adjudication required before simulation)

LLM calls: 0 (runtime mode; replay is bit-exact given the same source, artifact, and code versions)
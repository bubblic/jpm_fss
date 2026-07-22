# Runtime report (deterministic inference path): exxon_2024

Source: `previous_llm_extractor\annual_reports\for_financial_statements\exxon_2024.pdf`  
Source SHA256: `00ae54024a75b1b270d876f0a17120be3e1da35334373ad112c8898d2fca7c5e`  
LLM assist: FORBIDDEN in this mode (no model in the inference path)  
Mapping artifact: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\artifacts\mappings\exxon_2024.json` (approved by: PENDING SIGN-OFF; built at code f798bfc)  

## balance_sheet

- pages [87, 88] (artifact), 57 rows x 3 columns, scale 1000000
- accepted cells 146, flags 12
- footing: 4 verified groups, PASS
- A = L + E: N/A (no combined or component totals)
- concept mapping: 7 lexical, 14 artifact, 0 LLM, 36 unmapped

## income_statement

- pages [85] (artifact), 20 rows x 3 columns, scale 1000000
- accepted cells 60, flags 8
- footing: 3 verified groups, FAIL
- concept mapping: 0 lexical, 10 artifact, 0 LLM, 10 unmapped

## cash_flow

- pages [88] (artifact), 35 rows x 3 columns, scale 1000000
- accepted cells 101, flags 4
- footing: 3 verified groups, PASS
- cash tie: FAIL (begin 31568 + change -7705 (activity totals, fx added) vs end 23187)
- concept mapping: 0 lexical, 15 artifact, 0 LLM, 20 unmapped

## Simulation

- skipped: 12 flagged balance-sheet cells; income_statement footing unverified (adjudication required before simulation)

LLM calls: 0 (runtime mode; replay is bit-exact given the same source, artifact, and code versions)
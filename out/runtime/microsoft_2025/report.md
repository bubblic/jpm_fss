# Runtime report (deterministic inference path): microsoft_2025

Source: `previous_llm_extractor\annual_reports\for_financial_statements\microsoft_2025.pdf`  
Source SHA256: `4793f36c40be9d078b9508e291587e947c0e3c819a82f455a8e0a2715998c7a9`  
LLM assist: FORBIDDEN in this mode (no model in the inference path)  
Mapping artifact: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\artifacts\mappings\microsoft_2025.json` (approved by: PENDING SIGN-OFF; built at code f798bfc)  

## balance_sheet

- pages [38] (artifact), 34 rows x 2 columns, scale 1000000
- accepted cells 68, flags 0, artifact-adjudicated 2
- footing: 7 verified groups, PASS
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 34 lexical, 0 LLM, 0 unmapped

## income_statement

- pages [36] (artifact), 19 rows x 3 columns, scale 1000000
- accepted cells 57, flags 0
- footing: 6 verified groups, PASS
- concept mapping: 15 lexical, 0 LLM, 4 unmapped

## cash_flow

- pages [39] (artifact), 34 rows x 3 columns, scale 1000000
- accepted cells 102, flags 0
- footing: 4 verified groups, PASS
- cash tie: PASS (begin 18315 + change 11927 (net-change row, fx inside change) vs end 30242)
- concept mapping: 34 lexical, 0 LLM, 0 unmapped

## Simulation

- symbolic closure: PROVEN
- baseline: mean net income 112,871M (identity violations 0)
- expansion: mean net income 118,220M (identity violations 0)
- recession: mean net income 104,794M (identity violations 0)
- competition: mean net income 108,618M (identity violations 0)
- rate_hike: mean net income 113,495M (identity violations 0)
- inflation: mean net income 111,643M (identity violations 0)

LLM calls: 0 (runtime mode; replay is bit-exact given the same source, artifact, and code versions)
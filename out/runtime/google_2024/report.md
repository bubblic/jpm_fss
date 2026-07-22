# Runtime report (deterministic inference path): google_2024

Source: `previous_llm_extractor\annual_reports\for_financial_statements\google_2024.pdf`  
Source SHA256: `745700dad59d69a137d705194b7944c91dc1fb1d5de6b3866df0da7db9cee2d6`  
LLM assist: FORBIDDEN in this mode (no model in the inference path)  
Mapping artifact: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\artifacts\mappings\google_2024.json` (approved by: PENDING SIGN-OFF; built at code f798bfc)  

## balance_sheet

- pages [57] (artifact), 26 rows x 2 columns, scale 1000000
- accepted cells 51, flags 1, artifact-adjudicated 1
- footing: 5 verified groups, PASS
- A = L + E: N/A (no combined or component totals)
- concept mapping: 15 lexical, 6 artifact, 0 LLM, 5 unmapped

## income_statement

- pages [58] (artifact), 13 rows x 3 columns, scale 1000000
- accepted cells 39, flags 0
- footing: 3 verified groups, PASS
- concept mapping: 7 lexical, 2 artifact, 0 LLM, 4 unmapped

## cash_flow

- pages [61] (artifact), 34 rows x 3 columns, scale 1000000
- accepted cells 99, flags 2
- footing: 5 verified groups, PASS
- cash tie: PASS (begin 20945 + change 934 (net-change row, fx inside change) vs end 21879)
- concept mapping: 12 lexical, 17 artifact, 0 LLM, 5 unmapped

## Simulation

- skipped: 1 flagged balance-sheet cells (adjudication required before simulation)

LLM calls: 0 (runtime mode; replay is bit-exact given the same source, artifact, and code versions)
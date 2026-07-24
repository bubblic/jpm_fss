# Runtime report (deterministic inference path): microsoft_2024

Source: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\data\carry\microsoft_2024.pdf`  
Source SHA256: `15fe53f0e0fbb4e604207646ab6db5ac1fa2e2bd0d346b5e88798d4f247dc3e6`  
LLM assist: FORBIDDEN in this mode (no model in the inference path)  
Mapping artifact: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\artifacts\mappings\microsoft_2024.json` (approved by: PENDING SIGN-OFF; built at code 7192cce)  

## balance_sheet

- pages [82] (artifact), 34 rows x 2 columns, scale 1000000
- accepted cells 68, flags 1
- footing: 7 verified groups, PASS
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 34 lexical, 0 LLM, 0 unmapped

## income_statement

- pages [80] (artifact), 19 rows x 3 columns, scale 1000000
- accepted cells 57, flags 0
- footing: 6 verified groups, PASS
- concept mapping: 15 lexical, 0 LLM, 4 unmapped

## cash_flow

- pages [84] (artifact), 34 rows x 3 columns, scale 1000000
- accepted cells 102, flags 0
- footing: 4 verified groups, PASS
- cash tie: PASS (begin 34704 + change -16389 (net-change row, fx inside change) vs end 18315)
- concept mapping: 31 lexical, 3 artifact, 0 LLM, 0 unmapped

## Simulation

- skipped: 1 flagged balance-sheet cells (adjudication required before simulation)

LLM calls: 0 (runtime mode; replay is bit-exact given the same source, artifact, and code versions)
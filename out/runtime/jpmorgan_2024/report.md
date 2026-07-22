# Runtime report (deterministic inference path): jpmorgan_2024

Source: `previous_llm_extractor\annual_reports\for_financial_statements\jpmorgan_2024.pdf`  
Source SHA256: `78443e60b3188a70673ca7042d0bf9e4dc596d04072af729242886d22bd0a4e3`  
LLM assist: FORBIDDEN in this mode (no model in the inference path)  
Mapping artifact: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\artifacts\mappings\jpmorgan_2024.json` (approved by: PENDING SIGN-OFF; built at code f798bfc)  

## balance_sheet

- pages [208] (artifact), 40 rows x 2 columns, scale 1000000
- accepted cells 78, flags 1
- footing: 6 verified groups, PASS
- A = L + E: FAIL (assets vs combined right-hand total)
- concept mapping: 5 lexical, 12 artifact, 0 LLM, 23 unmapped

## income_statement

- pages [206] (artifact), 30 rows x 3 columns, scale 1000000
- accepted cells 90, flags 0
- footing: 3 verified groups, FAIL
- concept mapping: 2 lexical, 12 artifact, 0 LLM, 16 unmapped

## cash_flow

- pages [210] (artifact), 46 rows x 3 columns, scale 1000000
- accepted cells 131, flags 0
- footing: 3 verified groups, FAIL
- cash tie: PASS (begin 624151 + change -154834 (net-change row, fx inside change) vs end 469317)
- concept mapping: 4 lexical, 16 artifact, 0 LLM, 26 unmapped

## Simulation

- skipped: 1 flagged balance-sheet cells; A = L + E failed; cash_flow footing unverified; income_statement footing unverified (adjudication required before simulation)

LLM calls: 0 (runtime mode; replay is bit-exact given the same source, artifact, and code versions)
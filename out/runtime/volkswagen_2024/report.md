# Runtime report (deterministic inference path): volkswagen_2024

Source: `previous_llm_extractor\annual_reports\for_financial_statements\volkswagen_2024.pdf`  
Source SHA256: `48dfd913979245ae936471b3f5ddf7d6dcf62a8b099c2c9aae5c64dff450c017`  
LLM assist: FORBIDDEN in this mode (no model in the inference path)  
Mapping artifact: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\artifacts\mappings\volkswagen_2024.json` (approved by: PENDING SIGN-OFF; built at code f798bfc)  

## balance_sheet

- pages [475, 476] (artifact), 50 rows x 2 columns, scale 1
- accepted cells 94, flags 37
- footing: 7 verified groups, PASS
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 14 lexical, 18 artifact, 0 LLM, 18 unmapped

## income_statement

- pages [472] (artifact), 16 rows x 2 columns, scale 1000000
- accepted cells 30, flags 7
- footing: 2 verified groups, FAIL
- concept mapping: 1 lexical, 6 artifact, 0 LLM, 9 unmapped

## cash_flow

- pages [478] (artifact), 29 rows x 2 columns, scale 1000000
- accepted cells 50, flags 2, artifact-adjudicated 2
- footing: 3 verified groups, FAIL
- cash tie: FAIL (begin 43522 + change 28291 (activity totals, fx inside change) vs end 40296)
- concept mapping: 1 lexical, 20 artifact, 0 LLM, 8 unmapped

## Simulation

- skipped: 37 flagged balance-sheet cells; cash_flow footing unverified; income_statement footing unverified (adjudication required before simulation)

LLM calls: 0 (runtime mode; replay is bit-exact given the same source, artifact, and code versions)
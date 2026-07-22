# Runtime report (deterministic inference path): tencent_2024

Source: `previous_llm_extractor\annual_reports\for_financial_statements\tencent_2024.pdf`  
Source SHA256: `95b0652da8294527d150a56a9de293627b53e73b4a4c21202c153ea6eb4e9134`  
LLM assist: FORBIDDEN in this mode (no model in the inference path)  
Mapping artifact: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\artifacts\mappings\tencent_2024.json` (approved by: PENDING SIGN-OFF; built at code f798bfc)  

## balance_sheet

- pages [126, 127, 128] (artifact), 29 rows x 2 columns, scale 1
- accepted cells 56, flags 15
- footing: 6 verified groups, PASS
- A = L + E: N/A (no 'Total assets' row)
- concept mapping: 12 lexical, 12 artifact, 0 LLM, 5 unmapped

## income_statement

- pages [124] (artifact), 22 rows x 2 columns, scale 1
- accepted cells 44, flags 7
- footing: 6 verified groups, FAIL
- concept mapping: 4 lexical, 11 artifact, 0 LLM, 7 unmapped

## cash_flow

- pages [133, 134] (artifact), 34 rows x 2 columns, scale 1
- accepted cells 67, flags 0
- footing: 2 verified groups, PASS
- cash tie: FAIL (begin 172320 + change -40160 (net-change row, fx added) vs end 132519)
- concept mapping: 2 lexical, 25 artifact, 0 LLM, 7 unmapped

## Simulation

- skipped: 15 flagged balance-sheet cells; income_statement footing unverified (adjudication required before simulation)

LLM calls: 0 (runtime mode; replay is bit-exact given the same source, artifact, and code versions)
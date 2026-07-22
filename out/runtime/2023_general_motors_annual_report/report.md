# Runtime report (deterministic inference path): 2023_general_motors_annual_report

Source: `previous_llm_extractor\annual_reports\for_financial_statements\2023 General Motors Annual Report .pdf`  
Source SHA256: `42bf7609408f7f8cc2a3be19d32f7a719be52ea668121db27cd969ed01d9c5ed`  
LLM assist: FORBIDDEN in this mode (no model in the inference path)  
Mapping artifact: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\artifacts\mappings\2023_general_motors_annual_report.json` (approved by: PENDING SIGN-OFF; built at code f798bfc)  

## balance_sheet

- pages [62] (artifact), 37 rows x 2 columns, scale 1000000
- accepted cells 74, flags 0
- footing: 9 verified groups, PASS
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 14 lexical, 14 artifact, 0 LLM, 9 unmapped

## income_statement

- pages [61] (artifact), 21 rows x 3 columns, scale 1000000
- accepted cells 63, flags 0
- footing: 4 verified groups, PASS
- concept mapping: 2 lexical, 8 artifact, 0 LLM, 11 unmapped

## cash_flow

- pages [63] (artifact), 33 rows x 3 columns, scale 1000000
- accepted cells 97, flags 0
- footing: 5 verified groups, FAIL
- cash tie: PASS (begin 21948 + change -31 (net-change row, fx inside change) vs end 21917)
- concept mapping: 2 lexical, 19 artifact, 0 LLM, 12 unmapped

## Simulation

- skipped: cash_flow footing unverified (adjudication required before simulation)

LLM calls: 0 (runtime mode; replay is bit-exact given the same source, artifact, and code versions)
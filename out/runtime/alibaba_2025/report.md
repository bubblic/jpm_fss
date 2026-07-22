# Runtime report (deterministic inference path): alibaba_2025

Source: `previous_llm_extractor\annual_reports\for_financial_statements\alibaba_2025.pdf`  
Source SHA256: `8ab1234844b56a2be8b90d92301d0a46123c8770610e87f9462bb27b0e2b7182`  
LLM assist: FORBIDDEN in this mode (no model in the inference path)  
Mapping artifact: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\artifacts\mappings\alibaba_2025.json` (approved by: PENDING SIGN-OFF; built at code f798bfc)  

## balance_sheet

- pages [310] (artifact), 28 rows x 3 columns, scale 1
- accepted cells 62, flags 0
- footing: 25 verified groups, FAIL
- A = L + E: N/A (no 'Total assets' row)
- concept mapping: 8 lexical, 0 LLM, 20 unmapped

## income_statement

- pages [319, 320] (artifact), 35 rows x 9 columns, scale 1
- accepted cells 168, flags 18
- footing: 34 verified groups, FAIL
- concept mapping: 14 lexical, 0 LLM, 21 unmapped

## cash_flow

- pages [311, 312, 313, 314, 315] (artifact), 71 rows x 7 columns, scale 1
- accepted cells 166, flags 47
- footing: 61 verified groups, FAIL
- cash tie: N/A (no beginning/ending cash rows)
- concept mapping: 4 lexical, 0 LLM, 67 unmapped

## Simulation

- skipped: balance_sheet footing unverified; cash_flow footing unverified; income_statement footing unverified (adjudication required before simulation)

LLM calls: 0 (runtime mode; replay is bit-exact given the same source, artifact, and code versions)
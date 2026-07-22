# Runtime report (deterministic inference path): lehman_ar2007

Source: `previous_llm_extractor\annual_reports\for_financial_statements\lehman\ar2007.pdf`  
Source SHA256: `3fa8386c5db7964d069bb8bdb8899d4134142b7c1e3a89e6377844d38bbe47c5`  
LLM assist: FORBIDDEN in this mode (no model in the inference path)  
Mapping artifact: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\artifacts\mappings\lehman_ar2007.json` (approved by: PENDING SIGN-OFF; built at code f798bfc)  

## balance_sheet

- pages [86, 87] (artifact), 33 rows x 2 columns, scale 1000000
- accepted cells 66, flags 2
- footing: 5 verified groups, PASS
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 6 lexical, 11 artifact, 0 LLM, 16 unmapped

## income_statement

- pages [85] (artifact), 30 rows x 3 columns, scale 1000000
- accepted cells 84, flags 0
- footing: 7 verified groups, PASS
- concept mapping: 3 lexical, 6 artifact, 0 LLM, 21 unmapped

## cash_flow

- pages [151, 152, 153] (artifact), 21 rows x 5 columns, scale 1
- accepted cells 90, flags 1
- footing: 4 verified groups, FAIL
- cash tie: N/A (no beginning/ending cash rows)
- concept mapping: 6 lexical, 5 artifact, 0 LLM, 10 unmapped

## Simulation

- skipped: 2 flagged balance-sheet cells; cash_flow footing unverified (adjudication required before simulation)

LLM calls: 0 (runtime mode; replay is bit-exact given the same source, artifact, and code versions)
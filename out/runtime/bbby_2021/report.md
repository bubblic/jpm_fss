# Runtime report (deterministic inference path): bbby_2021

Source: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\data\carry\bbby_2021.pdf`  
Source SHA256: `d62cc2e0e70dbf1dc9e603e96ce69e82acea903c27ff935bb34f1e35c521de2b`  
LLM assist: FORBIDDEN in this mode (no model in the inference path)  
Mapping artifact: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\artifacts\mappings\bbby_2021.json` (approved by: PENDING SIGN-OFF; built at code 7192cce)  

## balance_sheet

- pages [69, 70] (artifact), 27 rows x 2 columns, scale 1000
- accepted cells 52, flags 0
- footing: 6 verified groups, PASS
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 12 lexical, 12 artifact, 0 LLM, 3 unmapped

## income_statement

- pages [71] (artifact), 18 rows x 3 columns, scale 1000
- accepted cells 49, flags 0
- footing: 3 verified groups, PASS
- concept mapping: 3 lexical, 7 artifact, 0 LLM, 8 unmapped

## cash_flow

- pages [74] (artifact), 41 rows x 3 columns, scale 1000
- accepted cells 101, flags 0
- footing: 2 verified groups, PASS
- cash tie: PASS (begin 1407224 + change -936340 (net-change row, fx inside change) vs end 470884)
- concept mapping: 6 lexical, 21 artifact, 0 LLM, 14 unmapped

## Simulation

- symbolic closure: PROVEN
- baseline: mean net income 0M (identity violations 201)
- expansion: mean net income 0M (identity violations 201)
- recession: mean net income 0M (identity violations 201)
- competition: mean net income 0M (identity violations 201)
- rate_hike: mean net income 0M (identity violations 201)
- inflation: mean net income 0M (identity violations 201)

LLM calls: 0 (runtime mode; replay is bit-exact given the same source, artifact, and code versions)
# Onboarding report (build time): bbby_ar2022

Source: `previous_llm_extractor\annual_reports\for_financial_statements\bbby\ar2022.pdf`  
Source SHA256: `1c0493f0331effa2009b98f64cae9988b11b5b6ae635a258c0d15d52bf481d25`  
LLM assist: configured
Mapping artifact written: `C:\Users\jaebu\repo\jpmorgan\jpm_fss\artifacts\mappings\bbby_ar2022.json` (status: PENDING SIGN-OFF)  

## balance_sheet

- pages [66, 67] (deterministic), 30 rows x 2 columns, scale 1000
- accepted cells 51, flags 0
- footing: 4 verified groups, PASS
- A = L + E: N/A (no combined or component totals)
- concept mapping: 11 lexical, 14 LLM, 5 unmapped

## income_statement

- pages [69] (deterministic), 19 rows x 3 columns, scale 1000
- accepted cells 52, flags 0
- footing: 3 verified groups, PASS
- concept mapping: 3 lexical, 7 LLM, 9 unmapped

## cash_flow

- pages [74] (llm), 46 rows x 3 columns, scale 1000
- accepted cells 102, flags 0
- footing: 1 verified groups, PASS
- cash tie: N/A (no beginning/ending cash rows)
- concept mapping: 6 lexical, 13 LLM, 27 unmapped

## Simulation

- symbolic closure: PROVEN
- baseline: mean net income 0M (identity violations 201)
- expansion: mean net income 0M (identity violations 201)
- recession: mean net income 0M (identity violations 201)
- competition: mean net income 0M (identity violations 201)
- rate_hike: mean net income 0M (identity violations 201)
- inflation: mean net income 0M (identity violations 201)

LLM calls: 59
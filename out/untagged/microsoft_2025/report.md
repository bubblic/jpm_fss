# Untagged extraction report: microsoft_2025

Source: `previous_llm_extractor\annual_reports\for_financial_statements\microsoft_2025.pdf`  
LLM assist: configured

## balance_sheet

- pages [38] (deterministic), 34 rows x 2 columns, scale 1000000
- accepted cells 68, flags 0, LLM-adjudicated 2
- footing: 7 verified groups, PASS
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 34 lexical, 0 LLM, 0 unmapped

## income_statement

- pages [36] (deterministic), 19 rows x 3 columns, scale 1000000
- accepted cells 57, flags 0
- footing: 6 verified groups, PASS
- concept mapping: 15 lexical, 0 LLM, 4 unmapped

## cash_flow

- pages [39] (deterministic), 34 rows x 3 columns, scale 1000000
- accepted cells 102, flags 0
- footing: 4 verified groups, PASS
- cash tie: PASS (begin 18315 + change 11927 (net-change row, fx inside change) vs end 30242)
- concept mapping: 34 lexical, 0 LLM, 0 unmapped

## Simulation

- symbolic closure: PROVEN
- baseline: mean net income 112,871M (identity violations 0)
- expansion: mean net income 118,220M (identity violations 0)
- recession: mean net income 104,794M (identity violations 0)
- competition: mean net income 108,618M (identity violations 0)
- rate_hike: mean net income 113,495M (identity violations 0)
- inflation: mean net income 111,643M (identity violations 0)

LLM calls: 8
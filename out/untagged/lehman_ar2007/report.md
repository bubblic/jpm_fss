# Untagged extraction report: lehman_ar2007

Source: `previous_llm_extractor\annual_reports\for_financial_statements\lehman\ar2007.pdf`  
LLM assist: configured

## balance_sheet

- pages [86, 87] (deterministic), 23 rows x 2 columns, scale 1000000
- accepted cells 46, flags 0
- footing: 2 verified groups, PASS
- A = L + E: N/A (no combined or component totals)
- concept mapping: 3 lexical, 8 LLM, 12 unmapped

## income_statement

- pages [85] (deterministic), 30 rows x 3 columns, scale 1000000
- accepted cells 84, flags 0
- footing: 7 verified groups, FAIL
- concept mapping: 3 lexical, 6 LLM, 21 unmapped

## cash_flow

- pages [62, 89, 112] (llm), 54 rows x 4 columns, scale 1000000
- accepted cells 119, flags 24
- footing: 5 verified groups, PASS
- cash tie: N/A (no beginning/ending cash rows)
- concept mapping: 3 lexical, 13 LLM, 38 unmapped

## Simulation

- skipped: income_statement footing unverified (adjudication required before simulation)

LLM calls: 90
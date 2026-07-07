# Untagged extraction report: lehman_ar2007

Source: `previous_llm_extractor\annual_reports\for_financial_statements\lehman\ar2007.pdf`  
LLM assist: configured

## balance_sheet

- pages [86, 87] (deterministic), 33 rows x 2 columns, scale 1000000
- accepted cells 66, flags 2
- footing: 5 verified groups, PASS
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 6 lexical, 11 LLM, 16 unmapped

## income_statement

- pages [85] (deterministic), 30 rows x 3 columns, scale 1000000
- accepted cells 84, flags 0
- footing: 7 verified groups, PASS
- concept mapping: 3 lexical, 6 LLM, 21 unmapped

## cash_flow

- pages [151, 152, 153] (llm), 21 rows x 5 columns, scale 1
- accepted cells 90, flags 1
- footing: 4 verified groups, FAIL
- cash tie: N/A (no beginning/ending cash rows)
- concept mapping: 6 lexical, 5 LLM, 10 unmapped

## Simulation

- skipped: 2 flagged balance-sheet cells; cash_flow footing unverified (adjudication required before simulation)

LLM calls: 50
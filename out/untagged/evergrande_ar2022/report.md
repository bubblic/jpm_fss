# Untagged extraction report: evergrande_ar2022

Source: `previous_llm_extractor\annual_reports\for_financial_statements\evergrande\ar2022.pdf`  
LLM assist: configured

## balance_sheet

- pages [46, 47] (deterministic), 13 rows x 2 columns, scale 1000000
- accepted cells 26, flags 8
- footing: 4 verified groups, FAIL
- A = L + E: N/A (no 'Total assets' row)
- concept mapping: 4 lexical, 4 LLM, 5 unmapped

## income_statement

- pages [48, 49] (deterministic), 34 rows x 2 columns, scale 1
- accepted cells 60, flags 21, LLM-adjudicated 5
- footing: 9 verified groups, FAIL
- concept mapping: 4 lexical, 21 LLM, 9 unmapped

## cash_flow

- pages [52, 53] (deterministic), 34 rows x 2 columns, scale 1000000
- accepted cells 63, flags 1
- footing: 3 verified groups, FAIL
- cash tie: PASS (begin 5435 + change -1103 (net-change row, fx added) vs end 4334)
- concept mapping: 4 lexical, 23 LLM, 7 unmapped

## Simulation

- skipped: 8 flagged balance-sheet cells; balance_sheet footing unverified; cash_flow footing unverified; income_statement footing unverified (adjudication required before simulation)

LLM calls: 90
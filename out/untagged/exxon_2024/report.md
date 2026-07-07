# Untagged extraction report: exxon_2024

Source: `previous_llm_extractor\annual_reports\for_financial_statements\exxon_2024.pdf`  
LLM assist: configured

## balance_sheet

- pages [87, 88] (deterministic), 57 rows x 3 columns, scale 1000000
- accepted cells 146, flags 12
- footing: 4 verified groups, PASS
- A = L + E: N/A (no combined or component totals)
- concept mapping: 7 lexical, 14 LLM, 36 unmapped

## income_statement

- pages [85] (deterministic), 20 rows x 3 columns, scale 1000000
- accepted cells 60, flags 8
- footing: 3 verified groups, FAIL
- concept mapping: 0 lexical, 10 LLM, 10 unmapped

## cash_flow

- pages [88] (deterministic), 35 rows x 3 columns, scale 1000000
- accepted cells 101, flags 4
- footing: 3 verified groups, PASS
- cash tie: FAIL (begin 31568 + change -7705 (activity totals, fx added) vs end 23187)
- concept mapping: 0 lexical, 15 LLM, 20 unmapped

## Simulation

- skipped: 12 flagged balance-sheet cells; income_statement footing unverified (adjudication required before simulation)

LLM calls: 90
# Untagged extraction report: tencent_2024

Source: `previous_llm_extractor\annual_reports\for_financial_statements\tencent_2024.pdf`  
LLM assist: configured

## balance_sheet

- pages [126, 127, 128] (deterministic), 29 rows x 2 columns, scale 1
- accepted cells 56, flags 15
- footing: 6 verified groups, PASS
- A = L + E: N/A (no 'Total assets' row)
- concept mapping: 12 lexical, 10 LLM, 7 unmapped

## income_statement

- pages [124] (deterministic), 22 rows x 2 columns, scale 1
- accepted cells 44, flags 7
- footing: 6 verified groups, FAIL
- concept mapping: 4 lexical, 11 LLM, 7 unmapped

## cash_flow

- pages [133, 134] (deterministic), 34 rows x 2 columns, scale 1
- accepted cells 67, flags 0
- footing: 2 verified groups, PASS
- cash tie: FAIL (begin 172320 + change -40160 (net-change row, fx added) vs end 132519)
- concept mapping: 2 lexical, 25 LLM, 7 unmapped

## Simulation

- skipped: 15 flagged balance-sheet cells; income_statement footing unverified (adjudication required before simulation)

LLM calls: 55
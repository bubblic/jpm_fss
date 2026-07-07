# Untagged extraction report: lvmh_dec_2024

Source: `previous_llm_extractor\annual_reports\for_financial_statements\lvmh_dec_2024.pdf`  
LLM assist: configured

## balance_sheet

- pages [26] (deterministic), 32 rows x 3 columns, scale 1
- accepted cells 96, flags 22
- footing: 2 verified groups, FAIL
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 12 lexical, 19 LLM, 1 unmapped

## income_statement

- pages [24, 25] (deterministic), 42 rows x 3 columns, scale 1000000
- accepted cells 121, flags 11
- footing: 9 verified groups, FAIL
- concept mapping: 5 lexical, 13 LLM, 24 unmapped

## cash_flow

- pages [28] (deterministic), 34 rows x 4 columns, scale 1000000
- accepted cells 113, flags 0
- footing: 7 verified groups, FAIL
- cash tie: N/A (no net-change row or activity totals)
- concept mapping: 3 lexical, 20 LLM, 11 unmapped

## Simulation

- skipped: 22 flagged balance-sheet cells; balance_sheet footing unverified; cash_flow footing unverified; income_statement footing unverified (adjudication required before simulation)

LLM calls: 69
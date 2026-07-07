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

- pages [24] (deterministic), 21 rows x 3 columns, scale 1000000
- accepted cells 63, flags 9
- footing: 4 verified groups, FAIL
- concept mapping: 5 lexical, 9 LLM, 7 unmapped

## cash_flow

- pages [5, 21, 28] (llm), 15 rows x 6 columns, scale 1
- accepted cells 6, flags 39, LLM-adjudicated 3
- footing: 4 verified groups, PASS
- cash tie: N/A (no beginning/ending cash rows)
- concept mapping: 0 lexical, 0 LLM, 15 unmapped

## Simulation

- skipped: 22 flagged balance-sheet cells; balance_sheet footing unverified; income_statement footing unverified (adjudication required before simulation)

LLM calls: 75
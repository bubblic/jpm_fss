# Untagged extraction report: volkswagen_2024

Source: `previous_llm_extractor\annual_reports\for_financial_statements\volkswagen_2024.pdf`  
LLM assist: configured

## balance_sheet

- pages [132] (deterministic), 29 rows x 6 columns, scale 1000000
- accepted cells 164, flags 4, LLM-adjudicated 2
- footing: 2 verified groups, FAIL
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 11 lexical, 10 LLM, 8 unmapped

## income_statement

- pages [472] (deterministic), 16 rows x 2 columns, scale 1000000
- accepted cells 30, flags 7
- footing: 2 verified groups, FAIL
- concept mapping: 1 lexical, 6 LLM, 9 unmapped

## cash_flow

- pages [128, 478, 539] (llm), 8 rows x 2 columns, scale 1000000
- accepted cells 16, flags 0
- footing: 0 verified groups, PASS
- cash tie: N/A (no beginning/ending cash rows)
- concept mapping: 5 lexical, 3 LLM, 0 unmapped

## Simulation

- skipped: 4 flagged balance-sheet cells; balance_sheet footing unverified; income_statement footing unverified (adjudication required before simulation)

LLM calls: 58
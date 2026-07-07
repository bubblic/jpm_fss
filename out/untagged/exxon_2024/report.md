# Untagged extraction report: exxon_2024

Source: `previous_llm_extractor\annual_reports\for_financial_statements\exxon_2024.pdf`  
LLM assist: configured

## balance_sheet

- pages [87, 88, 89] (deterministic), 103 rows x 9 columns, scale 1
- accepted cells 224, flags 211
- footing: 0 verified groups, PASS
- A = L + E: N/A (no 'Total assets' row)
- concept mapping: 12 lexical, 15 LLM, 76 unmapped

## income_statement

- pages [85, 86, 87] (deterministic), 58 rows x 3 columns, scale 1
- accepted cells 143, flags 18
- footing: 3 verified groups, FAIL
- concept mapping: 9 lexical, 12 LLM, 37 unmapped

## cash_flow

- pages [88, 89] (deterministic), 74 rows x 9 columns, scale 1
- accepted cells 169, flags 198, LLM-adjudicated 3
- footing: 0 verified groups, PASS
- cash tie: N/A (no beginning/ending cash rows)
- concept mapping: 3 lexical, 12 LLM, 59 unmapped

## Simulation

- skipped: 211 flagged balance-sheet cells; income_statement footing unverified (adjudication required before simulation)

LLM calls: 160
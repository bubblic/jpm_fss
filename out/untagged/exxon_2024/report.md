# Untagged extraction report: exxon_2024

Source: `previous_llm_extractor\annual_reports\for_financial_statements\exxon_2024.pdf`  
LLM assist: not configured (deterministic only)

## balance_sheet

- pages [87, 88, 89] (deterministic), 103 rows x 9 columns, scale 1
- accepted cells 224, flags 211
- footing: 0 verified groups, PASS
- A = L + E: N/A (no 'Total assets' row)
- concept mapping: 12 lexical, 0 LLM, 91 unmapped

## income_statement

- pages [85, 86, 87] (deterministic), 58 rows x 3 columns, scale 1
- accepted cells 143, flags 18
- footing: 0 verified groups, PASS
- concept mapping: 9 lexical, 0 LLM, 49 unmapped

## cash_flow

- pages [88, 89] (deterministic), 74 rows x 9 columns, scale 1
- accepted cells 166, flags 201
- footing: 0 verified groups, PASS
- cash tie: N/A (no beginning/ending cash rows)
- concept mapping: 3 lexical, 0 LLM, 71 unmapped

## Simulation

- skipped: 211 flagged balance-sheet cells (adjudication required before simulation)

LLM calls: 0
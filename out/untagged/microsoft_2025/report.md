# Untagged extraction report: microsoft_2025

Source: `previous_llm_extractor\annual_reports\for_financial_statements\microsoft_2025.pdf`  
LLM assist: not configured (deterministic only)

## balance_sheet

- pages [38] (deterministic), 34 rows x 2 columns, scale 1000000
- accepted cells 66, flags 2
- footing: 7 verified groups, PASS
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 34 lexical, 0 LLM, 0 unmapped

## income_statement

- pages [36] (deterministic), 19 rows x 3 columns, scale 1000000
- accepted cells 57, flags 0
- footing: 6 verified groups, PASS
- concept mapping: 15 lexical, 0 LLM, 4 unmapped

## cash_flow

- pages [39] (deterministic), 34 rows x 3 columns, scale 1000000
- accepted cells 102, flags 0
- footing: 4 verified groups, PASS
- cash tie: PASS (begin 18315 + change 11927 (net-change row, fx inside change) vs end 30242)
- concept mapping: 34 lexical, 0 LLM, 0 unmapped

## Simulation

- skipped: 2 flagged balance-sheet cells (adjudication required before simulation)

LLM calls: 0
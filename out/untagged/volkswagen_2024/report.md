# Untagged extraction report: volkswagen_2024

Source: `previous_llm_extractor\annual_reports\for_financial_statements\volkswagen_2024.pdf`  
LLM assist: configured

## balance_sheet

- pages [475, 476] (deterministic), 50 rows x 2 columns, scale 1
- accepted cells 94, flags 37
- footing: 7 verified groups, PASS
- A = L + E: PASS (assets vs combined right-hand total)
- concept mapping: 14 lexical, 15 LLM, 21 unmapped

## income_statement

- pages [472] (deterministic), 16 rows x 2 columns, scale 1000000
- accepted cells 30, flags 7
- footing: 2 verified groups, FAIL
- concept mapping: 1 lexical, 6 LLM, 9 unmapped

## cash_flow

- pages [478] (deterministic), 29 rows x 2 columns, scale 1000000
- accepted cells 50, flags 2, LLM-adjudicated 2
- footing: 3 verified groups, FAIL
- cash tie: FAIL (begin 43522 + change 28291 (activity totals, fx inside change) vs end 40296)
- concept mapping: 1 lexical, 19 LLM, 9 unmapped

## Simulation

- skipped: 37 flagged balance-sheet cells; cash_flow footing unverified; income_statement footing unverified (adjudication required before simulation)

LLM calls: 90
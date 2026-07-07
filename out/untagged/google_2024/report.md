# Untagged extraction report: google_2024

Source: `previous_llm_extractor\annual_reports\for_financial_statements\google_2024.pdf`  
LLM assist: not configured (deterministic only)

## balance_sheet

- pages [57] (deterministic), 26 rows x 2 columns, scale 1000000
- accepted cells 50, flags 2
- footing: 5 verified groups, PASS
- A = L + E: N/A (no combined or component totals)
- concept mapping: 15 lexical, 0 LLM, 11 unmapped

## income_statement

- pages [58] (deterministic), 13 rows x 3 columns, scale 1000000
- accepted cells 39, flags 0
- footing: 3 verified groups, FAIL
- concept mapping: 7 lexical, 0 LLM, 6 unmapped

## cash_flow

- pages [61] (deterministic), 34 rows x 3 columns, scale 1000000
- accepted cells 99, flags 2
- footing: 5 verified groups, PASS
- cash tie: PASS (begin 20945 + change 934 (net-change row, fx inside change) vs end 21879)
- concept mapping: 12 lexical, 0 LLM, 22 unmapped

## Simulation

- skipped: 2 flagged balance-sheet cells; income_statement footing unverified (adjudication required before simulation)

LLM calls: 0